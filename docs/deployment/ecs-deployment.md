# ECS Fargate 部署指南

## 📋 概述

本文檔提供詳細的 ECS Fargate 部署操作指南，包括從本地開發到生產環境的完整部署流程。

## 🔧 前置需求

### 系統需求

- AWS CLI v2.0+
- Docker Engine 20.10+
- Poetry 1.2+
- Terraform 1.0+ (可選)

### AWS 權限需求

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:*",
        "ecr:*",
        "iam:PassRole",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "elasticloadbalancing:*",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "apigateway:*"
      ],
      "Resource": "*"
    }
  ]
}
```

## 🏗️ 本地開發環境部署

### 1. 環境準備

```bash
# 克隆專案
git clone <repository-url>
cd aws-cqrs-test

# 安裝依賴
poetry install

# 檢查環境
./scripts/verification/verify_system.sh
```

### 2. 啟動本地服務

```bash
# 進入服務目錄
cd query-service

# 啟動所有服務
docker-compose up -d

# 檢查服務狀態
docker-compose ps

# 驗證服務健康
curl http://localhost:8000/health
```

### 3. 本地測試

```bash
# 執行單元測試
poetry run pytest tests/ -v

# 執行整合測試
./scripts/testing/test_full_flow.sh

# 查詢功能測試
./scripts/queries/simple_query.sh --all
```

## 🚀 AWS 生產環境部署

### 步驟 1: 建立 ECR 儲存庫

```bash
# 設定環境變數
export AWS_REGION=ap-southeast-1
export AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
export ECR_REGISTRY=$AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com

# 建立 ECR 儲存庫
aws ecr create-repository \
    --repository-name query-service \
    --region $AWS_REGION \
    --image-scanning-configuration scanOnPush=true

# 設定儲存庫政策（可選）
aws ecr put-lifecycle-policy \
    --repository-name query-service \
    --lifecycle-policy-text '{
        "rules": [
            {
                "rulePriority": 1,
                "description": "Keep last 10 images",
                "selection": {
                    "tagStatus": "any",
                    "countType": "imageCountMoreThan",
                    "countNumber": 10
                },
                "action": {
                    "type": "expire"
                }
            }
        ]
    }'
```

### 步驟 2: 建構並推送容器映像

```bash
# 登入 ECR
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ECR_REGISTRY

# 建構映像
cd query-service
docker build -t query-service:latest ./eks_handler

# 標記映像
docker tag query-service:latest $ECR_REGISTRY/query-service:latest
docker tag query-service:latest $ECR_REGISTRY/query-service:$(git rev-parse --short HEAD)

# 推送映像
docker push $ECR_REGISTRY/query-service:latest
docker push $ECR_REGISTRY/query-service:$(git rev-parse --short HEAD)
```

### 步驟 3: 建立 ECS 叢集

```bash
# 建立 ECS 叢集
aws ecs create-cluster \
    --cluster-name query-service-cluster \
    --capacity-providers FARGATE \
    --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1

# 驗證叢集建立
aws ecs describe-clusters --clusters query-service-cluster
```

### 步驟 4: 建立 IAM 角色

#### 任務執行角色

```bash
# 建立信任政策
cat > trust-policy.json << EOF
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
EOF

# 建立執行角色
aws iam create-role \
    --role-name ecsTaskExecutionRole-query-service \
    --assume-role-policy-document file://trust-policy.json

# 附加政策
aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole-query-service \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

#### 任務角色

```bash
# 建立任務角色
aws iam create-role \
    --role-name ecsTaskRole-query-service \
    --assume-role-policy-document file://trust-policy.json

# 建立自定義政策
cat > task-policy.json << EOF
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
        "dynamodb:DeleteItem",
        "lambda:InvokeFunction",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam put-role-policy \
    --role-name ecsTaskRole-query-service \
    --policy-name QueryServiceTaskPolicy \
    --policy-document file://task-policy.json
```

### 步驟 5: 建立任務定義

