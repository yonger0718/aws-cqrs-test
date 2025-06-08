# Migration V3 實施文檔

## 📋 概述

本文檔詳細說明了 Query Service 從 Lambda + API Gateway 架構遷移到 ECS Fargate + Internal API Gateway 架構的實施細節。

## 🔄 主要變更

### 1. 資料庫結構變更

#### Command Records 表新增欄位

- **新增欄位**: `ap_id` (String)
- **用途**: 服務的來源 AP ID
- **範例值**: `mobile-app-001`, `web-portal-001`, `mobile-app-002`

#### 測試資料更新

所有測試資料已更新包含 `ap_id` 欄位：

```json
{
  "transaction_id": "tx_001",
  "ap_id": "mobile-app-001"
  // ... 其他欄位
}
```

### 2. API 端點變更

#### 端點重命名

- **舊端點**: `/query/failure` 或 `/failed`
- **新端點**: `/query/fail`
- **影響範圍**:
  - FastAPI 服務
  - Lambda 函數
  - API Gateway 配置

### 3. 架構遷移

#### 從 Lambda 到 ECS Fargate

```txt
舊架構: API Gateway -> EKS → Lambda Functions → DynamoDB
新架構: Internal API Gateway → ECS Fargate → Lambda Functions → DynamoDB
```

#### 新增組件

1. **ECS Fargate 服務**

   - 容器化的 FastAPI 應用
   - 自動擴展和健康檢查
   - Service Discovery 整合

2. **Internal API Gateway**

   - VPC 內部 API Gateway
   - VPC Link 連接到 ALB
   - 私有端點配置

3. **Application Load Balancer**
   - 內部負載均衡器
   - 健康檢查配置
   - Target Group 管理

## 📁 新增檔案結構

```
query-service/
├── infra/
│   ├── ecs/
│   │   ├── task-definition.json
│   │   └── service-definition.json
│   ├── api-gateway/
│   │   └── internal-api.json
│   └── terraform/
│       ├── main.tf
│       ├── iam.tf
│       ├── api-gateway.tf
│       └── outputs.tf
└── scripts/
    └── deploy-ecs.sh
```

## 🔧 技術實施細節

### 1. ECS Fargate 配置

#### 任務定義

- **CPU**: 256 vCPU
- **Memory**: 512 MB
- **網路模式**: awsvpc
- **日誌**: CloudWatch Logs

#### 服務配置

- **期望任務數**: 2
- **部署策略**: Rolling Update
- **健康檢查**: `/health` 端點

### 2. Internal API Gateway

#### 端點配置

- `POST /query/user` - 用戶查詢
- `POST /query/marketing` - 行銷活動查詢
- `POST /query/fail` - 失敗記錄查詢
- `GET /health` - 健康檢查

#### 安全配置

- VPC 內部存取限制
- VPC Link 連接
- 私有 DNS 解析

### 3. 資料模型更新

#### Stream Processor Lambda

```python
@dataclass
class CommandRecord:
    # ... 現有欄位
    ap_id: Optional[str] = None  # 新增

@dataclass
class QueryRecord:
    # ... 現有欄位
    ap_id: Optional[str] = None  # 新增
```

#### FastAPI 模型

```python
class NotificationRecord(BaseModel):
    # ... 現有欄位
    ap_id: Optional[str] = None  # 新增
```

## 🚀 部署流程

### 1. 本地開發環境

```bash
# 啟動 LocalStack 環境
cd query-service
docker-compose up -d

# 執行測試
python -m pytest tests/
```

### 2. AWS 生產環境

```bash
# 設定環境變數
export VPC_ID=vpc-xxxxxxxxx
export PRIVATE_SUBNET_1=subnet-xxxxxxxxx
export PRIVATE_SUBNET_2=subnet-yyyyyyyyy
export AWS_REGION=ap-southeast-1

# 執行部署腳本
./query-service/scripts/deploy-ecs.sh
```

### 3. Terraform 部署

