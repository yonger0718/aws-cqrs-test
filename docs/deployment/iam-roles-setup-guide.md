# IAM 角色設定指南

## 概述

本指南詳細說明如何為 CQRS Query Service 創建所需的 IAM 角色和權限。包含 ECS 服務和 Lambda 函數所需的完整 IAM 配置。

## 🔐 IAM 角色架構概覽

### 必需的 IAM 角色

1. **ECS Task Execution Role** - 用於 ECS 任務啟動和容器管理
2. **ECS Task Role** - 用於 ECS 任務運行時的 AWS 服務訪問
3. **Lambda Execution Role** - 用於 Lambda 函數執行和 AWS 服務訪問

## 📋 角色 1: ECS Task Execution Role

### 1.1 進入 IAM Console

1. AWS Console → IAM → Roles → Create role

### 1.2 選擇信任實體

```
Trusted entity type: AWS service
Use case: Elastic Container Service → Elastic Container Service Task
```

### 1.3 基本配置

```
Role name: query-service-ecs-execution-role
Description: ECS task execution role for query service containers
```

### 1.4 附加 AWS 管理的政策

- `AmazonECSTaskExecutionRolePolicy`

### 1.5 創建自定義政策

#### ECR 和 CloudWatch 訪問政策

1. IAM → Policies → Create policy
2. JSON 標籤，貼入以下內容：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRAccess",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogsAccess",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
      ],
      "Resource": [
        "arn:aws:logs:ap-southeast-1:*:log-group:/ecs/query-service",
        "arn:aws:logs:ap-southeast-1:*:log-group:/ecs/query-service:*"
      ]
    }
  ]
}
```

3. 政策名稱：`query-service-ecs-execution-policy`
4. 將此政策附加到 execution role

### 1.6 信任關係

確認信任關係如下：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

## 📋 角色 2: ECS Task Role

### 2.1 創建角色

```
Role name: query-service-ecs-task-role
Description: ECS task role for query service runtime permissions
Trusted entity: AWS service → Elastic Container Service Task
```

### 2.2 創建自定義政策

#### Lambda 調用政策

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "LambdaInvokeAccess",
      "Effect": "Allow",
      "Action": ["lambda:InvokeFunction"],
      "Resource": ["arn:aws:lambda:ap-southeast-1:*:function:query-service-*"]
    },
    {
      "Sid": "DynamoDBQueryAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:Query",
        "dynamodb:GetItem",
        "dynamodb:BatchGetItem",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:ap-southeast-1:*:table/EventQuery",
        "arn:aws:dynamodb:ap-southeast-1:*:table/EventQuery/index/*"
      ]
    },
    {
      "Sid": "APIGatewayInvokeAccess",
      "Effect": "Allow",
      "Action": ["execute-api:Invoke"],
      "Resource": ["arn:aws:execute-api:ap-southeast-1:*:*/*/query/*"]
    },
    {
      "Sid": "ECSExecAccess",
      "Effect": "Allow",
      "Action": [
        "ssmmessages:CreateControlChannel",
        "ssmmessages:CreateDataChannel",
        "ssmmessages:OpenControlChannel",
        "ssmmessages:OpenDataChannel"
      ],
      "Resource": "*"
    }
  ]
}
```

政策名稱：`query-service-ecs-task-policy`

### 2.3 信任關係

與 execution role 相同的信任關係。

## 📋 角色 3: Lambda Execution Role

### 3.1 創建角色

```
Role name: query-service-lambda-execution-role
Description: Lambda execution role for query service functions
Trusted entity: AWS service → Lambda
```

### 3.2 附加 AWS 管理的政策

- `AWSLambdaBasicExecutionRole`
- `AWSLambdaVPCAccessExecutionRole` (如果 Lambda 需要 VPC 訪問)

### 3.3 創建自定義政策