```bash
# 建立任務定義檔案
cat > task-definition.json << EOF
{
  "family": "query-service",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::$AWS_ACCOUNT:role/ecsTaskExecutionRole-query-service",
  "taskRoleArn": "arn:aws:iam::$AWS_ACCOUNT:role/ecsTaskRole-query-service",
  "containerDefinitions": [
    {
      "name": "ecs-handler",
      "image": "$ECR_REGISTRY/query-service:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        },
        {
          "name": "INTERNAL_API_URL",
          "value": "https://internal-api-id.execute-api.$AWS_REGION.amazonaws.com/v1"
        },
        {
          "name": "REQUEST_TIMEOUT",
          "value": "30"
        },
        {
          "name": "AWS_DEFAULT_REGION",
          "value": "$AWS_REGION"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/query-service",
          "awslogs-region": "$AWS_REGION",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

# 註冊任務定義
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

### 步驟 6: 建立負載均衡器

```bash
# 取得 VPC 和子網路資訊
export VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=isDefault,Values=true" \
    --query "Vpcs[0].VpcId" --output text)

export SUBNET_IDS=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query "Subnets[*].SubnetId" --output text)

# 建立安全群組
aws ec2 create-security-group \
    --group-name query-service-alb-sg \
    --description "Security group for Query Service ALB" \
    --vpc-id $VPC_ID

export ALB_SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=query-service-alb-sg" \
    --query "SecurityGroups[0].GroupId" --output text)

# 開放 80 和 443 端口
aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG_ID \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG_ID \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0

# 建立 ECS 服務安全群組
aws ec2 create-security-group \
    --group-name query-service-ecs-sg \
    --description "Security group for Query Service ECS" \
    --vpc-id $VPC_ID

export ECS_SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=query-service-ecs-sg" \
    --query "SecurityGroups[0].GroupId" --output text)

# 允許 ALB 訪問 ECS
aws ec2 authorize-security-group-ingress \
    --group-id $ECS_SG_ID \
    --protocol tcp \
    --port 8000 \
    --source-group $ALB_SG_ID

# 建立應用程式負載均衡器
aws elbv2 create-load-balancer \
    --name query-service-alb \
    --subnets $SUBNET_IDS \
    --security-groups $ALB_SG_ID \
    --scheme internal

export ALB_ARN=$(aws elbv2 describe-load-balancers \
    --names query-service-alb \
    --query "LoadBalancers[0].LoadBalancerArn" --output text)

# 建立目標群組
aws elbv2 create-target-group \
    --name query-service-tg \
    --protocol HTTP \
    --port 8000 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-path /health \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2

export TG_ARN=$(aws elbv2 describe-target-groups \
    --names query-service-tg \
    --query "TargetGroups[0].TargetGroupArn" --output text)

# 建立監聽器
aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=$TG_ARN
```

### 步驟 7: 建立 ECS 服務

```bash
# 建立服務定義檔案
cat > service-definition.json << EOF
{
  "serviceName": "query-service",
  "cluster": "query-service-cluster",
  "taskDefinition": "query-service",
  "desiredCount": 2,
  "launchType": "FARGATE",
  "platformVersion": "LATEST",
  "networkConfiguration": {
    "awsvpcConfiguration": {
      "subnets": [$(echo $SUBNET_IDS | sed 's/ /","/g' | sed 's/^/"/' | sed 's/$/"/')],
      "securityGroups": ["$ECS_SG_ID"],
      "assignPublicIp": "ENABLED"
    }
  },
  "loadBalancers": [
    {
      "targetGroupArn": "$TG_ARN",
      "containerName": "ecs-handler",
      "containerPort": 8000
    }
  ],
  "deploymentConfiguration": {
    "maximumPercent": 200,
    "minimumHealthyPercent": 50,
    "deploymentCircuitBreaker": {
      "enable": true,
      "rollback": true
    }
  },
  "enableExecuteCommand": true
}
EOF