```bash
cd query-service/infra/terraform

# 初始化
terraform init

# 規劃
terraform plan \
  -var="vpc_id=$VPC_ID" \
  -var="private_subnet_ids=[\"$PRIVATE_SUBNET_1\",\"$PRIVATE_SUBNET_2\"]"

# 部署
terraform apply
```

## 🧪 測試驗證

### 1. 健康檢查

```bash
# ECS 服務健康檢查
curl http://internal-alb.query-service.local/health

# API Gateway 健康檢查
curl https://internal-api-id.execute-api.ap-southeast-1.amazonaws.com/v1/health
```

### 2. 功能測試

```bash
# 用戶查詢
curl -X POST https://internal-api-id.execute-api.ap-southeast-1.amazonaws.com/v1/query/user \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user_001"}'

# 行銷活動查詢
curl -X POST https://internal-api-id.execute-api.ap-southeast-1.amazonaws.com/v1/query/marketing \
  -H "Content-Type: application/json" \
  -d '{"marketing_id": "campaign_2024_new_year"}'

# 失敗記錄查詢
curl -X POST https://internal-api-id.execute-api.ap-southeast-1.amazonaws.com/v1/query/fail \
  -H "Content-Type: application/json" \
  -d '{"transaction_id": "tx_002"}'
```

## 📊 監控和日誌

### 1. CloudWatch 指標

- ECS 服務 CPU/Memory 使用率
- ALB 目標健康狀態
- API Gateway 請求數和延遲

### 2. 日誌配置

- ECS 任務日誌: `/ecs/query-service`
- API Gateway 存取日誌
- ALB 存取日誌

## 🔒 安全考量

### 1. 網路安全

- 所有服務部署在私有子網
- Security Group 限制存取
- VPC Endpoint 用於 AWS 服務存取

### 2. IAM 權限

- ECS 執行角色: ECR、CloudWatch 存取
- ECS 任務角色: Lambda、DynamoDB 存取
- 最小權限原則

## 📈 效能優化

### 1. 自動擴展

- ECS 服務自動擴展配置
- Target Tracking 基於 CPU 使用率
- 最小/最大任務數限制

### 2. 快取策略

- API Gateway 回應快取
- 應用層快取 (如需要)

## 🔄 回滾計劃

### 1. 快速回滾

```bash
# 回滾到前一個任務定義
aws ecs update-service \
  --cluster query-service-cluster \
  --service query-service \
  --task-definition query-service-task:PREVIOUS_REVISION
```

### 2. 完整回滾

```bash
# 使用 Terraform 回滾
terraform apply -target=aws_ecs_service.query_service \
  -var="task_definition_revision=PREVIOUS_REVISION"
```

## ✅ 驗收標準

### 1. 功能驗收

- [ ] 所有 API 端點正常回應
- [ ] 資料查詢結果正確
- [ ] 新增 `ap_id` 欄位正確同步
- [ ] 健康檢查通過

### 2. 效能驗收

- [ ] API 回應時間 < 500ms
- [ ] 服務可用性 > 99.9%
- [ ] 自動擴展正常運作

### 3. 安全驗收

- [ ] 僅 VPC 內部可存取
- [ ] IAM 權限最小化
- [ ] 日誌記錄完整

## 📝 後續工作

1. **監控告警設定**

   - CloudWatch 告警配置
   - SNS 通知設定

2. **效能調優**

   - 根據實際負載調整資源配置
   - 優化查詢效能

3. **文檔更新**
   - API 文檔更新
   - 運維手冊更新

## 🆘 故障排除

### 常見問題

1. **ECS 任務啟動失敗**

   - 檢查 ECR 映像是否存在
   - 驗證 IAM 權限
   - 查看 CloudWatch 日誌

2. **API Gateway 502 錯誤**

   - 檢查 VPC Link 狀態
   - 驗證 ALB 目標健康狀態
   - 檢查 Security Group 規則

3. **資料同步問題**
   - 檢查 DynamoDB Stream 狀態
   - 驗證 Lambda 函數執行
   - 查看 Stream Processor 日誌

---

**實施完成日期**: 2024 年 12 月
**負責團隊**: DevOps & Backend Team
**版本**: v3.0.0
