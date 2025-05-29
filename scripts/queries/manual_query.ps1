# Manual Query Tool for CQRS System
# Based on successful test results

Write-Host "🗂️ CQRS System Manual Query Tool" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

$AWS_ENDPOINT = "http://localhost:4566"
$EKS_ENDPOINT = "http://localhost:8000"

function Show-Menu {
    Write-Host "`nSelect your query:" -ForegroundColor Yellow
    Write-Host "1. Show system status" -ForegroundColor Green
    Write-Host "2. Query DynamoDB tables" -ForegroundColor Green
    Write-Host "3. View table contents (sample)" -ForegroundColor Green
    Write-Host "4. Get record counts" -ForegroundColor Green
    Write-Host "5. Check EKS Handler info" -ForegroundColor Green
    Write-Host "0. Exit" -ForegroundColor Red
    Write-Host ""
}

function Show-SystemStatus {
    Write-Host "`n📊 System Status Summary" -ForegroundColor Cyan
    Write-Host "========================" -ForegroundColor Gray

    # EKS Handler
    try {
        $eks = Invoke-RestMethod -Uri $EKS_ENDPOINT -Method GET -TimeoutSec 3
        Write-Host "✅ EKS Handler: RUNNING ($($eks.version))" -ForegroundColor Green
        Write-Host "   Available endpoints: $($eks.endpoints -join ', ')" -ForegroundColor Cyan
    }
    catch {
        Write-Host "❌ EKS Handler: FAILED" -ForegroundColor Red
    }

    # DynamoDB Tables
    $headers = @{
        "Content-Type" = "application/x-amz-json-1.0"
        "X-Amz-Target" = "DynamoDB_20120810.ListTables"
    }
    try {
        $tables = Invoke-RestMethod -Uri $AWS_ENDPOINT -Method POST -Headers $headers -Body '{}'
        Write-Host "✅ DynamoDB: AVAILABLE" -ForegroundColor Green
        Write-Host "   Tables: $($tables.TableNames -join ', ')" -ForegroundColor Cyan
    }
    catch {
        Write-Host "❌ DynamoDB: FAILED" -ForegroundColor Red
    }
}

function Query-DynamoDBTables {
    Write-Host "`n🗂️ DynamoDB Tables Information" -ForegroundColor Cyan
    Write-Host "==============================" -ForegroundColor Gray

    $headers = @{
        "Content-Type" = "application/x-amz-json-1.0"
        "X-Amz-Target" = "DynamoDB_20120810.ListTables"
    }

    try {
        $response = Invoke-RestMethod -Uri $AWS_ENDPOINT -Method POST -Headers $headers -Body '{}'
        Write-Host "📋 Available tables:" -ForegroundColor Green
        $response.TableNames | ForEach-Object {
            Write-Host "  - $_" -ForegroundColor Cyan

            # Get table description
            $descHeaders = @{
                "Content-Type" = "application/x-amz-json-1.0"
                "X-Amz-Target" = "DynamoDB_20120810.DescribeTable"
            }
            $descBody = @{ TableName = $_ } | ConvertTo-Json

            try {
                $desc = Invoke-RestMethod -Uri $AWS_ENDPOINT -Method POST -Headers $descHeaders -Body $descBody
                Write-Host "    Status: $($desc.Table.TableStatus)" -ForegroundColor White
                Write-Host "    Key Schema: $($desc.Table.KeySchema.AttributeName -join ', ')" -ForegroundColor White
            }
            catch {
                Write-Host "    (Description unavailable)" -ForegroundColor Yellow
            }
        }
    }
    catch {
        Write-Host "❌ Failed to list tables: $($_.Exception.Message)" -ForegroundColor Red
    }
}

function View-TableContents {
    Write-Host "`n📄 Table Contents (Sample)" -ForegroundColor Cyan
    Write-Host "==========================" -ForegroundColor Gray

    $scanHeaders = @{
        "Content-Type" = "application/x-amz-json-1.0"
        "X-Amz-Target" = "DynamoDB_20120810.Scan"
    }

    # Command Records
    Write-Host "`n📝 Command Records (first 3):" -ForegroundColor Yellow
    $cmdBody = @{ TableName = "command-records"; Limit = 3 } | ConvertTo-Json
    try {
        $response = Invoke-RestMethod -Uri $AWS_ENDPOINT -Method POST -Headers $scanHeaders -Body $cmdBody
        $response.Items | ForEach-Object {
            Write-Host "  Transaction: $($_.transaction_id.S)" -ForegroundColor Cyan
            Write-Host "  User: $($_.user_id.S)" -ForegroundColor Cyan
            Write-Host "  Created: $($_.created_at.N)" -ForegroundColor Cyan
            Write-Host "  ---" -ForegroundColor Gray
        }
    }
    catch {
        Write-Host "  ❌ Failed to query command records" -ForegroundColor Red
    }

    # Notification Records
    Write-Host "`n📢 Notification Records (first 3):" -ForegroundColor Yellow
    $notifyBody = @{ TableName = "notification-records"; Limit = 3 } | ConvertTo-Json
    try {
        $response = Invoke-RestMethod -Uri $AWS_ENDPOINT -Method POST -Headers $scanHeaders -Body $notifyBody
        $response.Items | ForEach-Object {
            Write-Host "  User: $($_.user_id.S)" -ForegroundColor Cyan
            Write-Host "  Title: $($_.notification_title.S)" -ForegroundColor Cyan
            Write-Host "  Status: $($_.status.S)" -ForegroundColor Cyan
            Write-Host "  Platform: $($_.platform.S)" -ForegroundColor Cyan
            Write-Host "  ---" -ForegroundColor Gray
        }
    }
    catch {
        Write-Host "  ❌ Failed to query notification records" -ForegroundColor Red
    }
}

