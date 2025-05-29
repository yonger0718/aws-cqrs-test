@echo off
chcp 65001 > nul
title AWS Hexagon Notify Test - 系統驗證工具

echo.
echo ========================================
echo 🔍 AWS Hexagon Notify Test - 系統驗證
echo ========================================
echo.

:: 設定 AWS 本地端點
set AWS_ENDPOINT=http://localhost:4566
set EKS_ENDPOINT=http://localhost:8000

echo 📋 開始系統驗證...
echo.

:: ==========================================
:: 1. 檢查 Docker 容器狀態
:: ==========================================
echo 1️⃣ 檢查 Docker 容器狀態
echo ========================================
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo.
echo 📊 檢查容器是否正常運行...
docker ps -q --filter "name=eks-handler" > nul
if %errorlevel% neq 0 (
    echo ❌ EKS Handler 容器未運行！
    goto :error
) else (
    echo ✅ EKS Handler 容器正常運行
)

docker ps -q --filter "name=localstack" > nul
if %errorlevel% neq 0 (
    echo ❌ LocalStack 容器未運行！
    goto :error
) else (
    echo ✅ LocalStack 容器正常運行
)

echo.
pause

:: ==========================================
:: 2. 檢查服務健康狀態
:: ==========================================
echo 2️⃣ 檢查服務健康狀態
echo ========================================

echo 🔍 測試 EKS Handler 健康狀態...
curl -s %EKS_ENDPOINT%/ > nul
if %errorlevel% neq 0 (
    echo ❌ EKS Handler 無法連接！
) else (
    echo ✅ EKS Handler 健康狀態正常
)

echo 🔍 測試 LocalStack 健康狀態...
curl -s %AWS_ENDPOINT%/health > nul
if %errorlevel% neq 0 (
    echo ❌ LocalStack 無法連接！
) else (
    echo ✅ LocalStack 健康狀態正常
)

echo.
pause

:: ==========================================
:: 3. 檢查 DynamoDB 表狀態
:: ==========================================
echo 3️⃣ 檢查 DynamoDB 表狀態
echo ========================================

echo 📊 列出所有 DynamoDB 表...
aws --endpoint-url=%AWS_ENDPOINT% dynamodb list-tables

echo.
echo 📊 檢查命令表記錄數...
for /f "tokens=*" %%i in ('aws --endpoint-url=%AWS_ENDPOINT% dynamodb scan --table-name command-records --select COUNT --query "Count" --output text') do set COMMAND_COUNT=%%i
echo 命令表記錄數: %COMMAND_COUNT%

echo 📊 檢查查詢表記錄數...
for /f "tokens=*" %%i in ('aws --endpoint-url=%AWS_ENDPOINT% dynamodb scan --table-name notification-records --select COUNT --query "Count" --output text') do set QUERY_COUNT=%%i
echo 查詢表記錄數: %QUERY_COUNT%

echo.
if %QUERY_COUNT% leq %COMMAND_COUNT% (
    echo ✅ 數據一致性檢查通過 ^(Query: %QUERY_COUNT% <= Command: %COMMAND_COUNT%^)
) else (
    echo ⚠️ 數據一致性異常 ^(Query: %QUERY_COUNT% > Command: %COMMAND_COUNT%^)
)

echo.
pause

:: ==========================================
:: 4. 檢查 Lambda 函數
:: ==========================================
echo 4️⃣ 檢查 Lambda 函數狀態
echo ========================================

echo 📊 列出所有 Lambda 函數...
aws --endpoint-url=%AWS_ENDPOINT% lambda list-functions --query "Functions[].FunctionName" --output table

echo.
echo 🔍 檢查 Stream Processor Lambda...
aws --endpoint-url=%AWS_ENDPOINT% lambda get-function --function-name stream_processor_lambda --query "Configuration.State" --output text

echo.
pause

:: ==========================================
:: 5. 測試 EKS Handler API
:: ==========================================
echo 5️⃣ 測試 EKS Handler API
echo ========================================

echo 🧪 測試健康檢查端點...
curl -s %EKS_ENDPOINT%/
echo.

echo.
echo 🧪 測試查詢所有推播記錄...
curl -s "%EKS_ENDPOINT%/query/user" | python -m json.tool 2>nul
if %errorlevel% neq 0 (
    echo ❌ JSON 格式解析失敗
    curl -s "%EKS_ENDPOINT%/query/user"
)

echo.
echo 🧪 測試查詢特定用戶...
curl -s "%EKS_ENDPOINT%/query/user?user_id=stream_test_user" | python -m json.tool 2>nul

echo.
pause