# 建立服務
aws ecs create-service --cli-input-json file://service-definition.json
```

### 步驟 8: 建立 Internal API Gateway

```bash
# 建立 API Gateway
aws apigateway create-rest-api \
    --name query-service-internal-api \
    --endpoint-configuration types=PRIVATE \
    --policy '{
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": "*",
          "Action": "execute-api:Invoke",
          "Resource": "*",
          "Condition": {
            "StringEquals": {
              "aws:sourceVpc": "'$VPC_ID'"
            }
          }
        }
      ]
    }'

export API_ID=$(aws apigateway get-rest-apis \
    --query "items[?name=='query-service-internal-api'].id" --output text)

# 取得根資源 ID
export ROOT_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --query "items[?path=='/'].id" --output text)

# 建立 /query 資源
aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_ID \
    --path-part query

export QUERY_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --query "items[?pathPart=='query'].id" --output text)

# 建立 /query/user 資源和方法
aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $QUERY_ID \
    --path-part user

export USER_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --query "items[?pathPart=='user'].id" --output text)

aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $USER_ID \
    --http-method POST \
    --authorization-type NONE

# 配置 Lambda 整合
aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $USER_ID \
    --http-method POST \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:$AWS_REGION:lambda:path/2015-03-31/functions/arn:aws:lambda:$AWS_REGION:$AWS_ACCOUNT:function:query-result-lambda/invocations"

# 部署 API
aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name v1
```

## 🧪 部署驗證

### 1. 服務健康檢查

```bash
# 檢查 ECS 服務狀態
aws ecs describe-services \
    --cluster query-service-cluster \
    --services query-service

# 檢查任務狀態
aws ecs list-tasks \
    --cluster query-service-cluster \
    --service-name query-service

# 檢查負載均衡器狀態
aws elbv2 describe-target-health \
    --target-group-arn $TG_ARN
```

### 2. 功能測試

```bash
# 取得 ALB DNS 名稱
export ALB_DNS=$(aws elbv2 describe-load-balancers \
    --load-balancer-arns $ALB_ARN \
    --query "LoadBalancers[0].DNSName" --output text)

# 測試健康檢查
curl http://$ALB_DNS/health

# 測試查詢功能
curl -X POST http://$ALB_DNS/query/user \
    -H "Content-Type: application/json" \
    -d '{"user_id": "test_user_001", "limit": 10}'
```

### 3. 日誌檢查

```bash
# 查看 ECS 任務日誌
aws logs tail /ecs/query-service --follow

# 查看特定日誌串流
aws logs get-log-events \
    --log-group-name /ecs/query-service \
    --log-stream-name ecs/ecs-handler/$(aws ecs list-tasks \
        --cluster query-service-cluster \
        --service-name query-service \
        --query "taskArns[0]" --output text | cut -d'/' -f3)
```

## 📊 監控設定

### 1. CloudWatch 告警

```bash
# CPU 使用率告警
aws cloudwatch put-metric-alarm \
    --alarm-name "ECS-query-service-HighCPU" \
    --alarm-description "High CPU usage for query service" \
    --metric-name CPUUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 70 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2 \
    --alarm-actions arn:aws:sns:$AWS_REGION:$AWS_ACCOUNT:query-service-alerts \
    --dimensions Name=ServiceName,Value=query-service Name=ClusterName,Value=query-service-cluster

# 記憶體使用率告警
aws cloudwatch put-metric-alarm \
    --alarm-name "ECS-query-service-HighMemory" \
    --alarm-description "High memory usage for query service" \
    --metric-name MemoryUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2 \
    --alarm-actions arn:aws:sns:$AWS_REGION:$AWS_ACCOUNT:query-service-alerts \
    --dimensions Name=ServiceName,Value=query-service Name=ClusterName,Value=query-service-cluster
```

### 2. 應用程式深度監控

```bash
# 安裝 CloudWatch Container Insights
aws ecs put-account-setting \
    --name containerInsights \
    --value enabled
