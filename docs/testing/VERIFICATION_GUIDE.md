# 🔍 AWS Hexagon Notify Test - 完整驗證測試指南

## 📋 測試環境檢查清單

### ✅ 前置條件
- [x] Docker Desktop 正在運行
- [x] LocalStack 容器已啟動 (port 4566)
- [x] EKS Handler 容器已啟動 (port 8000)
- [x] DynamoDB 表已創建並初始化
- [x] Lambda 函數已部署

---

## 🚀 快速驗證步驟

### 1. **服務狀態檢查**

#### 檢查 Docker 容器
```bash
# 查看運行中的容器
docker ps

# 應該看到兩個容器：
# - eks-handler (port 8000)
# - localstack (port 4566)
```

#### 檢查服務健康狀態
```bash
# 檢查 EKS Handler 健康狀態
curl http://localhost:8000/

# 檢查 LocalStack 健康狀態
curl http://localhost:4566/health
```

### 2. **DynamoDB 表狀態檢查**

#### 列出所有表
```bash
aws --endpoint-url=http://localhost:4566 dynamodb list-tables
```

#### 檢查命令表記錄數
```bash
aws --endpoint-url=http://localhost:4566 dynamodb scan \
  --table-name command-records \
  --select COUNT
```

#### 檢查查詢表記錄數
```bash
aws --endpoint-url=http://localhost:4566 dynamodb scan \
  --table-name notification-records \
  --select COUNT
```

### 3. **Lambda 函數檢查**

#### 列出所有 Lambda 函數
```bash
aws --endpoint-url=http://localhost:4566 lambda list-functions
```

#### 檢查 Stream Processor Lambda
```bash
aws --endpoint-url=http://localhost:4566 lambda get-function \
  --function-name stream_processor_lambda
```

### 4. **DynamoDB Stream 狀態檢查**

#### 檢查 Stream 配置
```bash
aws --endpoint-url=http://localhost:4566 dynamodb describe-table \
  --table-name command-records \
  --query 'Table.StreamSpecification'
```

#### 檢查事件源映射
```bash
aws --endpoint-url=http://localhost:4566 lambda list-event-source-mappings
```

---

## 🧪 核心功能測試

### 測試 1: EKS Handler 直接調用
```bash
# 測試健康檢查端點
curl -X GET http://localhost:8000/

# 測試查詢用戶推播記錄
curl -X GET "http://localhost:8000/query/user?user_id=stream_test_user"

# 測試查詢所有推播記錄
curl -X GET "http://localhost:8000/query/user"
```

### 測試 2: DynamoDB 數據查詢

#### 查詢命令表 (Command Side)
```bash
# 掃描所有記錄
aws --endpoint-url=http://localhost:4566 dynamodb scan \
  --table-name command-records

# 查詢特定交易ID
aws --endpoint-url=http://localhost:4566 dynamodb get-item \
  --table-name command-records \
  --key '{
    "transaction_id": {"S": "tx_stream_test_1748489873"},
    "created_at": {"N": "1748489873870"}
  }'
```

#### 查詢通知表 (Query Side)
```bash
# 掃描所有記錄
aws --endpoint-url=http://localhost:4566 dynamodb scan \
  --table-name notification-records

# 查詢特定用戶記錄
aws --endpoint-url=http://localhost:4566 dynamodb query \
  --table-name notification-records \
  --key-condition-expression "user_id = :user_id" \
  --expression-attribute-values '{
    ":user_id": {"S": "stream_test_user"}
  }'
```

### 測試 3: CQRS Stream 處理功能

#### 使用現有測試腳本
```bash
# 執行 CQRS Stream 測試
python test_stream.py
```

#### 手動測試 Stream 處理
```bash
# 1. 記錄當前查詢表記錄數
aws --endpoint-url=http://localhost:4566 dynamodb scan \
  --table-name notification-records \
  --select COUNT

# 2. 插入新記錄到命令表
aws --endpoint-url=http://localhost:4566 dynamodb put-item \
  --table-name command-records \
  --item '{
    "transaction_id": {"S": "manual_test_'$(date +%s)'"},
    "created_at": {"N": "'$(date +%s%3N)'"},
    "user_id": {"S": "manual_test_user"},
    "marketing_id": {"S": "manual_campaign"},
    "notification_title": {"S": "手動測試推播"},
    "platform": {"S": "ANDROID"},
    "status": {"S": "PENDING"}
  }'

# 3. 等待 5 秒讓 Stream 處理
echo "等待 Stream 處理..."
sleep 5

# 4. 檢查查詢表是否有新記錄
aws --endpoint-url=http://localhost:4566 dynamodb scan \
  --table-name notification-records \
  --select COUNT

# 5. 查詢具體的同步記錄
aws --endpoint-url=http://localhost:4566 dynamodb query \
  --table-name notification-records \
  --key-condition-expression "user_id = :user_id" \
  --expression-attribute-values '{
    ":user_id": {"S": "manual_test_user"}
  }'
```

