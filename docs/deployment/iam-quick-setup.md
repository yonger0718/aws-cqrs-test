# IAM 快速設定參考

## 🚀 快速設定總覽

需要創建的 3 個 IAM 角色：

### 1️⃣ ECS Task Execution Role

```bash
角色名稱: query-service-ecs-execution-role
用途: 啟動和管理 ECS 容器
附加政策: AmazonECSTaskExecutionRolePolicy + 自定義 ECR/Logs 政策
```

### 2️⃣ ECS Task Role

```bash
角色名稱: query-service-ecs-task-role
用途: ECS 容器運行時的 AWS 服務訪問
附加政策: 自定義 Lambda/DynamoDB/API Gateway 政策
```

### 3️⃣ Lambda Execution Role

```bash
角色名稱: query-service-lambda-execution-role
用途: Lambda 函數執行和 AWS 服務訪問
附加政策: AWSLambdaBasicExecutionRole + 自定義 DynamoDB/VPC 政策
```

## ⚡ 快速創建腳本

### AWS CLI 創建命令

#### 1. 創建信任政策文件

**ecs-trust-policy.json**

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

**lambda-trust-policy.json**

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

#### 2. 創建角色

```bash
# ECS Execution Role
aws iam create-role \
  --role-name query-service-ecs-execution-role \
  --assume-role-policy-document file://ecs-trust-policy.json

# ECS Task Role
aws iam create-role \
  --role-name query-service-ecs-task-role \
  --assume-role-policy-document file://ecs-trust-policy.json

# Lambda Execution Role
aws iam create-role \
  --role-name query-service-lambda-execution-role \
  --assume-role-policy-document file://lambda-trust-policy.json
```

#### 3. 附加 AWS 管理政策

```bash
# ECS Execution Role
aws iam attach-role-policy \
  --role-name query-service-ecs-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Lambda Execution Role
aws iam attach-role-policy \
  --role-name query-service-lambda-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
  --role-name query-service-lambda-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole
```

## 📋 最小權限政策模板

### ECS Execution 自定義政策

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
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
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:ap-southeast-1:*:log-group:/ecs/query-service*"
    }
  ]
}
```

### ECS Task 自定義政策

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["lambda:InvokeFunction"],
      "Resource": "arn:aws:lambda:ap-southeast-1:*:function:query-service-*"
    },
    {
      "Effect": "Allow",
      "Action": ["dynamodb:Query", "dynamodb:GetItem"],
      "Resource": [
        "arn:aws:dynamodb:ap-southeast-1:*:table/EventQuery",
        "arn:aws:dynamodb:ap-southeast-1:*:table/EventQuery/index/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["execute-api:Invoke"],
      "Resource": "arn:aws:execute-api:ap-southeast-1:*:*/*/query/*"
    }
  ]
}
```

### Lambda 自定義政策

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:Query",
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DescribeStream",
        "dynamodb:GetRecords",
        "dynamodb:GetShardIterator"
      ],
      "Resource": [
        "arn:aws:dynamodb:ap-southeast-1:*:table/command-records*",
        "arn:aws:dynamodb:ap-southeast-1:*:table/EventQuery*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateNetworkInterface",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DeleteNetworkInterface"
      ],
      "Resource": "*"
    }
  ]
}
```

## 🎯 GUI 快速設定步驟

### 步驟 1-3: 針對每個角色重複

1. **IAM Console** → Roles → Create role
2. **選擇實體**: AWS service → (ECS Task/Lambda)
3. **附加政策**: 選擇對應的 AWS 管理政策
4. **角色名稱**: 輸入角色名稱
5. **Create role**

### 步驟 4: 添加自定義政策

1. **IAM Console** → Policies → Create policy
2. **JSON 標籤** → 貼入政策內容
3. **Review policy** → 命名政策
4. **回到角色** → Attach policies → 選擇剛建的政策

## 🔍 快速驗證

### 檢查角色是否存在

```bash
aws iam get-role --role-name query-service-ecs-execution-role
aws iam get-role --role-name query-service-ecs-task-role
aws iam get-role --role-name query-service-lambda-execution-role
```

### 檢查附加的政策

```bash
aws iam list-attached-role-policies --role-name query-service-ecs-execution-role
```

## 📝 部署時使用的 ARN

複製以下 ARN 用於部署配置：

```bash
# ECS Task Definition 中使用
executionRoleArn: arn:aws:iam::YOUR_ACCOUNT_ID:role/query-service-ecs-execution-role
taskRoleArn: arn:aws:iam::YOUR_ACCOUNT_ID:role/query-service-ecs-task-role

# Lambda 函數中使用
Role: arn:aws:iam::YOUR_ACCOUNT_ID:role/query-service-lambda-execution-role
```

## ⚠️ 重要注意事項

1. **替換 YOUR_ACCOUNT_ID** - 用您的實際 AWS 帳號 ID
2. **區域設定** - 確保所有 ARN 中的區域為 `ap-southeast-1`
3. **最小權限** - 如不需要某些權限，可從政策中移除
4. **資源限制** - 盡量指定具體的資源 ARN 而非使用 `*`