```

## 🔄 更新和維護

### 1. 滾動更新

```bash
# 建構新版本映像
docker build -t query-service:$(git rev-parse --short HEAD) ./eks_handler
docker tag query-service:$(git rev-parse --short HEAD) $ECR_REGISTRY/query-service:$(git rev-parse --short HEAD)
docker push $ECR_REGISTRY/query-service:$(git rev-parse --short HEAD)

# 更新任務定義
# 編輯 task-definition.json 中的映像標籤
aws ecs register-task-definition --cli-input-json file://task-definition.json

# 更新服務
aws ecs update-service \
    --cluster query-service-cluster \
    --service query-service \
    --task-definition query-service:$(aws ecs describe-task-definition \
        --task-definition query-service \
        --query "taskDefinition.revision" --output text)
```

### 2. 擴展服務

```bash
# 水平擴展
aws ecs update-service \
    --cluster query-service-cluster \
    --service query-service \
    --desired-count 4

# 垂直擴展（需要新的任務定義）
# 編輯 task-definition.json 中的 CPU 和記憶體設定
aws ecs register-task-definition --cli-input-json file://task-definition.json
aws ecs update-service \
    --cluster query-service-cluster \
    --service query-service \
    --task-definition query-service:NEW_REVISION
```

## 🗑️ 清理資源

### 完整清理腳本

```bash
#!/bin/bash

# 停止並刪除 ECS 服務
aws ecs update-service \
    --cluster query-service-cluster \
    --service query-service \
    --desired-count 0

aws ecs delete-service \
    --cluster query-service-cluster \
    --service query-service \
    --force

# 刪除任務定義（取消註冊所有版本）
for revision in $(aws ecs list-task-definitions \
    --family-prefix query-service \
    --query "taskDefinitionArns[]" --output text); do
    aws ecs deregister-task-definition --task-definition $revision
done

# 刪除 ECS 叢集
aws ecs delete-cluster --cluster query-service-cluster

# 刪除負載均衡器
aws elbv2 delete-load-balancer --load-balancer-arn $ALB_ARN
aws elbv2 delete-target-group --target-group-arn $TG_ARN

# 刪除安全群組
aws ec2 delete-security-group --group-id $ECS_SG_ID
aws ec2 delete-security-group --group-id $ALB_SG_ID

# 刪除 IAM 角色
aws iam detach-role-policy \
    --role-name ecsTaskExecutionRole-query-service \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

aws iam delete-role-policy \
    --role-name ecsTaskRole-query-service \
    --policy-name QueryServiceTaskPolicy

aws iam delete-role --role-name ecsTaskExecutionRole-query-service
aws iam delete-role --role-name ecsTaskRole-query-service

# 刪除 API Gateway
aws apigateway delete-rest-api --rest-api-id $API_ID

# 刪除 ECR 儲存庫
aws ecr delete-repository \
    --repository-name query-service \
    --force

echo "清理完成！"
```

## 📝 故障排除

### 常見問題和解決方案

1. **任務無法啟動**

   ```bash
   # 檢查任務定義
   aws ecs describe-task-definition --task-definition query-service

   # 檢查服務事件
   aws ecs describe-services --cluster query-service-cluster --services query-service
   ```

2. **健康檢查失敗**

   ```bash
   # 檢查目標群組健康狀態
   aws elbv2 describe-target-health --target-group-arn $TG_ARN

   # 檢查安全群組規則
   aws ec2 describe-security-groups --group-ids $ECS_SG_ID
   ```

3. **記憶體或 CPU 不足**
   ```bash
   # 更新任務定義中的資源配置
   # 編輯 task-definition.json
   aws ecs register-task-definition --cli-input-json file://task-definition.json
   ```

## 📚 相關文檔

- [ECS 遷移指南](../architecture/ecs-migration-guide.md)
- [API 變更說明](../api/api-changes-v3.md)
- [測試驗證指南](../testing/VERIFICATION_GUIDE.md)
