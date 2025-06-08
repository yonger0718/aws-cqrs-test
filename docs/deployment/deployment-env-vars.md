# 手動部署環境變數配置指南

## 概述

本文檔列出了在生產環境中手動部署 Lambda 函數和 ECS 服務時需要設置的所有環境變數。

## 🚀 ECS (FastAPI Query Service) 環境變數

### 必需環境變數

```bash
# 環境配置
ENVIRONMENT=production

# API Gateway 配置
INTERNAL_API_URL=https://your-api-gateway-id.execute-api.ap-southeast-1.amazonaws.com/v1

# AWS 區域配置
AWS_DEFAULT_REGION=ap-southeast-1
AWS_REGION=ap-southeast-1

# 請求配置
REQUEST_TIMEOUT=30
```

### 可選環境變數 (本地開發用)

```bash
# 本地開發時使用
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

### ECS Task Definition 示例

```json
{
  "environment": [
    {
      "name": "ENVIRONMENT",
      "value": "production"
    },
    {
      "name": "INTERNAL_API_URL",
      "value": "https://your-api-gateway-id.execute-api.ap-southeast-1.amazonaws.com/v1"
    },
    {
      "name": "AWS_DEFAULT_REGION",
      "value": "ap-southeast-1"
    },
    {
      "name": "AWS_REGION",
      "value": "ap-southeast-1"
    },
    {
      "name": "REQUEST_TIMEOUT",
      "value": "30"
    }
  ]
}
```

## 🔧 Lambda 函數環境變數

### Stream Processor Lambda

處理 DynamoDB Stream 事件，實現 CQRS 資料同步。

```bash
# Lambda 基本配置
AWS_LAMBDA_FUNCTION_NAME=query-service-stream-processor
AWS_REGION=ap-southeast-1

# DynamoDB 配置
NOTIFICATION_TABLE_NAME=EventQuery

# 本地開發配置 (僅開發環境)
LOCALSTACK_HOSTNAME=localstack
```

### Query Lambda

提供 API Gateway 到 EKS Handler 的路由適配。

```bash
# Lambda 基本配置
AWS_LAMBDA_FUNCTION_NAME=query-service-query-lambda

# EKS Handler 配置
EKS_HANDLER_URL=http://your-internal-alb-url:8000

# 請求配置
REQUEST_TIMEOUT=10
```

### Query Result Lambda

直接查詢 DynamoDB 並返回結果。

```bash
# Lambda 基本配置
AWS_LAMBDA_FUNCTION_NAME=query-service-query-result-lambda
AWS_REGION=ap-southeast-1

# DynamoDB 配置
NOTIFICATION_TABLE_NAME=EventQuery

# 本地開發配置 (僅開發環境)
LOCALSTACK_HOSTNAME=localstack
```

## 📋 部署檢查清單

### ECS 部署前檢查

- [ ] 確認 Internal API Gateway 已部署並獲取正確的 URL
- [ ] 確認 VPC 和子網配置正確
- [ ] 確認 IAM 角色具有適當權限
- [ ] 確認 ECR 映像已推送到正確的儲存庫

### Lambda 部署前檢查

- [ ] 確認 DynamoDB 表已創建
- [ ] 確認 DynamoDB Stream 已啟用
- [ ] 確認 IAM 執行角色具有適當權限
- [ ] 確認 Lambda 函數映像已推送到 ECR

### 環境變數驗證

```bash
# 驗證 ECS 服務環境變數
aws ecs describe-task-definition --task-definition query-service-task

# 驗證 Lambda 函數環境變數
aws lambda get-function-configuration --function-name query-service-stream-processor
aws lambda get-function-configuration --function-name query-service-query-lambda
aws lambda get-function-configuration --function-name query-service-query-result-lambda
```

## 🔍 故障排除

### 常見問題

1. **Internal API Gateway 連接失敗**

   - 檢查 `INTERNAL_API_URL` 是否正確
   - 確認 API Gateway 部署狀態
   - 檢查網路連接和安全群組設定

2. **DynamoDB 訪問失敗**

   - 檢查 `NOTIFICATION_TABLE_NAME` 是否正確
   - 確認 IAM 角色具有 DynamoDB 讀寫權限
   - 檢查區域設定是否一致

3. **Lambda 函數超時**
   - 檢查 `REQUEST_TIMEOUT` 設定
   - 確認下游服務回應時間
   - 調整 Lambda 函數超時設定

### 日誌查看

```bash
# ECS 服務日誌
aws logs get-log-events --log-group-name /ecs/query-service

# Lambda 函數日誌
aws logs get-log-events --log-group-name /aws/lambda/query-service-stream-processor
aws logs get-log-events --log-group-name /aws/lambda/query-service-query-lambda
aws logs get-log-events --log-group-name /aws/lambda/query-service-query-result-lambda
```

## 📝 版本記錄

- v1.0.0: 初始版本，包含所有必要的環境變數配置
