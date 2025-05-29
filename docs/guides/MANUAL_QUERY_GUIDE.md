# 🔍 手動查詢指南 - SQS、DynamoDB 和 AWS 服務

## 📋 查詢工具選擇

### 🛠️ 方式一：AWS CLI（推薦）
如果已安裝 AWS CLI：
```bash
# 設定本地端點
export AWS_ENDPOINT=http://localhost:4566
```

### 🛠️ 方式二：LocalStack Web UI
訪問：http://localhost:4566 （如果 LocalStack Pro）

### 🛠️ 方式三：直接 HTTP API 調用
使用 curl 或 PowerShell 直接調用 LocalStack API

---

## 🗂️ DynamoDB 查詢

### 📊 列出所有表
```bash
# AWS CLI 方式
aws --endpoint-url=http://localhost:4566 dynamodb list-tables

# curl 方式
curl -X POST http://localhost:4566/ \
  -H "Content-Type: application/x-amz-json-1.0" \
  -H "X-Amz-Target: DynamoDB_20120810.ListTables" \
  -d '{}'

# PowerShell 方式
$headers = @{
    "Content-Type" = "application/x-amz-json-1.0"
    "X-Amz-Target" = "DynamoDB_20120810.ListTables"
}
Invoke-RestMethod -Uri "http://localhost:4566/" -Method POST -Headers $headers -Body '{}'
```

### 📋 掃描表數據

#### 查詢命令表 (command-records)
```bash
# AWS CLI - 掃描所有記錄
aws --endpoint-url=http://localhost:4566 dynamodb scan --table-name command-records

# AWS CLI - 只統計數量
aws --endpoint-url=http://localhost:4566 dynamodb scan \
  --table-name command-records \
  --select COUNT

# AWS CLI - 限制返回數量
aws --endpoint-url=http://localhost:4566 dynamodb scan \
  --table-name command-records \
  --limit 5

# curl 方式
curl -X POST http://localhost:4566/ \
  -H "Content-Type: application/x-amz-json-1.0" \
  -H "X-Amz-Target: DynamoDB_20120810.Scan" \
  -d '{
    "TableName": "command-records",
    "Limit": 10
  }'
```

#### 查詢通知表 (notification-records)
```bash
# AWS CLI - 掃描所有記錄
aws --endpoint-url=http://localhost:4566 dynamodb scan --table-name notification-records

# AWS CLI - 查詢特定用戶
aws --endpoint-url=http://localhost:4566 dynamodb query \
  --table-name notification-records \
  --key-condition-expression "user_id = :user_id" \
  --expression-attribute-values '{
    ":user_id": {"S": "stream_test_user"}
  }'

# AWS CLI - 查詢特定用戶的最新記錄
aws --endpoint-url=http://localhost:4566 dynamodb query \
  --table-name notification-records \
  --key-condition-expression "user_id = :user_id" \
  --expression-attribute-values '{
    ":user_id": {"S": "stream_test_user"}
  }' \
  --scan-index-forward false \
  --limit 1
```

### 🔍 查詢特定記錄
```bash
# 根據主鍵查詢
aws --endpoint-url=http://localhost:4566 dynamodb get-item \
  --table-name command-records \
  --key '{
    "transaction_id": {"S": "tx_stream_test_1748496975"},
    "created_at": {"N": "1748496975544"}
  }'

# 條件查詢
aws --endpoint-url=http://localhost:4566 dynamodb scan \
  --table-name notification-records \
  --filter-expression "platform = :platform AND #status = :status" \
  --expression-attribute-names '{
    "#status": "status"
  }' \
  --expression-attribute-values '{
    ":platform": {"S": "IOS"},
    ":status": {"S": "SENT"}
  }'
```

### 📈 表詳細資訊
```bash
# 查看表結構和狀態
aws --endpoint-url=http://localhost:4566 dynamodb describe-table \
  --table-name command-records

# 查看 Stream 配置
aws --endpoint-url=http://localhost:4566 dynamodb describe-table \
  --table-name command-records \
  --query 'Table.StreamSpecification'

# 查看表的索引資訊
aws --endpoint-url=http://localhost:4566 dynamodb describe-table \
  --table-name notification-records \
  --query 'Table.GlobalSecondaryIndexes'
```

---

## 📬 SQS 佇列查詢

