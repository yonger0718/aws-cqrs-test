# Lambda GUI 部署詳細步驟指南

## 🎯 Lambda 函數完整部署流程

### 前置準備

#### 1.1 確認 ECR 映像

確認以下 Lambda 容器映像已推送到 ECR：

- `query-service-stream-processor-lambda:latest`
- `query-service-query-lambda:latest`
- `query-service-query-result-lambda:latest`

#### 1.2 準備 IAM 執行角色

確認 `lambda-execution-role` 已創建，並具有以下權限：

- `AWSLambdaBasicExecutionRole`
- DynamoDB 讀寫權限
- VPC 網路權限 (如需要)

## 🔧 Lambda 函數部署

### 函數 1: Stream Processor Lambda

#### 1.1 創建函數

1. **進入 Lambda Console**

   - AWS Console → Lambda → Functions
   - 點擊 "Create function"

2. **選擇創建方式**

   - 選擇 "Container image"

3. **基本資訊**

   ```
   Function name: query-service-stream-processor
   Container image URI: {ACCOUNT_ID}.dkr.ecr.ap-southeast-1.amazonaws.com/query-service-stream-processor-lambda:latest
   Package type: Image
   ```

4. **執行角色**

   ```
   Execution role: Use an existing role
   Existing role: lambda-execution-role
   ```

5. **點擊 "Create function"**

#### 1.2 配置函數設定

**基本設定**

1. 進入函數 → Configuration → General configuration → Edit
   ```
   Description: CQRS Stream Processor for DynamoDB events
   Timeout: 3 minutes
   Memory: 256 MB
   ```

**環境變數**

1. Configuration → Environment variables → Edit
   ```
   AWS_LAMBDA_FUNCTION_NAME: query-service-stream-processor
   AWS_REGION: ap-southeast-1
   NOTIFICATION_TABLE_NAME: EventQuery
   ```

**觸發器設定**

1. Function overview → Add trigger
2. 選擇 "DynamoDB"
3. 配置：
   ```
   DynamoDB table: command-records
   Starting position: Latest
   Batch size: 10
   Maximum batching window in seconds: 5
   Enable trigger: Yes
   ```

#### 1.3 測試函數

1. Test → Create test event
2. 選擇 "DynamoDB" 模板
3. 修改測試數據後執行測試

### 函數 2: Query Lambda

#### 2.1 創建函數

1. **基本資訊**
   ```
   Function name: query-service-query-lambda
   Container image URI: {ACCOUNT_ID}.dkr.ecr.ap-southeast-1.amazonaws.com/query-service-query-lambda:latest
   Execution role: lambda-execution-role
   ```

#### 2.2 配置函數設定

**基本設定**

```
Timeout: 1 minute
Memory: 256 MB
```

**環境變數**

```
AWS_LAMBDA_FUNCTION_NAME: query-service-query-lambda
EKS_HANDLER_URL: http://your-internal-alb-url:8000
REQUEST_TIMEOUT: 10
```

**VPC 配置**

1. Configuration → VPC → Edit
   ```
   VPC: 選擇與 ECS 相同的 VPC
   Subnets: 選擇私有子網
   Security groups:
   - 出站規則: 允許 HTTPS (443) 到 0.0.0.0/0
   - 出站規則: 允許 HTTP (8000) 到 ECS 安全群組
   ```

#### 2.3 API Gateway 整合

此函數將由 API Gateway 觸發，稍後在 API Gateway 設定中配置。

### 函數 3: Query Result Lambda

#### 3.1 創建函數

1. **基本資訊**
   ```
   Function name: query-service-query-result-lambda
   Container image URI: {ACCOUNT_ID}.dkr.ecr.ap-southeast-1.amazonaws.com/query-service-query-result-lambda:latest
   Execution role: lambda-execution-role
   ```

#### 3.2 配置函數設定

**基本設定**

```
Timeout: 1 minute
Memory: 256 MB
```

**環境變數**

```
AWS_LAMBDA_FUNCTION_NAME: query-service-query-result-lambda
AWS_REGION: ap-southeast-1
NOTIFICATION_TABLE_NAME: EventQuery
```

## 🌐 API Gateway 設定

### 1. 創建 REST API

#### 1.1 進入 API Gateway Console

1. AWS Console → API Gateway
2. 點擊 "Create API"
3. 選擇 "REST API" → "Build"

#### 1.2 API 基本設定

```
API name: query-service-internal-api
Description: Internal API for CQRS Query Service
Endpoint Type: Regional
```

### 2. 創建資源結構

#### 2.1 創建根資源

1. Actions → Create Resource
   ```
   Resource Name: query
   Resource Path: /query
   ```

#### 2.2 創建子資源

