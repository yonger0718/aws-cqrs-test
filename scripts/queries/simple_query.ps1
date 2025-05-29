# Simple LocalStack Query Tool
# Encoding: UTF-8

$AWS_ENDPOINT = "http://localhost:4566"
$EKS_ENDPOINT = "http://localhost:8000"

Write-Host ""
Write-Host "LocalStack Query Tool" -ForegroundColor Cyan
Write-Host "===================" -ForegroundColor Cyan
Write-Host ""

function Invoke-DynamoDBRequest {
    param([string]$Target, [string]$Body = "{}")
    
    $headers = @{
        "Content-Type"  = "application/x-amz-json-1.0"
        "X-Amz-Target"  = $Target
        "Authorization" = "AWS4-HMAC-SHA256 Credential=test/20230101/us-east-1/dynamodb/aws4_request, SignedHeaders=host;x-amz-date, Signature=test"
    }
    
    try {
        return Invoke-RestMethod -Uri $AWS_ENDPOINT -Method POST -Headers $headers -Body $Body
    }
    catch {
        Write-Host "Request failed: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

function Show-Menu {
    Write-Host "Select query type:" -ForegroundColor Yellow
    Write-Host "1. DynamoDB Tables" -ForegroundColor Green
    Write-Host "2. Lambda Functions" -ForegroundColor Green
    Write-Host "3. EKS Handler API" -ForegroundColor Green
    Write-Host "4. Full Status Check" -ForegroundColor Green
    Write-Host "0. Exit" -ForegroundColor Red
    Write-Host ""
}

function Query-DynamoDB {
    Write-Host "DynamoDB Query" -ForegroundColor Cyan
    Write-Host "==============" -ForegroundColor Gray
    
    # List all tables
    Write-Host "1. List all tables" -ForegroundColor Yellow
    $response = Invoke-DynamoDBRequest -Target "DynamoDB_20120810.ListTables"
    if ($response) {
        Write-Host "Tables:" -ForegroundColor Green
        $response.TableNames | ForEach-Object { Write-Host "  - $_" -ForegroundColor Cyan }
    }
    
    Write-Host ""
    Write-Host "2. Scan command-records table" -ForegroundColor Yellow
    $scanBody = @{ TableName = "command-records"; Limit = 5 } | ConvertTo-Json
    $response = Invoke-DynamoDBRequest -Target "DynamoDB_20120810.Scan" -Body $scanBody
    if ($response) {
        Write-Host "command-records content (first 5):" -ForegroundColor Green
        $response.Items | ForEach-Object {
            Write-Host "  Transaction ID: $($_.transaction_id.S)" -ForegroundColor Cyan
            Write-Host "  User ID: $($_.user_id.S)" -ForegroundColor Cyan
            Write-Host "  Created: $($_.created_at.N)" -ForegroundColor Cyan
            Write-Host "  ---" -ForegroundColor Gray
        }
        Write-Host "Total records: $($response.Count)" -ForegroundColor Green
    }
    
    Write-Host ""
    Write-Host "3. Scan notification-records table" -ForegroundColor Yellow
    $scanBody = @{ TableName = "notification-records"; Limit = 5 } | ConvertTo-Json
    $response = Invoke-DynamoDBRequest -Target "DynamoDB_20120810.Scan" -Body $scanBody
    if ($response) {
        Write-Host "notification-records content (first 5):" -ForegroundColor Green
        $response.Items | ForEach-Object {
            Write-Host "  User ID: $($_.user_id.S)" -ForegroundColor Cyan
            Write-Host "  Title: $($_.notification_title.S)" -ForegroundColor Cyan
            Write-Host "  Status: $($_.status.S)" -ForegroundColor Cyan
            Write-Host "  Platform: $($_.platform.S)" -ForegroundColor Cyan
            Write-Host "  ---" -ForegroundColor Gray
        }
        Write-Host "Total records: $($response.Count)" -ForegroundColor Green
    }
}

function Query-Lambda {
    Write-Host "Lambda Functions" -ForegroundColor Cyan
    Write-Host "================" -ForegroundColor Gray
    
    try {
        $response = Invoke-RestMethod -Uri "$AWS_ENDPOINT/2015-03-31/functions" -Method GET
        if ($response) {
            Write-Host "Lambda functions:" -ForegroundColor Green
            $response.Functions | ForEach-Object {
                Write-Host "  - Name: $($_.FunctionName)" -ForegroundColor Cyan
                Write-Host "    Runtime: $($_.Runtime)" -ForegroundColor Cyan
                Write-Host "    State: $($_.State)" -ForegroundColor Cyan
                Write-Host "    ---" -ForegroundColor Gray
            }
        }
    }
    catch {
        Write-Host "Lambda query failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Test-EKSHandler {
    Write-Host "EKS Handler API Test" -ForegroundColor Cyan
    Write-Host "===================" -ForegroundColor Gray
    
    Write-Host "1. Health check" -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri $EKS_ENDPOINT -Method GET
        Write-Host "Health check result:" -ForegroundColor Green
        Write-Host ($response | ConvertTo-Json) -ForegroundColor Cyan
    }
    catch {
        Write-Host "EKS Handler connection failed: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "2. Query all notifications" -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri "$EKS_ENDPOINT/query/user" -Method GET
        Write-Host "Query result:" -ForegroundColor Green
        Write-Host "  Success: $($response.success)" -ForegroundColor Cyan
        Write-Host "  Count: $($response.count)" -ForegroundColor Cyan
        if ($response.items -and $response.items.Count -gt 0) {
            Write-Host "  First record example:" -ForegroundColor Cyan
            Write-Host ($response.items[0] | ConvertTo-Json) -ForegroundColor White
        }
    }
    catch {
        Write-Host "API query failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Check-AllStatus {
    Write-Host "Full Status Check" -ForegroundColor Cyan
    Write-Host "=================" -ForegroundColor Gray
    
    # Check Docker containers
    Write-Host "1. Docker containers" -ForegroundColor Yellow
    try {
        $containers = docker ps --format "table {{.Names}}\t{{.Status}}"
        if ($containers) {
            Write-Host $containers -ForegroundColor Cyan
        }
    }
    catch {
        Write-Host "Docker command failed" -ForegroundColor Red
    }
    
    Write-Host ""
    
    # Check LocalStack health
    Write-Host "2. LocalStack services" -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri "$AWS_ENDPOINT/health" -Method GET
        Write-Host "LocalStack health:" -ForegroundColor Green
        $response.services | Get-Member -MemberType NoteProperty | ForEach-Object {
            $serviceName = $_.Name
            $status = $response.services.$serviceName
            $color = if ($status -eq "available") { "Green" } else { "Red" }
            Write-Host "  $serviceName : $status" -ForegroundColor $color
        }
    }
    catch {
        Write-Host "LocalStack health check failed" -ForegroundColor Red
    }
    
    Write-Host ""
    
    # Check data statistics
    Write-Host "3. Data statistics" -ForegroundColor Yellow
    
    $commandCountBody = @{ TableName = "command-records"; Select = "COUNT" } | ConvertTo-Json
    $commandResponse = Invoke-DynamoDBRequest -Target "DynamoDB_20120810.Scan" -Body $commandCountBody
    $commandCount = if ($commandResponse) { $commandResponse.Count } else { "N/A" }
    
    $queryCountBody = @{ TableName = "notification-records"; Select = "COUNT" } | ConvertTo-Json
    $queryResponse = Invoke-DynamoDBRequest -Target "DynamoDB_20120810.Scan" -Body $queryCountBody
    $queryCount = if ($queryResponse) { $queryResponse.Count } else { "N/A" }
    
    Write-Host "  Command table records: $commandCount" -ForegroundColor Cyan
    Write-Host "  Query table records: $queryCount" -ForegroundColor Cyan
    
    if ($commandCount -ne "N/A" -and $queryCount -ne "N/A") {
        if ([int]$queryCount -le [int]$commandCount) {
            Write-Host "  Data consistency: OK" -ForegroundColor Green
        }
        else {
            Write-Host "  Data consistency: WARNING" -ForegroundColor Yellow
        }
    }
}

# Main program loop
do {
    Show-Menu
    $choice = Read-Host "Enter option (0-4)"
    
    switch ($choice) {
        "1" { Query-DynamoDB }
        "2" { Query-Lambda }
        "3" { Test-EKSHandler }
        "4" { Check-AllStatus }
        "0" { 
            Write-Host "Thank you!" -ForegroundColor Green
            break 
        }
        default { 
            Write-Host "Invalid option" -ForegroundColor Red 
        }
    }
    
    if ($choice -ne "0") {
        Write-Host ""
        Read-Host "Press Enter to continue"
        Clear-Host
    }
} while ($choice -ne "0") 