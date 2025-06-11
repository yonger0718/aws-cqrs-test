# Lambda 測試指南

本指南說明如何在您的 CQRS 架構中對 Lambda 函數進行測試，使用 AWS 提供的標準事件模板。

## 📁 檔案結構

```
query-service/
├── lambda-test-templates.json     # Lambda 測試事件模板（全部）
├── test_lambda.py                # 測試執行腳本
├── LAMBDA_TESTING_GUIDE.md       # 本指南文件
├── test-events/                   # 獨立的測試事件文件
│   ├── dynamodb-stream-ios-insert.json
│   ├── apigateway-user-query.json
│   └── eventbridge-scheduled.json
└── lambdas/
    ├── stream_processor_lambda/   # DynamoDB Stream 處理器
    ├── query_lambda/             # API Gateway 查詢處理器
    └── query_result_lambda/      # 查詢結果處理器
```

## 🏗️ 架構說明

您的系統實現了 CQRS (Command Query Responsibility Segregation) 模式：

### Lambda 函數角色

1. **`stream_processor_lambda`**
   - **觸發源**: DynamoDB Stream (command-records 表)
   - **功能**: 處理 INSERT 事件，將資料同步到 query side
   - **目標表**: notification-records

2. **`query_lambda`**
   - **觸發源**: API Gateway HTTP 事件
   - **功能**: 接收查詢請求並轉發到 EKS Handler
   - **端點**: `/user`, `/marketing`, `/fail`

3. **`query_result_lambda`**
   - **觸發源**: 定時事件或自定義觸發
   - **功能**: 處理查詢結果統計和報告

## 🧪 測試方法

### 方法 1: 使用測試腳本 (推薦)

```bash
# 查看所有可用的測試案例
python test_lambda.py list

# 測試特定案例
python test_lambda.py stream_processor dynamodb_stream_insert_event
python test_lambda.py query_lambda api_gateway_user_query

# 執行所有測試
python test_lambda.py all

# 詳細輸出模式
python test_lambda.py stream_processor dynamodb_stream_insert_event --verbose
```

### 方法 2: AWS CLI 測試

```bash
# 測試 Stream Processor Lambda - iOS 推播事件
aws lambda invoke \
    --function-name stream-processor-lambda \
    --payload file://test-events/dynamodb-stream-ios-insert.json \
    --cli-binary-format raw-in-base64-out \
    response-stream.json

# 測試 Query Lambda - 用戶查詢
aws lambda invoke \
    --function-name query-lambda \
    --payload file://test-events/apigateway-user-query.json \
    --cli-binary-format raw-in-base64-out \
    response-query.json

# 測試 Query Result Lambda - 定時事件
aws lambda invoke \
    --function-name query-result-lambda \
    --payload file://test-events/eventbridge-scheduled.json \
    --cli-binary-format raw-in-base64-out \
    response-result.json

# 查看回應結果
cat response-stream.json
cat response-query.json
cat response-result.json
```

### 方法 3: AWS Lambda Console 測試

1. 登入 AWS Lambda Console
2. 選擇目標 Lambda 函數
3. 點擊 **Test** 標籤
4. 選擇 **Create new test event**
5. 從 `lambda-test-templates.json` 複製對應的事件 JSON
6. 執行測試

## 📋 測試案例說明

### Stream Processor Lambda 測試

#### 1. `dynamodb_stream_insert_ios_notification`
- **描述**: 測試 iOS 推播通知 INSERT 事件處理
- **用途**: 驗證 iOS 平台資料同步功能
- **測試文件**: `test-events/dynamodb-stream-ios-insert.json`
- **期望結果**: 成功處理並同步到 notification-records 表

#### 2. `dynamodb_stream_insert_android_notification`
- **描述**: 測試 Android 推播通知 INSERT 事件處理
- **用途**: 驗證 Android 平台資料同步功能
- **期望結果**: 成功處理並同步到 notification-records 表

#### 3. `dynamodb_stream_insert_failed_notification`
- **描述**: 測試失敗推播通知 INSERT 事件處理
- **用途**: 驗證失敗記錄的資料同步功能
- **期望結果**: 成功處理失敗記錄並包含錯誤訊息

#### 4. `dynamodb_stream_modify_event`
- **描述**: 測試 MODIFY 事件處理
- **用途**: 驗證事件過濾功能
- **期望結果**: 事件被跳過，不進行處理

#### 5. `dynamodb_stream_remove_event`
- **描述**: 測試 REMOVE 事件處理
- **用途**: 驗證刪除事件過濾功能
- **期望結果**: 事件被跳過，不進行處理

### Query Lambda 測試

#### 1. `apigateway_http_user_query_get`
- **描述**: 測試用戶查詢 GET 請求
- **參數**: `user_id=user-123`
- **測試文件**: `test-events/apigateway-user-query.json`
- **期望結果**: 返回用戶的推播記錄

#### 2. `apigateway_http_marketing_query_get`
- **描述**: 測試行銷活動查詢 GET 請求
- **參數**: `marketing_id=welcome-campaign-2024`
- **期望結果**: 返回活動的推播統計