重複以下步驟創建三個子資源：

**用戶查詢資源**

```
Parent Resource: /query
Resource Name: user
Resource Path: /user
```

**行銷查詢資源**

```
Parent Resource: /query
Resource Name: marketing
Resource Path: /marketing
```

**失敗查詢資源**

```
Parent Resource: /query
Resource Name: fail
Resource Path: /fail
```

### 3. 配置方法

#### 3.1 為 /query/user 添加 GET 方法

1. 選擇 `/query/user` 資源
2. Actions → Create Method → GET
3. 整合設定：
   ```
   Integration type: Lambda Function
   Use Lambda Proxy integration: ✓ (勾選)
   Lambda Region: ap-southeast-1
   Lambda Function: query-service-query-lambda
   ```

#### 3.2 為 /query/marketing 添加 GET 方法

重複上述步驟，選擇相同的 Lambda 函數

#### 3.3 為 /query/fail 添加 GET 方法

重複上述步驟，選擇相同的 Lambda 函數

### 4. 部署 API

#### 4.1 部署到階段

1. Actions → Deploy API
2. 配置：
   ```
   Deployment stage: [New Stage]
   Stage name: v1
   Stage description: Production deployment
   Deployment description: Initial deployment
   ```

#### 4.2 獲取 API URL

部署完成後，記錄 "Invoke URL"，格式如下：

```
https://api-id.execute-api.ap-southeast-1.amazonaws.com/v1
```

此 URL 將用於 ECS 服務的 `INTERNAL_API_URL` 環境變數。

## 🔍 測試和驗證

### 1. 測試 Lambda 函數

#### 1.1 測試 Stream Processor

1. Lambda Console → query-service-stream-processor → Test
2. 使用 DynamoDB Stream 測試事件
3. 檢查執行結果和日誌

#### 1.2 測試 Query Lambda

1. 可通過 API Gateway 測試工具測試
2. 或使用 curl：
   ```bash
   curl "https://api-id.execute-api.ap-southeast-1.amazonaws.com/v1/query/user?user_id=test123"
   ```

### 2. 監控設定

#### 2.1 CloudWatch 日誌

確認以下日誌群組已創建並有日誌輸出：

- `/aws/lambda/query-service-stream-processor`
- `/aws/lambda/query-service-query-lambda`
- `/aws/lambda/query-service-query-result-lambda`

#### 2.2 CloudWatch 指標

1. 進入 CloudWatch → Metrics → Lambda
2. 檢查函數的指標：
   - Invocations
   - Duration
   - Errors
   - Throttles

## 🚨 故障排除

### 常見問題

#### 1. Lambda 函數冷啟動時間過長

**解決方案**:

- 增加記憶體配置 (512MB 或更高)
- 考慮使用 Provisioned Concurrency

#### 2. VPC Lambda 連接超時

**症狀**: Lambda 無法連接到 ECS 服務
**解決方案**:

1. 檢查 VPC 配置是否正確
2. 確認子網有 NAT Gateway (私有子網)
3. 檢查安全群組規則

#### 3. DynamoDB 權限錯誤

**症狀**: Stream Processor 無法寫入 DynamoDB
**解決方案**:

1. 檢查執行角色是否有 DynamoDB 權限
2. 確認表名稱正確
3. 檢查區域設定

#### 4. API Gateway 502 錯誤

**症狀**: API Gateway 返回 502 Bad Gateway
**解決方案**:

1. 檢查 Lambda 函數是否正常執行
2. 確認 Lambda Proxy 整合已啟用
3. 檢查 Lambda 回應格式

### 日誌查看

#### CloudWatch Logs Insights 查詢

```sql
-- 查看錯誤日誌
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 50

-- 查看函數執行時間
fields @timestamp, @duration
| sort @timestamp desc
| limit 50
```

## 📋 部署檢查清單

### Lambda 函數檢查

- [ ] 所有三個 Lambda 函數已創建
- [ ] 環境變數配置正確
- [ ] IAM 執行角色權限適當
- [ ] DynamoDB 觸發器已設定 (Stream Processor)
- [ ] VPC 配置正確 (Query Lambda)

### API Gateway 檢查

- [ ] REST API 已創建
- [ ] 資源結構正確
- [ ] 方法配置正確
- [ ] Lambda 整合已啟用
- [ ] API 已部署到階段

### 測試檢查

- [ ] Lambda 函數測試通過
- [ ] API Gateway 端點可存取
- [ ] CloudWatch 日誌正常輸出
- [ ] 監控指標正常顯示

### 整合檢查

- [ ] ECS 服務的 INTERNAL_API_URL 已更新
- [ ] 端到端流程測試通過
- [ ] 健康檢查端點正常運作
