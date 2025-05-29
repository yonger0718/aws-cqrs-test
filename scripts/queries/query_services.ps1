# 🔍 LocalStack 服務查詢工具 (PowerShell 版本 - 無需 AWS CLI)
# 編碼: UTF-8

$Host.UI.RawUI.WindowTitle = "LocalStack 服務查詢工具"

# 設定端點
$AWS_ENDPOINT = "http://localhost:4566"
$EKS_ENDPOINT = "http://localhost:8000"

# AWS 簽名相關（LocalStack 不需要真實簽名）
$AWS_ACCESS_KEY_ID = "test"
$AWS_SECRET_ACCESS_KEY = "test"
$AWS_REGION = "us-east-1"

Write-Host ""
Write-Host "🔍 LocalStack 服務查詢工具" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan
Write-Host ""

# 輔助函數：發送 DynamoDB 請求
function Invoke-DynamoDBRequest {
    param(
        [string]$Target,
        [string]$Body = "{}"
    )

    $headers = @{
        "Content-Type"  = "application/x-amz-json-1.0"
        "X-Amz-Target"  = $Target
        "Authorization" = "AWS4-HMAC-SHA256 Credential=test/20230101/us-east-1/dynamodb/aws4_request, SignedHeaders=host;x-amz-date, Signature=test"
    }

    try {
        $response = Invoke-RestMethod -Uri $AWS_ENDPOINT -Method POST -Headers $headers -Body $Body
        return $response
    }
    catch {
        Write-Host "❌ 請求失敗: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

# 輔助函數：發送 SQS 請求
function Invoke-SQSRequest {
    param(
        [string]$Action,
        [hashtable]$Parameters = @{}
    )

    $queryString = "Action=$Action"
    foreach ($key in $Parameters.Keys) {
        $queryString += "&$key=$($Parameters[$key])"
    }

    try {
        $response = Invoke-RestMethod -Uri "$AWS_ENDPOINT/?$queryString" -Method GET
        return $response
    }
    catch {
        Write-Host "❌ SQS 請求失敗: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

# 輔助函數：發送 Lambda 請求
function Invoke-LambdaRequest {
    param(
        [string]$Path,
        [string]$Method = "GET",
        [string]$Body = ""
    )

    $uri = "$AWS_ENDPOINT/2015-03-31$Path"

    try {
        if ($Method -eq "GET") {
            $response = Invoke-RestMethod -Uri $uri -Method GET
        }
        else {
            $response = Invoke-RestMethod -Uri $uri -Method $Method -Body $Body -ContentType "application/json"
        }
        return $response
    }
    catch {
        Write-Host "❌ Lambda 請求失敗: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

# 主功能函數
function Show-Menu {
    Write-Host "請選擇查詢類型：" -ForegroundColor Yellow
    Write-Host "1. DynamoDB 表查詢" -ForegroundColor Green
    Write-Host "2. SQS 佇列查詢" -ForegroundColor Green
    Write-Host "3. Lambda 函數查詢" -ForegroundColor Green
    Write-Host "4. EKS Handler API 測試" -ForegroundColor Green
    Write-Host "5. 完整狀態檢查" -ForegroundColor Green
    Write-Host "6. 數據統計分析" -ForegroundColor Green
    Write-Host "0. 結束程式" -ForegroundColor Red
    Write-Host ""
}

# DynamoDB 查詢功能
function Query-DynamoDB {
    Write-Host "🗂️ DynamoDB 表查詢" -ForegroundColor Cyan
    Write-Host "========================" -ForegroundColor Gray

    Write-Host "1. 列出所有表" -ForegroundColor Yellow
    $response = Invoke-DynamoDBRequest -Target "DynamoDB_20120810.ListTables"
    if ($response) {
        Write-Host "DynamoDB 表列表:" -ForegroundColor Green
        $response.TableNames | ForEach-Object { Write-Host "  - $_" -ForegroundColor Cyan }
    }

    Write-Host ""
    Write-Host "2. 掃描 command-records 表" -ForegroundColor Yellow
    $scanBody = @{
        TableName = "command-records"
        Limit     = 5
    } | ConvertTo-Json

    $response = Invoke-DynamoDBRequest -Target "DynamoDB_20120810.Scan" -Body $scanBody
    if ($response) {
        Write-Host "command-records 表內容 (前 5 筆):" -ForegroundColor Green
        $response.Items | ForEach-Object {
            $item = $_
            Write-Host "  交易ID: $($item.transaction_id.S)" -ForegroundColor Cyan
            Write-Host "  用戶ID: $($item.user_id.S)" -ForegroundColor Cyan
            Write-Host "  建立時間: $($item.created_at.N)" -ForegroundColor Cyan
            Write-Host "  ---" -ForegroundColor Gray
        }
        Write-Host "總記錄數: $($response.Count)" -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "3. 掃描 notification-records 表" -ForegroundColor Yellow
    $scanBody = @{
        TableName = "notification-records"
        Limit     = 5
    } | ConvertTo-Json

    $response = Invoke-DynamoDBRequest -Target "DynamoDB_20120810.Scan" -Body $scanBody
    if ($response) {
        Write-Host "notification-records 表內容 (前 5 筆):" -ForegroundColor Green
        $response.Items | ForEach-Object {
            $item = $_
            Write-Host "  用戶ID: $($item.user_id.S)" -ForegroundColor Cyan
            Write-Host "  推播標題: $($item.notification_title.S)" -ForegroundColor Cyan
            Write-Host "  狀態: $($item.status.S)" -ForegroundColor Cyan
            Write-Host "  平台: $($item.platform.S)" -ForegroundColor Cyan
            Write-Host "  ---" -ForegroundColor Gray
        }
        Write-Host "總記錄數: $($response.Count)" -ForegroundColor Green
    }
}

# SQS 查詢功能
function Query-SQS {
    Write-Host "📬 SQS 佇列查詢" -ForegroundColor Cyan
    Write-Host "========================" -ForegroundColor Gray

    try {
        $response = Invoke-RestMethod -Uri "$AWS_ENDPOINT/000000000000/" -Method GET
        if ($response) {
            Write-Host "SQS 佇列列表:" -ForegroundColor Green
            Write-Host $response -ForegroundColor Cyan
        }
    }
    catch {
        Write-Host "⚠️ 沒有找到 SQS 佇列或服務未啟用" -ForegroundColor Yellow
    }
}

# Lambda 查詢功能
function Query-Lambda {
    Write-Host "🔧 Lambda 函數查詢" -ForegroundColor Cyan
    Write-Host "========================" -ForegroundColor Gray

    Write-Host "1. 列出所有 Lambda 函數" -ForegroundColor Yellow
    $response = Invoke-LambdaRequest -Path "/functions"
    if ($response) {
        Write-Host "Lambda 函數列表:" -ForegroundColor Green
        $response.Functions | ForEach-Object {
            Write-Host "  - 函數名稱: $($_.FunctionName)" -ForegroundColor Cyan
            Write-Host "    運行時: $($_.Runtime)" -ForegroundColor Cyan
            Write-Host "    狀態: $($_.State)" -ForegroundColor Cyan
            Write-Host "    ---" -ForegroundColor Gray
        }
    }

    Write-Host ""
    Write-Host "2. 查詢 stream_processor_lambda 詳細資訊" -ForegroundColor Yellow
    $response = Invoke-LambdaRequest -Path "/functions/stream_processor_lambda"
    if ($response) {
        Write-Host "stream_processor_lambda 詳細資訊:" -ForegroundColor Green
        Write-Host "  函數名稱: $($response.Configuration.FunctionName)" -ForegroundColor Cyan
        Write-Host "  運行時: $($response.Configuration.Runtime)" -ForegroundColor Cyan
        Write-Host "  狀態: $($response.Configuration.State)" -ForegroundColor Cyan
        Write-Host "  記憶體: $($response.Configuration.MemorySize) MB" -ForegroundColor Cyan
        Write-Host "  超時: $($response.Configuration.Timeout) 秒" -ForegroundColor Cyan
    }

    Write-Host ""
    Write-Host "3. 測試 Lambda 函數調用" -ForegroundColor Yellow
    $testPayload = @{
        test = "PowerShell 測試"
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$AWS_ENDPOINT/2015-03-31/functions/stream_processor_lambda/invocations" -Method POST -Body $testPayload -ContentType "application/json"
        Write-Host "Lambda 調用結果:" -ForegroundColor Green
        Write-Host $response -ForegroundColor Cyan
    }
    catch {
        Write-Host "⚠️ Lambda 調用失敗: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# EKS Handler API 測試
function Test-EKSHandler {
    Write-Host "🚀 EKS Handler API 測試" -ForegroundColor Cyan
    Write-Host "========================" -ForegroundColor Gray

    Write-Host "1. 健康檢查" -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri $EKS_ENDPOINT -Method GET
        Write-Host "健康檢查結果:" -ForegroundColor Green
        Write-Host ($response | ConvertTo-Json -Depth 10) -ForegroundColor Cyan
    }
    catch {
        Write-Host "❌ EKS Handler 無法連接: $($_.Exception.Message)" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "2. 查詢所有推播記錄" -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri "$EKS_ENDPOINT/query/user" -Method GET
        Write-Host "查詢結果:" -ForegroundColor Green
        Write-Host "  成功: $($response.success)" -ForegroundColor Cyan
        Write-Host "  記錄數: $($response.count)" -ForegroundColor Cyan
        if ($response.items -and $response.items.Count -gt 0) {
            Write-Host "  第一筆記錄範例:" -ForegroundColor Cyan
            Write-Host ($response.items[0] | ConvertTo-Json) -ForegroundColor White
        }
    }
    catch {
        Write-Host "❌ API 查詢失敗: $($_.Exception.Message)" -ForegroundColor Red
    }

    Write-Host ""
    Write-Host "3. 查詢特定用戶 (stream_test_user)" -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri "$EKS_ENDPOINT/query/user?user_id=stream_test_user" -Method GET
        Write-Host "特定用戶查詢結果:" -ForegroundColor Green
        Write-Host "  記錄數: $($response.count)" -ForegroundColor Cyan
        if ($response.items) {
            $response.items | ForEach-Object {
                Write-Host "  - 用戶: $($_.user_id)" -ForegroundColor Cyan
                Write-Host "    標題: $($_.notification_title)" -ForegroundColor Cyan
                Write-Host "    狀態: $($_.status)" -ForegroundColor Cyan
            }
        }
    }
    catch {
        Write-Host "❌ 特定用戶查詢失敗: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# 完整狀態檢查
function Check-AllStatus {
    Write-Host "🔍 完整狀態檢查" -ForegroundColor Cyan
    Write-Host "========================" -ForegroundColor Gray

    # 檢查 Docker 容器
    Write-Host "1. Docker 容器狀態" -ForegroundColor Yellow
    try {
        $containers = docker ps --format "table {{.Names}}\t{{.Status}}" 2>$null
        if ($containers) {
            Write-Host $containers -ForegroundColor Cyan
        }
        else {
            Write-Host "⚠️ 無法獲取 Docker 容器資訊" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "❌ Docker 命令失敗" -ForegroundColor Red
    }

    Write-Host ""

    # 檢查 LocalStack 服務
    Write-Host "2. LocalStack 服務狀態" -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri "$AWS_ENDPOINT/health" -Method GET
        Write-Host "LocalStack 健康狀態:" -ForegroundColor Green
        $response.services | Get-Member -MemberType NoteProperty | ForEach-Object {
            $serviceName = $_.Name
            $status = $response.services.$serviceName
            $statusColor = if ($status -eq "available") { "Green" } else { "Red" }
            Write-Host "  $serviceName : $status" -ForegroundColor $statusColor
        }
    }
    catch {
        Write-Host "❌ LocalStack 健康檢查失敗" -ForegroundColor Red
    }

    Write-Host ""

    # 檢查表數據
    Write-Host "3. 數據統計" -ForegroundColor Yellow

    # 命令表統計
    $commandCountBody = @{
        TableName = "command-records"
        Select    = "COUNT"
    } | ConvertTo-Json

    $commandResponse = Invoke-DynamoDBRequest -Target "DynamoDB_20120810.Scan" -Body $commandCountBody
    $commandCount = if ($commandResponse) { $commandResponse.Count } else { "N/A" }

    # 查詢表統計
    $queryCountBody = @{
        TableName = "notification-records"
        Select    = "COUNT"
    } | ConvertTo-Json

    $queryResponse = Invoke-DynamoDBRequest -Target "DynamoDB_20120810.Scan" -Body $queryCountBody
    $queryCount = if ($queryResponse) { $queryResponse.Count } else { "N/A" }

    Write-Host "  命令表記錄數: $commandCount" -ForegroundColor Cyan
    Write-Host "  查詢表記錄數: $queryCount" -ForegroundColor Cyan

    if ($commandCount -ne "N/A" -and $queryCount -ne "N/A") {
        if ([int]$queryCount -le [int]$commandCount) {
            Write-Host "  ✅ 數據一致性正常" -ForegroundColor Green
        }
        else {
            Write-Host "  ⚠️ 數據一致性異常" -ForegroundColor Yellow
        }
    }
}

# 數據統計分析
function Analyze-Data {
    Write-Host "📊 數據統計分析" -ForegroundColor Cyan
    Write-Host "========================" -ForegroundColor Gray

    Write-Host "1. 按平台統計推播記錄" -ForegroundColor Yellow

    # 掃描所有通知記錄並分析
    $scanBody = @{
        TableName = "notification-records"
    } | ConvertTo-Json

    $response = Invoke-DynamoDBRequest -Target "DynamoDB_20120810.Scan" -Body $scanBody
    if ($response -and $response.Items) {
        $platforms = @{}
        $statuses = @{}

        $response.Items | ForEach-Object {
            $platform = $_.platform.S
            $status = $_.status.S

            if ($platforms.ContainsKey($platform)) {
                $platforms[$platform]++
            }
            else {
                $platforms[$platform] = 1
            }

            if ($statuses.ContainsKey($status)) {
                $statuses[$status]++
            }
            else {
                $statuses[$status] = 1
            }
        }

        Write-Host "按平台統計:" -ForegroundColor Green
        $platforms.GetEnumerator() | Sort-Object Value -Descending | ForEach-Object {
            Write-Host "  $($_.Key): $($_.Value) 筆" -ForegroundColor Cyan
        }

        Write-Host ""
        Write-Host "2. 按狀態統計推播記錄" -ForegroundColor Yellow
        Write-Host "按狀態統計:" -ForegroundColor Green
        $statuses.GetEnumerator() | Sort-Object Value -Descending | ForEach-Object {
            Write-Host "  $($_.Key): $($_.Value) 筆" -ForegroundColor Cyan
        }

        Write-Host ""
        Write-Host "3. 最新 5 筆記錄" -ForegroundColor Yellow
        $sortedItems = $response.Items | Sort-Object { [long]$_.created_at.N } -Descending | Select-Object -First 5
        $sortedItems | ForEach-Object {
            $timestamp = [long]$_.created_at.N
            $date = [DateTimeOffset]::FromUnixTimeMilliseconds($timestamp).ToString("yyyy-MM-dd HH:mm:ss")
            Write-Host "  $date - $($_.user_id.S) - $($_.notification_title.S)" -ForegroundColor Cyan
        }
    }
    else {
        Write-Host "⚠️ 無法獲取數據進行分析" -ForegroundColor Yellow
    }
}

# 主程式循環
do {
    Show-Menu
    $choice = Read-Host "請輸入選項 (0-6)"

    switch ($choice) {
        "1" { Query-DynamoDB }
        "2" { Query-SQS }
        "3" { Query-Lambda }
        "4" { Test-EKSHandler }
        "5" { Check-AllStatus }
        "6" { Analyze-Data }
        "0" {
            Write-Host "👋 謝謝使用！" -ForegroundColor Green
            break
        }
        default {
            Write-Host "❌ 無效選項，請重新選擇" -ForegroundColor Red
        }
    }

    if ($choice -ne "0") {
        Write-Host ""
        Read-Host "按 Enter 返回主選單"
        Clear-Host
    }
} while ($choice -ne "0")