#### 3. `apigateway_http_fail_query_get`
- **描述**: 測試失敗記錄查詢 GET 請求
- **參數**: `transaction_id=tx-failed-003`
- **期望結果**: 返回失敗的推播記錄

#### 4. `apigateway_http_invalid_request`
- **描述**: 測試缺少必要參數的無效請求
- **期望結果**: 返回 400 Bad Request

#### 5. `apigateway_http_cors_preflight`
- **描述**: 測試 CORS 預檢請求
- **用途**: 驗證 CORS 配置
- **期望結果**: 返回適當的 CORS 標頭

### Query Result Lambda 測試

#### 1. `eventbridge_scheduled_event`
- **描述**: 測試 EventBridge 定時觸發事件
- **用途**: 驗證定時報告生成功能
- **測試文件**: `test-events/eventbridge-scheduled.json`
- **期望結果**: 成功生成定時報告

#### 2. `eventbridge_custom_event`
- **描述**: 測試自定義 EventBridge 事件
- **用途**: 驗證自定義報告觸發功能
- **期望結果**: 成功處理自定義報告請求

#### 3. `cloudwatch_alarm_trigger`
- **描述**: 測試 CloudWatch 警報觸發事件
- **用途**: 驗證警報驅動的報告生成
- **期望結果**: 成功處理警報並生成相關報告

#### 4. `sns_notification_trigger`
- **描述**: 測試 SNS 通知觸發事件
- **用途**: 驗證 SNS 驅動的報告功能
- **期望結果**: 成功處理 SNS 消息並生成報告

#### 5. `sqs_batch_trigger`
- **描述**: 測試 SQS 批次觸發事件
- **用途**: 驗證批次報告處理功能
- **期望結果**: 成功處理多個 SQS 消息

## ⚙️ 環境設定

### 本地測試環境

```bash
# 設定環境變數
export NOTIFICATION_TABLE_NAME=notification-records
export EKS_HANDLER_URL=http://eks-handler:8000
export REQUEST_TIMEOUT=10
export AWS_REGION=ap-southeast-1

# 啟動 LocalStack (如果需要)
docker-compose up localstack

# 確保 EKS Handler 服務運行中
docker-compose up eks-handler
```

### 測試前檢查清單

- [ ] LocalStack 服務正在運行
- [ ] DynamoDB 表已創建 (`command-records`, `notification-records`)
- [ ] EKS Handler 服務可訪問
- [ ] 環境變數已正確設定
- [ ] Python 依賴已安裝

## 🔍 測試資料說明

### DynamoDB Stream 事件格式

```json
{
  "Records": [
    {
      "eventName": "INSERT|MODIFY|REMOVE",
      "dynamodb": {
        "NewImage": {
          "transaction_id": {"S": "tx-test-001"},
          "user_id": {"S": "user-test-123"},
          "status": {"S": "SENT"},
          // ... 其他欄位
        }
      }
    }
  ]
}
```

### API Gateway 事件格式

```json
{
  "version": "2.0",
  "routeKey": "GET /user",
  "queryStringParameters": {
    "user_id": "user-test-123"
  },
  "requestContext": {
    "http": {
      "method": "GET",
      "path": "/user"
    }
  }
}
```

## 🐛 常見問題排除

### 1. Lambda 導入錯誤
```
ImportError: No module named 'app'
```
**解決方案**: 確保在正確的目錄下執行測試腳本

### 2. DynamoDB 連接錯誤
```
ClientError: The security token included in the request is invalid
```
**解決方案**: 檢查 AWS 認證設定或 LocalStack 配置

### 3. EKS Handler 連接超時
```
ConnectionError: HTTPConnectionPool
```
**解決方案**: 確保 EKS Handler 服務正在運行且可訪問

### 4. 環境變數未設定
```
KeyError: 'NOTIFICATION_TABLE_NAME'
```
**解決方案**: 設定必要的環境變數

## 📊 測試結果分析

### 成功的測試輸出範例

```json
{
  "statusCode": 200,
  "processedRecords": 1
}
```

### 失敗的測試輸出範例

```json
{
  "errorType": "ValueError",
  "errorMessage": "Missing required fields: ['user_id']"
}
```

## 🚀 持續集成建議

### GitHub Actions 範例

```yaml
name: Lambda Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          cd query-service
          pip install -r requirements.txt
      - name: Run Lambda tests
        run: |
          cd query-service
          python test_lambda.py all
```

## 📚 相關文件

- [AWS Lambda 測試指南](https://docs.aws.amazon.com/lambda/latest/dg/testing-deployment.html)
- [DynamoDB Streams 事件格式](https://docs.aws.amazon.com/lambda/latest/dg/with-ddb.html)
- [API Gateway 事件格式](https://docs.aws.amazon.com/lambda/latest/dg/services-apigateway.html)
- [專案架構說明](./README.md)

---

💡 **提示**: 建議在部署到生產環境前，先在本地環境使用這些測試模板驗證所有 Lambda 函數的功能。
