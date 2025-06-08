# ECS Fargate 遷移指南

## 📋 概述

本文檔詳細說明專案從 EKS (Elastic Kubernetes Service) 遷移到 ECS Fargate (Elastic Container Service) 的完整過程和架構變更。

## 🔄 架構變更概覽

### 遷移前架構 (EKS)

```txt
用戶請求 → API Gateway → Query Lambda → EKS Handler → DynamoDB
```

### 遷移後架構 (ECS Fargate)

```txt
用戶請求 → API Gateway → Query Lambda → ECS Handler → Internal API Gateway → Query Result Lambda → DynamoDB
```

## 🎯 主要變更項目

### 1. 容器平台遷移

| 項目           | 遷移前 (EKS)         | 遷移後 (ECS Fargate) |
| -------------- | -------------------- | -------------------- |
| **平台**       | Kubernetes           | ECS Fargate          |
| **管理複雜度** | 高 (需管理 K8s 叢集) | 低 (無伺服器容器)    |
| **擴展方式**   | Pod 自動擴展         | 任務自動擴展         |
| **網路**       | K8s 網路模型         | AWS VPC 網路         |
| **日誌**       | K8s 日誌系統         | CloudWatch Logs      |

### 2. 服務通信架構

#### 遷移前：直接調用

- EKS Handler 直接調用 Lambda 函數
- 使用 `LambdaAdapter.invoke_lambda()` 方法

#### 遷移後：HTTP 通信

- ECS Handler 透過 Internal API Gateway 調用 Lambda
- 使用 HTTP 客戶端進行通信
- 增加了一層 API Gateway 抽象

### 3. 資料庫 Schema 更新

新增 `ap_id` 欄位到所有相關表格：

```sql
-- Command Records 表
ALTER TABLE command-records ADD COLUMN ap_id STRING;

-- Notification Records 表
ALTER TABLE notification-records ADD COLUMN ap_id STRING;
```

**ap_id 欄位說明：**

- 用途：標識服務來源的 AP ID
- 範例值：`mobile-app-001`, `web-portal-001`, `mobile-app-002`
- 類型：String (S)
- 必填：否 (Optional)

### 4. API 端點重命名

| 功能     | 遷移前端點                     | 遷移後端點                |
| -------- | ------------------------------ | ------------------------- |
| 失敗查詢 | `/query/failures` 或 `/failed` | `/query/fail`             |
| 用戶查詢 | `/query/user`                  | `/query/user` (不變)      |
| 活動查詢 | `/query/marketing`             | `/query/marketing` (不變) |

## 🏗️ 技術實施細節

### 1. ECS Fargate 配置

#### 任務定義 (Task Definition)

```json
{
  "family": "query-service",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "ecs-handler",
      "image": "your-account.dkr.ecr.region.amazonaws.com/query-service:latest",
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
          "value": "https://internal-api-id.execute-api.region.amazonaws.com/v1"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/query-service",
          "awslogs-region": "ap-southeast-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### 服務定義 (Service Definition)

```json
{
  "serviceName": "query-service",
  "cluster": "query-service-cluster",
  "taskDefinition": "query-service:1",
  "desiredCount": 2,
  "launchType": "FARGATE",
  "networkConfiguration": {
    "awsvpcConfiguration": {
      "subnets": ["subnet-xxx", "subnet-yyy"],
      "securityGroups": ["sg-xxx"],
      "assignPublicIp": "DISABLED"
    }
  },
  "loadBalancers": [
    {
      "targetGroupArn": "arn:aws:elasticloadbalancing:region:account:targetgroup/query-service/xxx",
      "containerName": "ecs-handler",
      "containerPort": 8000
    }
  ]
}
```

### 2. Internal API Gateway 設定

#### API Gateway 配置

```yaml
openapi: 3.0.0
info:
  title: Internal Query API
  version: 1.0.0
paths:
  /query/user:
    post:
      summary: 查詢用戶推播記錄
      x-amazon-apigateway-integration:
        type: aws_proxy
        httpMethod: POST
        uri: arn:aws:apigateway:region:lambda:path/2015-03-31/functions/arn:aws:lambda:region:account:function:query-result-lambda/invocations
  /query/marketing:
    post:
      summary: 查詢活動推播記錄
      x-amazon-apigateway-integration:
        type: aws_proxy
        httpMethod: POST
        uri: arn:aws:apigateway:region:lambda:path/2015-03-31/functions/arn:aws:lambda:region:account:function:query-result-lambda/invocations
  /query/fail:
    post:
      summary: 查詢失敗推播記錄
      x-amazon-apigateway-integration:
        type: aws_proxy
        httpMethod: POST
        uri: arn:aws:apigateway:region:lambda:path/2015-03-31/functions/arn:aws:lambda:region:account:function:query-result-lambda/invocations
```

### 3. 程式碼變更

#### 環境變數更新

```bash
# ECS 容器環境變數
ENVIRONMENT=production
INTERNAL_API_URL=https://internal-api-id.execute-api.ap-southeast-1.amazonaws.com/v1
REQUEST_TIMEOUT=30
AWS_DEFAULT_REGION=ap-southeast-1
```

#### HTTP 客戶端實作

```python
import httpx
from typing import Optional, Dict, Any

class InternalApiClient:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout

    async def query_user(self, user_id: str, limit: Optional[int] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/query/user",
                json={"user_id": user_id, "limit": limit}
            )
            response.raise_for_status()
            return response.json()

    async def query_marketing(self, marketing_id: str, limit: Optional[int] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/query/marketing",
                json={"marketing_id": marketing_id, "limit": limit}
            )
            response.raise_for_status()
            return response.json()

    async def query_fail(self, transaction_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/query/fail",
                json={"transaction_id": transaction_id}
            )
            response.raise_for_status()
            return response.json()