### 📋 列出所有佇列
```bash
# AWS CLI 方式
aws --endpoint-url=http://localhost:4566 sqs list-queues

# curl 方式
curl "http://localhost:4566/000000000000/"

# PowerShell 方式
Invoke-RestMethod -Uri "http://localhost:4566/000000000000/"
```

### 📨 檢查佇列內容
```bash
# 接收訊息（不刪除）
aws --endpoint-url=http://localhost:4566 sqs receive-message \
  --queue-url http://localhost:4566/000000000000/your-queue-name \
  --max-number-of-messages 10

# 檢查佇列屬性
aws --endpoint-url=http://localhost:4566 sqs get-queue-attributes \
  --queue-url http://localhost:4566/000000000000/your-queue-name \
  --attribute-names All

# 清空佇列
aws --endpoint-url=http://localhost:4566 sqs purge-queue \
  --queue-url http://localhost:4566/000000000000/your-queue-name
```

### 📊 佇列統計
```bash
# 查看佇列中的訊息數量
aws --endpoint-url=http://localhost:4566 sqs get-queue-attributes \
  --queue-url http://localhost:4566/000000000000/your-queue-name \
  --attribute-names ApproximateNumberOfMessages,ApproximateNumberOfMessagesNotVisible
```

---

## 🔧 Lambda 函數查詢

### 📋 列出所有函數
```bash
# AWS CLI 方式
aws --endpoint-url=http://localhost:4566 lambda list-functions

# 只顯示函數名稱
aws --endpoint-url=http://localhost:4566 lambda list-functions \
  --query 'Functions[].FunctionName' \
  --output table

# curl 方式
curl http://localhost:4566/2015-03-31/functions/
```

### 🔍 查詢特定函數
```bash
# 查看函數配置
aws --endpoint-url=http://localhost:4566 lambda get-function \
  --function-name stream_processor_lambda

# 查看函數程式碼
aws --endpoint-url=http://localhost:4566 lambda get-function \
  --function-name stream_processor_lambda \
  --query 'Code'

# 查看環境變數
aws --endpoint-url=http://localhost:4566 lambda get-function-configuration \
  --function-name stream_processor_lambda \
  --query 'Environment'
```

### 🧪 測試 Lambda 函數
```bash
# 同步調用
aws --endpoint-url=http://localhost:4566 lambda invoke \
  --function-name stream_processor_lambda \
  --payload '{"test": "data"}' \
  response.json

# 查看回應
cat response.json

# 異步調用
aws --endpoint-url=http://localhost:4566 lambda invoke \
  --function-name stream_processor_lambda \
  --invocation-type Event \
  --payload '{"test": "data"}' \
  response.json
```

### 📊 函數事件源映射
```bash
# 列出所有事件源映射
aws --endpoint-url=http://localhost:4566 lambda list-event-source-mappings

# 查詢特定函數的事件源
aws --endpoint-url=http://localhost:4566 lambda list-event-source-mappings \
  --function-name stream_processor_lambda

# 查看 DynamoDB Stream 映射詳情
aws --endpoint-url=http://localhost:4566 lambda list-event-source-mappings \
  --function-name stream_processor_lambda \
  --query 'EventSourceMappings[0]'
```

---

## 📡 API Gateway 查詢

### 📋 列出所有 API
```bash
# 列出 REST API
aws --endpoint-url=http://localhost:4566 apigateway get-rest-apis

# 列出 API 詳細資訊
aws --endpoint-url=http://localhost:4566 apigateway get-rest-apis \
  --query 'items[].[name,id,createdDate]' \
  --output table
```

### 🔍 查詢 API 結構
```bash
# 假設您的 API ID 是 "abcd1234"
API_ID="your-api-id"

# 查看 API 資源
aws --endpoint-url=http://localhost:4566 apigateway get-resources \
  --rest-api-id $API_ID

# 查看特定資源的方法
aws --endpoint-url=http://localhost:4566 apigateway get-method \
  --rest-api-id $API_ID \
  --resource-id "resource-id" \
  --http-method GET
```

---

## 🌊 DynamoDB Streams 查詢

### 📋 列出所有 Streams
```bash
# 列出 DynamoDB Streams
aws --endpoint-url=http://localhost:4566 dynamodbstreams list-streams

# 查看特定表的 Stream
aws --endpoint-url=http://localhost:4566 dynamodbstreams describe-stream \
  --stream-arn "arn:aws:dynamodb:us-east-1:000000000000:table/command-records/stream/..."
```