---

## 🔧 API Gateway 測試

### 測試 Lambda 函數直接調用
```bash
# 測試 Query Lambda
aws --endpoint-url=http://localhost:4566 lambda invoke \
  --function-name query_lambda \
  --payload '{"user_id": "stream_test_user"}' \
  output.json && cat output.json

# 測試 Query Result Lambda
aws --endpoint-url=http://localhost:4566 lambda invoke \
  --function-name query_result_lambda \
  --payload '{"user_id": "stream_test_user"}' \
  output.json && cat output.json
```

### 測試 API Gateway 端點
```bash
# 列出 API Gateway
aws --endpoint-url=http://localhost:4566 apigateway get-rest-apis

# 如果 API Gateway 正常，測試端點
# (需要替換實際的 API ID)
curl -X GET "http://localhost:4566/restapis/{api-id}/test/_user_request_/query/user"
```

---

## 📊 性能和監控測試

### 測試數據一致性
```bash
# 檢查兩個表的記錄數是否合理（Query 表 <= Command 表）
echo "命令表記錄數:"
aws --endpoint-url=http://localhost:4566 dynamodb scan \
  --table-name command-records \
  --select COUNT \
  --query 'Count'

echo "查詢表記錄數:"
aws --endpoint-url=http://localhost:4566 dynamodb scan \
  --table-name notification-records \
  --select COUNT \
  --query 'Count'
```

### 測試查詢性能
```bash
# 測試大量數據查詢性能
time curl -X GET "http://localhost:8000/query/user"

# 測試特定用戶查詢性能
time curl -X GET "http://localhost:8000/query/user?user_id=stream_test_user"
```

---

## 🚨 故障排除指令

### 查看容器日誌
```bash
# 查看 EKS Handler 日誌
docker logs eks-handler

# 查看 LocalStack 日誌
docker logs localstack-query-service

# 持續監控日誌
docker logs -f eks-handler
```

### 重啟服務
```bash
# 重啟 EKS Handler
docker restart eks-handler

# 重啟 LocalStack
docker restart localstack-query-service

# 重啟所有服務
docker compose restart
```

### 清理和重新初始化
```bash
# 停止所有服務
docker compose down

# 清理 volume 數據
docker volume prune

# 重新啟動並初始化
docker compose up -d
sleep 10
./infra/localstack/setup.sh
```

---

## 🎯 預期結果參考

### ✅ 正常運行指標
- **EKS Handler**: HTTP 200 響應，JSON 格式數據
- **DynamoDB 表**: 兩個表都存在且有數據
- **Stream 處理**: 5 秒內數據同步成功
- **Lambda 函數**: 3 個函數正常部署
- **數據一致性**: Query 表記錄數 <= Command 表記錄數

### ⚠️ 常見問題
- **502 錯誤**: API Gateway 整合問題，但 EKS Handler 直接調用正常
- **數據不同步**: 檢查 DynamoDB Stream 和事件源映射
- **容器無法啟動**: 檢查端口占用和 Docker 資源

---

## 📝 測試報告範本

### 測試執行記錄
```
測試時間: _____________
測試人員: _____________

服務狀態:
[ ] EKS Handler 正常運行
[ ] LocalStack 正常運行
[ ] DynamoDB 表正常訪問

功能測試:
[ ] EKS Handler 查詢成功
[ ] DynamoDB Stream 處理成功
[ ] 數據同步正常
[ ] Lambda 函數運行正常

性能測試:
[ ] 查詢響應時間 < 1 秒
[ ] Stream 處理延遲 < 5 秒
[ ] 數據一致性 100%

問題記錄:
_________________________________
_________________________________
```

---

**驗證完成後，您將確認整個 CQRS 架構正常運行！** 🎉 