```

## 🚀 部署流程

### 1. 本地開發環境

```bash
# 1. 確保 Docker Compose 配置正確
cd query-service
docker-compose up -d

# 2. 驗證服務啟動
curl http://localhost:8000/health

# 3. 執行測試
poetry run pytest tests/ -v
```

### 2. AWS 生產環境部署

```bash
# 1. 建立 ECR 儲存庫
aws ecr create-repository --repository-name query-service

# 2. 建構並推送映像
docker build -t query-service ./eks_handler
docker tag query-service:latest $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/query-service:latest
docker push $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/query-service:latest

# 3. 建立 ECS 叢集
aws ecs create-cluster --cluster-name query-service-cluster --capacity-providers FARGATE

# 4. 註冊任務定義
aws ecs register-task-definition --cli-input-json file://task-definition.json

# 5. 建立服務
aws ecs create-service --cli-input-json file://service-definition.json
```

### 3. 使用 Terraform 自動化部署

```bash
cd infra/terraform

# 初始化
terraform init

# 規劃部署
terraform plan \
  -var="cluster_name=query-service-cluster" \
  -var="service_name=query-service" \
  -var="image_uri=$AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/query-service:latest"

# 執行部署
terraform apply
```

## 🧪 測試驗證

### 1. 健康檢查驗證

```bash
# ECS 服務健康檢查
curl http://internal-alb.query-service.local/health

# API Gateway 健康檢查
curl https://internal-api-id.execute-api.ap-southeast-1.amazonaws.com/v1/health
```

### 2. 功能測試

```bash
# 用戶查詢測試
curl -X POST https://api-id.execute-api.ap-southeast-1.amazonaws.com/v1/query/user \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user_001", "limit": 10}'

# 失敗查詢測試 (新端點)
curl -X POST https://api-id.execute-api.ap-southeast-1.amazonaws.com/v1/query/fail \
  -H "Content-Type: application/json" \
  -d '{"transaction_id": "tx_002"}'
```

### 3. 效能測試

```bash
# 使用 Apache Bench 進行負載測試
ab -n 1000 -c 10 http://internal-alb.query-service.local/health

# 使用 wrk 進行效能測試
wrk -t4 -c10 -d30s --script=query-test.lua http://internal-alb.query-service.local/
```

## 📊 監控與日誌

### 1. CloudWatch 監控

#### 關鍵指標

- **CPU 使用率**: 目標 < 70%
- **記憶體使用率**: 目標 < 80%
- **響應時間**: 目標 < 100ms
- **錯誤率**: 目標 < 1%

#### 告警設定

```json
{
  "AlarmName": "ECS-HighCPU",
  "MetricName": "CPUUtilization",
  "Namespace": "AWS/ECS",
  "Statistic": "Average",
  "Period": 300,
  "EvaluationPeriods": 2,
  "Threshold": 70,
  "ComparisonOperator": "GreaterThanThreshold"
}
```

### 2. 日誌管理

```bash
# 查看 ECS 任務日誌
aws logs get-log-events \
  --log-group-name /ecs/query-service \
  --log-stream-name ecs/ecs-handler/task-id

# 即時日誌監控
aws logs tail /ecs/query-service --follow
```

## 🔧 故障排除

### 常見問題與解決方案

#### 1. ECS 任務啟動失敗

```bash
# 檢查任務定義
aws ecs describe-task-definition --task-definition query-service

# 檢查服務事件
aws ecs describe-services --cluster query-service-cluster --services query-service
```

#### 2. Internal API Gateway 連接問題

```bash
# 檢查 VPC 連線設定
aws ec2 describe-vpc-endpoints

# 測試網路連通性
curl -v https://internal-api-id.execute-api.ap-southeast-1.amazonaws.com/v1/health
```

#### 3. 記憶體不足

```bash
# 調整任務定義中的記憶體設定
aws ecs register-task-definition \
  --family query-service \
  --memory 1024  # 增加到 1GB
```

## 📝 遷移檢查清單

### 遷移前準備

- [ ] 備份現有 EKS 配置
- [ ] 準備 ECR 儲存庫
- [ ] 設定 IAM 角色和政策
- [ ] 建立 VPC 和子網路配置

### 遷移執行

- [ ] 建構並推送容器映像
- [ ] 建立 ECS 叢集
- [ ] 設定 Internal API Gateway
- [ ] 部署 ECS 服務
- [ ] 配置負載均衡器

### 遷移後驗證

- [ ] 健康檢查通過
- [ ] 功能測試通過
- [ ] 效能測試通過
- [ ] 監控告警設定
- [ ] 日誌收集正常

### 清理作業

- [ ] 關閉舊的 EKS 叢集
- [ ] 刪除未使用的資源
- [ ] 更新文檔和 README
- [ ] 通知團隊成員

## 🎯 效益總結

### 成本效益

- **減少管理負擔**: 無需管理 Kubernetes 叢集
- **按需付費**: Fargate 僅在任務運行時收費
- **自動擴展**: 基於負載自動調整任務數量

### 維運效益

- **簡化部署**: 標準的 ECS 部署流程
- **更好的監控**: 整合 CloudWatch 監控
- **故障隔離**: 任務層級的隔離

### 開發效益

- **標準化架構**: 符合 AWS 最佳實務
- **更好的測試**: HTTP 通信便於整合測試
- **可重用性**: 容器可在其他環境重用