### 📊 Stream 記錄查詢
```bash
# 獲取 Stream 的 Shard 資訊
aws --endpoint-url=http://localhost:4566 dynamodbstreams describe-stream \
  --stream-arn "your-stream-arn" \
  --query 'StreamDescription.Shards'

# 讀取 Stream 記錄
aws --endpoint-url=http://localhost:4566 dynamodbstreams get-records \
  --shard-iterator "your-shard-iterator"
```

---

## 🛠️ 實用查詢腳本

### 📋 完整狀態檢查腳本（PowerShell）
```powershell
# 檢查所有服務狀態
function Check-AllServices {
    Write-Host "🔍 檢查 DynamoDB 表..." -ForegroundColor Yellow
    aws --endpoint-url=http://localhost:4566 dynamodb list-tables
    
    Write-Host "`n📬 檢查 SQS 佇列..." -ForegroundColor Yellow
    aws --endpoint-url=http://localhost:4566 sqs list-queues
    
    Write-Host "`n🔧 檢查 Lambda 函數..." -ForegroundColor Yellow
    aws --endpoint-url=http://localhost:4566 lambda list-functions --query 'Functions[].FunctionName'
    
    Write-Host "`n📡 檢查 API Gateway..." -ForegroundColor Yellow
    aws --endpoint-url=http://localhost:4566 apigateway get-rest-apis --query 'items[].[name,id]'
}

Check-AllServices
```

### 📊 數據統計腳本
```bash
#!/bin/bash
echo "📊 DynamoDB 表統計"
echo "===================="

# 命令表統計
COMMAND_COUNT=$(aws --endpoint-url=http://localhost:4566 dynamodb scan \
  --table-name command-records \
  --select COUNT \
  --query 'Count' \
  --output text)
echo "命令表記錄數: $COMMAND_COUNT"

# 查詢表統計
QUERY_COUNT=$(aws --endpoint-url=http://localhost:4566 dynamodb scan \
  --table-name notification-records \
  --select COUNT \
  --query 'Count' \
  --output text)
echo "查詢表記錄數: $QUERY_COUNT"

# 數據一致性檢查
if [ "$QUERY_COUNT" -le "$COMMAND_COUNT" ]; then
    echo "✅ 數據一致性正常 (Query: $QUERY_COUNT <= Command: $COMMAND_COUNT)"
else
    echo "⚠️ 數據一致性異常 (Query: $QUERY_COUNT > Command: $COMMAND_COUNT)"
fi
```

---

## 🚀 一鍵查詢命令

### 快速檢查所有表內容
```bash
# 顯示所有表的前 5 筆記錄
for table in command-records notification-records; do
    echo "📋 表: $table"
    echo "=================="
    aws --endpoint-url=http://localhost:4566 dynamodb scan \
      --table-name $table \
      --limit 5
    echo ""
done
```

### 查詢最新的同步記錄
```bash
# 查詢最近同步的記錄
aws --endpoint-url=http://localhost:4566 dynamodb scan \
  --table-name notification-records \
  --limit 1 \
  --query 'Items[0]'
```

---

## 🎯 常用查詢模式

### 🔍 按時間範圍查詢
```bash
# 查詢過去 1 小時的記錄
HOUR_AGO=$(($(date +%s) - 3600))000

aws --endpoint-url=http://localhost:4566 dynamodb scan \
  --table-name notification-records \
  --filter-expression "created_at > :timestamp" \
  --expression-attribute-values '{
    ":timestamp": {"N": "'$HOUR_AGO'"}
  }'
```

### 📊 按狀態統計
```bash
# 統計不同狀態的記錄數
for status in PENDING SENT FAILED; do
    count=$(aws --endpoint-url=http://localhost:4566 dynamodb scan \
      --table-name notification-records \
      --filter-expression "#status = :status" \
      --expression-attribute-names '{"#status": "status"}' \
      --expression-attribute-values '{":status": {"S": "'$status'"}}' \
      --select COUNT \
      --query 'Count' \
      --output text)
    echo "$status: $count 筆記錄"
done
```

---

**💡 提示：記得根據您的實際環境調整表名稱和欄位名稱！** 