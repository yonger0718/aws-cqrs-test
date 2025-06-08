# DynamoDB 表名遷移指南

## 📋 概述

本文檔記錄了查詢表名稱從 `notification-records` 遷移到 `EventQuery` 的所有變更。

## 🔄 變更內容

### 表名變更

- **舊表名**: `notification-records`
- **新表名**: `EventQuery`

### 受影響的組件

#### 1. IAM 角色和政策

- **檔案**: `iam-roles-setup-guide.md`, `iam-quick-setup.md`
- **變更**: 更新所有 DynamoDB 資源 ARN 中的表名

```diff
- "arn:aws:dynamodb:ap-southeast-1:*:table/notification-records"
- "arn:aws:dynamodb:ap-southeast-1:*:table/notification-records/index/*"
+ "arn:aws:dynamodb:ap-southeast-1:*:table/EventQuery"
+ "arn:aws:dynamodb:ap-southeast-1:*:table/EventQuery/index/*"
```

#### 2. 環境變數配置

- **檔案**: `deployment-env-vars.md`
- **變更**: 更新 `NOTIFICATION_TABLE_NAME` 環境變數值

```diff
- NOTIFICATION_TABLE_NAME=notification-records
+ NOTIFICATION_TABLE_NAME=EventQuery
```

#### 3. AWS Console 部署指南

- **檔案**: `aws-console-deployment-guide.md`
- **變更**: 更新 Lambda 函數環境變數配置

#### 4. Lambda GUI 部署步驟

- **檔案**: `lambda-gui-deployment-steps.md`
- **變更**: 更新環境變數配置範例

## 🚀 部署時需要更新的配置

### Lambda 函數環境變數

#### Stream Processor Lambda

```bash
NOTIFICATION_TABLE_NAME=EventQuery
```

#### Query Result Lambda

```bash
NOTIFICATION_TABLE_NAME=EventQuery
```

### IAM 政策資源

確保以下 IAM 政策包含正確的表名：

```json
{
  "Resource": [
    "arn:aws:dynamodb:ap-southeast-1:*:table/EventQuery",
    "arn:aws:dynamodb:ap-southeast-1:*:table/EventQuery/index/*"
  ]
}
```

## ⚠️ 重要注意事項

### 部署前檢查

1. **確認新表已創建**

   ```bash
   aws dynamodb describe-table --table-name EventQuery
   ```

2. **更新所有 Lambda 函數環境變數**

   - query-service-stream-processor
   - query-service-query-result-lambda

3. **確認 IAM 角色具有新表的訪問權限**

4. **測試資料遷移（如需要）**

### 向後兼容性

- 舊的 `notification-records` 表可以保留作為備份
- 建議在確認新表運作正常後再刪除舊表
- Lambda 函數代碼中的表名是通過環境變數配置，不需要修改代碼

## 🔍 驗證步驟

### 1. 環境變數驗證

```bash
# 檢查 Lambda 函數環境變數
aws lambda get-function-configuration --function-name query-service-stream-processor | grep NOTIFICATION_TABLE_NAME
aws lambda get-function-configuration --function-name query-service-query-result-lambda | grep NOTIFICATION_TABLE_NAME
```

### 2. IAM 權限驗證

```bash
# 測試 DynamoDB 訪問權限
aws dynamodb describe-table --table-name EventQuery
```

### 3. 功能測試

1. 觸發 Stream Processor Lambda
2. 檢查資料是否正確寫入 EventQuery 表
3. 測試查詢功能是否正常

## 📝 已更新的文件清單

✅ **IAM 配置**

- `query-service/iam-roles-setup-guide.md`
- `query-service/iam-quick-setup.md`

✅ **部署配置**

- `query-service/deployment-env-vars.md`
- `query-service/aws-console-deployment-guide.md`
- `query-service/lambda-gui-deployment-steps.md`

✅ **本文檔**

- `query-service/table-name-migration.md`

## 📞 技術支援

如果在遷移過程中遇到問題，請檢查：

1. 表名是否在所有地方都已正確更新
2. IAM 權限是否包含新表的訪問權限
3. Lambda 函數環境變數是否已更新
4. DynamoDB 表是否已正確創建並配置 GSI