function Get-RecordCounts {
    Write-Host "`n📊 Record Counts" -ForegroundColor Cyan
    Write-Host "=================" -ForegroundColor Gray

    $countHeaders = @{
        "Content-Type" = "application/x-amz-json-1.0"
        "X-Amz-Target" = "DynamoDB_20120810.Scan"
    }

    # Command Records Count
    $cmdCountBody = @{ TableName = "command-records"; Select = "COUNT" } | ConvertTo-Json
    try {
        $cmdResponse = Invoke-RestMethod -Uri $AWS_ENDPOINT -Method POST -Headers $countHeaders -Body $cmdCountBody
        Write-Host "📝 Command Records: $($cmdResponse.Count)" -ForegroundColor Green
    }
    catch {
        Write-Host "📝 Command Records: Failed to count" -ForegroundColor Red
    }

    # Notification Records Count
    $notifyCountBody = @{ TableName = "notification-records"; Select = "COUNT" } | ConvertTo-Json
    try {
        $notifyResponse = Invoke-RestMethod -Uri $AWS_ENDPOINT -Method POST -Headers $countHeaders -Body $notifyCountBody
        Write-Host "📢 Notification Records: $($notifyResponse.Count)" -ForegroundColor Green
    }
    catch {
        Write-Host "📢 Notification Records: Failed to count" -ForegroundColor Red
    }

    # CQRS Consistency Check
    if ($cmdResponse -and $notifyResponse) {
        $cmdCount = [int]$cmdResponse.Count
        $notifyCount = [int]$notifyResponse.Count

        Write-Host "`n🔍 CQRS Consistency:" -ForegroundColor Magenta
        if ($notifyCount -le $cmdCount) {
            Write-Host "✅ Data consistency OK (Query: $notifyCount <= Command: $cmdCount)" -ForegroundColor Green
        }
        else {
            Write-Host "⚠️ Data inconsistency detected (Query: $notifyCount > Command: $cmdCount)" -ForegroundColor Yellow
        }

        $syncRate = [math]::Round(($notifyCount / $cmdCount) * 100, 1)
        Write-Host "📈 Synchronization rate: $syncRate%" -ForegroundColor Cyan
    }
}

function Check-EKSHandler {
    Write-Host "`n🚀 EKS Handler Information" -ForegroundColor Cyan
    Write-Host "==========================" -ForegroundColor Gray

    try {
        $response = Invoke-RestMethod -Uri $EKS_ENDPOINT -Method GET
        Write-Host "📋 Service Details:" -ForegroundColor Yellow
        Write-Host "  Name: $($response.service)" -ForegroundColor Cyan
        Write-Host "  Version: $($response.version)" -ForegroundColor Cyan
        Write-Host "  Available Endpoints:" -ForegroundColor Cyan
        $response.endpoints | ForEach-Object { Write-Host "    - $_" -ForegroundColor White }

        Write-Host "`n⚠️ Note: API endpoints return 405 Method Not Allowed" -ForegroundColor Yellow
        Write-Host "   This might be normal - they may require specific parameters" -ForegroundColor Yellow
        Write-Host "   or different HTTP methods for security reasons." -ForegroundColor Yellow
    }
    catch {
        Write-Host "❌ Failed to get EKS Handler info: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Main program loop
do {
    Show-Menu
    $choice = Read-Host "Enter option (0-5)"

    switch ($choice) {
        "1" { Show-SystemStatus }
        "2" { Query-DynamoDBTables }
        "3" { View-TableContents }
        "4" { Get-RecordCounts }
        "5" { Check-EKSHandler }
        "0" {
            Write-Host "`n👋 Thank you for using the CQRS Query Tool!" -ForegroundColor Green
            break
        }
        default {
            Write-Host "`n❌ Invalid option. Please try again." -ForegroundColor Red
        }
    }

    if ($choice -ne "0") {
        Write-Host ""
        Read-Host "Press Enter to continue"
        Clear-Host
    }
} while ($choice -ne "0")