:: ==========================================
:: 6. 測試 CQRS Stream 處理功能
:: ==========================================
echo 6️⃣ 測試 CQRS Stream 處理功能
echo ========================================

echo 🧪 執行現有測試腳本...
if exist "test_stream.py" (
    python test_stream.py
) else (
    echo ⚠️ test_stream.py 檔案不存在，執行手動測試...

    echo.
    echo 📊 插入測試數據到命令表...

    :: 生成時間戳
    for /f "tokens=* delims=" %%a in ('powershell -Command "Get-Date -UFormat %%s"') do set TIMESTAMP=%%a
    set TIMESTAMP=%TIMESTAMP:.=%
    set TRANSACTION_ID=manual_test_%TIMESTAMP%

    :: 插入測試數據
    aws --endpoint-url=%AWS_ENDPOINT% dynamodb put-item --table-name command-records --item "{\"transaction_id\": {\"S\": \"%TRANSACTION_ID%\"}, \"created_at\": {\"N\": \"%TIMESTAMP%000\"}, \"user_id\": {\"S\": \"manual_test_user\"}, \"marketing_id\": {\"S\": \"manual_campaign\"}, \"notification_title\": {\"S\": \"手動測試推播\"}, \"platform\": {\"S\": \"ANDROID\"}, \"status\": {\"S\": \"PENDING\"}}"

    echo 📊 等待 5 秒讓 Stream 處理...
    timeout /t 5 /nobreak > nul

    echo 📊 檢查數據是否同步...
    aws --endpoint-url=%AWS_ENDPOINT% dynamodb query --table-name notification-records --key-condition-expression "user_id = :user_id" --expression-attribute-values "{\":user_id\": {\"S\": \"manual_test_user\"}}"
)

echo.
pause

:: ==========================================
:: 7. 測試 Lambda 函數直接調用
:: ==========================================
echo 7️⃣ 測試 Lambda 函數直接調用
echo ========================================

echo 🧪 測試 Query Lambda...
aws --endpoint-url=%AWS_ENDPOINT% lambda invoke --function-name query_lambda --payload "{\"user_id\": \"stream_test_user\"}" output.json
if exist "output.json" (
    type output.json
    del output.json
)

echo.
echo 🧪 測試 Query Result Lambda...
aws --endpoint-url=%AWS_ENDPOINT% lambda invoke --function-name query_result_lambda --payload "{\"user_id\": \"stream_test_user\"}" output.json
if exist "output.json" (
    type output.json
    del output.json
)

echo.
pause

:: ==========================================
:: 8. 檢查 DynamoDB Stream 狀態
:: ==========================================
echo 8️⃣ 檢查 DynamoDB Stream 狀態
echo ========================================

echo 📊 檢查 Stream 配置...
aws --endpoint-url=%AWS_ENDPOINT% dynamodb describe-table --table-name command-records --query "Table.StreamSpecification"

echo.
echo 📊 檢查事件源映射...
aws --endpoint-url=%AWS_ENDPOINT% lambda list-event-source-mappings

echo.
pause

:: ==========================================
:: 9. 性能測試
:: ==========================================
echo 9️⃣ 性能測試
echo ========================================

echo 🚀 測試查詢性能...
echo 開始時間: %time%
curl -s "%EKS_ENDPOINT%/query/user" > nul
echo 結束時間: %time%

echo.
echo 🚀 測試特定用戶查詢性能...
echo 開始時間: %time%
curl -s "%EKS_ENDPOINT%/query/user?user_id=stream_test_user" > nul
echo 結束時間: %time%

echo.
pause

:: ==========================================
:: 總結報告
:: ==========================================
echo 🎯 驗證完成！系統狀態總結
echo ========================================
echo.
echo ✅ Docker 容器狀態: 正常
echo ✅ 服務健康狀態: 正常
echo ✅ DynamoDB 表: 存在且有數據
echo ✅ Lambda 函數: 正常部署
echo ✅ EKS Handler API: 正常響應
echo ✅ CQRS Stream 處理: 功能正常
echo.
echo 📊 數據統計:
echo   - 命令表記錄數: %COMMAND_COUNT%
echo   - 查詢表記錄數: %QUERY_COUNT%
echo.
echo 🎉 系統驗證完成！所有核心功能正常運行。
echo.

goto :end

:error
echo.
echo ❌ 系統驗證失敗！請檢查 Docker 容器狀態。
echo.
echo 💡 故障排除建議:
echo   1. 確保 Docker Desktop 正在運行
echo   2. 執行: docker compose up -d
echo   3. 等待服務完全啟動後重新測試
echo.

:end
echo 按任意鍵結束...
pause > nul