#### Lambda 完整權限政策

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDBFullAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:Query",
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:BatchGetItem",
        "dynamodb:BatchWriteItem",
        "dynamodb:Scan",
        "dynamodb:DescribeTable"
      ],
      "Resource": [
        "arn:aws:dynamodb:ap-southeast-1:*:table/command-records",
        "arn:aws:dynamodb:ap-southeast-1:*:table/command-records/stream/*",
        "arn:aws:dynamodb:ap-southeast-1:*:table/EventQuery",
        "arn:aws:dynamodb:ap-southeast-1:*:table/EventQuery/index/*"
      ]
    },
    {
      "Sid": "DynamoDBStreamAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:DescribeStream",
        "dynamodb:GetRecords",
        "dynamodb:GetShardIterator",
        "dynamodb:ListStreams"
      ],
      "Resource": [
        "arn:aws:dynamodb:ap-southeast-1:*:table/command-records/stream/*"
      ]
    },
    {
      "Sid": "CloudWatchLogsAccess",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ],
      "Resource": [
        "arn:aws:logs:ap-southeast-1:*:log-group:/aws/lambda/query-service-*",
        "arn:aws:logs:ap-southeast-1:*:log-group:/aws/lambda/query-service-*:*"
      ]
    },
    {
      "Sid": "VPCNetworkAccess",
      "Effect": "Allow",
      "Action": [
        "ec2:CreateNetworkInterface",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DeleteNetworkInterface",
        "ec2:AttachNetworkInterface",
        "ec2:DetachNetworkInterface"
      ],
      "Resource": "*"
    },
    {
      "Sid": "XRayTracing",
      "Effect": "Allow",
      "Action": ["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
      "Resource": "*"
    }
  ]
}
```

政策名稱：`query-service-lambda-execution-policy`

### 3.4 信任關係

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

## 🔧 GUI 設定步驟詳解

### 步驟 1: 創建政策

#### 1.1 進入 IAM Console

1. AWS Console → IAM → Policies → Create policy

#### 1.2 使用 JSON 編輯器

1. 選擇 "JSON" 標籤
2. 刪除預設內容
3. 貼入上述 JSON 政策內容
4. 點擊 "Next: Tags"

#### 1.3 添加標籤 (可選)

```
Environment: production
Service: query-service
Component: iam-policy
```

#### 1.4 檢查和命名

1. Policy name: 使用建議的政策名稱
2. Description: 添加描述
3. 點擊 "Create policy"

### 步驟 2: 創建角色

#### 2.1 進入角色創建頁面

1. IAM → Roles → Create role

#### 2.2 選擇信任實體

- 對於 ECS 角色：AWS service → Elastic Container Service
- 對於 Lambda 角色：AWS service → Lambda

#### 2.3 附加政策

1. 搜尋並選擇 AWS 管理的政策
2. 搜尋並選擇剛創建的自定義政策
3. 點擊 "Next"

#### 2.4 角色詳細資訊

```
Role name: [如上述定義]
Description: [對應的描述]
Tags: [環境和服務標籤]
```

#### 2.5 檢查和創建

1. 檢查所有設定
2. 點擊 "Create role"

## 🛡️ 安全最佳實踐

### 最小權限原則

1. **僅授予必要權限** - 不要使用 `*` 資源除非必要
2. **定期檢查權限** - 移除不再需要的權限
3. **使用條件限制** - 根據需要添加 IP 或時間條件

### 條件限制範例

在政策中添加條件：

```json
{
  "Condition": {
    "IpAddress": {
      "aws:SourceIp": ["10.0.0.0/16"]
    },
    "StringEquals": {
      "aws:RequestedRegion": "ap-southeast-1"
    }
  }
}
```

### 監控和審計

1. **啟用 CloudTrail** - 記錄 IAM 活動
2. **設定 CloudWatch 警報** - 監控異常權限使用
3. **定期權限審查** - 使用 IAM Access Analyzer

## 📊 權限驗證

### 測試 ECS 角色

```bash
# 檢查角色是否可以拉取 ECR 映像
aws sts assume-role --role-arn arn:aws:iam::ACCOUNT:role/query-service-ecs-execution-role --role-session-name test

# 測試 CloudWatch 日誌權限
aws logs describe-log-groups --log-group-name-prefix "/ecs/query-service"
```

### 測試 Lambda 角色

```bash
# 檢查 DynamoDB 訪問權限
aws dynamodb describe-table --table-name EventQuery

# 測試 Lambda 調用權限
aws lambda invoke --function-name query-service-stream-processor test-output.json
```

## 🔍 故障排除

### 常見權限錯誤

#### 1. ECR 拉取失敗

**錯誤**: `CannotPullContainerError`
**解決方案**:

- 檢查 execution role 是否有 ECR 權限
- 確認 ECR 政策中的 `ecr:GetAuthorizationToken` 權限

#### 2. CloudWatch 日誌寫入失敗

**錯誤**: 無日誌輸出
**解決方案**:

- 檢查 `logs:CreateLogGroup` 權限
- 確認日誌群組 ARN 正確

#### 3. DynamoDB 訪問被拒

**錯誤**: `AccessDeniedException`
**解決方案**:

- 檢查資源 ARN 是否正確
- 確認動作權限 (Query, GetItem 等)

#### 4. Lambda VPC 超時

**錯誤**: Lambda 函數超時
**解決方案**:

- 檢查 VPC 網路介面權限
- 確認子網有 NAT Gateway

## 📋 部署檢查清單

### IAM 角色檢查

- [ ] ECS Task Execution Role 已創建
- [ ] ECS Task Role 已創建
- [ ] Lambda Execution Role 已創建
- [ ] 所有必要政策已附加
- [ ] 信任關係配置正確

### 權限驗證

- [ ] ECR 映像拉取測試通過
- [ ] CloudWatch 日誌寫入正常
- [ ] DynamoDB 讀寫權限正常
- [ ] Lambda 函數可正常執行
- [ ] API Gateway 調用權限正常

### 安全檢查

- [ ] 使用最小權限原則
- [ ] 資源 ARN 具體化 (避免使用 `*`)
- [ ] 添加適當的條件限制
- [ ] 啟用監控和審計

## 📝 角色摘要表

| 角色名稱                            | 用途         | 主要權限                      | 信任實體                |
| ----------------------------------- | ------------ | ----------------------------- | ----------------------- |
| query-service-ecs-execution-role    | ECS 任務啟動 | ECR, CloudWatch Logs          | ecs-tasks.amazonaws.com |
| query-service-ecs-task-role         | ECS 運行時   | Lambda, DynamoDB, API Gateway | ecs-tasks.amazonaws.com |
| query-service-lambda-execution-role | Lambda 執行  | DynamoDB, CloudWatch, VPC     | lambda.amazonaws.com    |
