# Query Service - CQRS 查詢服務

本目錄包含 CQRS 架構中的查詢端實現，基於六邊形架構模式。

## 🏗️ 服務概述

查詢服務負責處理所有的讀取操作，通過 API Gateway 接收請求，並從專門的查詢數據表中檢索數據。

```txt
用戶請求 → API Gateway → Query Lambda → ECS Handler → Internal API Gateway → Query Result Lambda → Query Table
```

## 📁 目錄結構

```txt
query-service/
├── eks_handler/                      # FastAPI 應用（六邊形架構，ECS 容器）
│   ├── main.py                       # 主應用程序
│   ├── Dockerfile                    # ECS 容器配置
│   └── requirements.txt              # 服務依賴
├── lambdas/                          # AWS Lambda 函數
│   ├── query_lambda/                 # API Gateway 入口
│   ├── query_result_lambda/          # 查詢處理邏輯（透過 Internal API Gateway）
│   └── stream_processor_lambda/      # DynamoDB Stream 處理
├── tests/                            # 測試套件
│   ├── test_eks_handler.py           # 單元測試（HTTP 通信架構）
│   └── test_integration.py           # 整合測試
├── infra/                            # 基礎設施配置
│   ├── localstack/setup.sh          # LocalStack 初始化
│   └── terraform/                    # ECS/Terraform 部署配置
├── docker-compose.yml               # 本地開發環境
└── requirements.txt                  # Lambda 依賴
```

## 🗄️ 資料表設計

### Command Table (command-records) - 寫入側

| 欄位名稱             | 類型       | 說明                      |
| -------------------- | ---------- | ------------------------- |
| `transaction_id`     | String (S) | Partition Key，交易 ID    |
| `created_at`         | Number (N) | Sort Key，毫秒時間戳      |
| `user_id`            | String (S) | 用戶識別碼                |
| `marketing_id`       | String (S) | 活動代碼                  |
| `ap_id`              | String (S) | 服務來源 AP ID            |
| `notification_title` | String (S) | 通知標題                  |
| `status`             | String (S) | SENT / DELIVERED / FAILED |
| `platform`           | String (S) | IOS / ANDROID / WEBPUSH   |
| `device_token`       | String (S) | 設備推播令牌              |
| `payload`            | String (S) | 推播內容 JSON             |
| `error_msg`          | String (S) | 失敗原因（可選）          |

**特色**: 啟用 DynamoDB Stream，支援 NEW_AND_OLD_IMAGES

### Query Table (notification-records) - 查詢側

| 欄位名稱             | 類型       | 說明                               |
| -------------------- | ---------- | ---------------------------------- |
| `user_id`            | String (S) | Partition Key                      |
| `created_at`         | Number (N) | Sort Key，毫秒時間戳，支援倒序查詢 |
| `transaction_id`     | String (S) | 交易 ID                            |
| `marketing_id`       | String (S) | 活動代碼                           |
| `ap_id`              | String (S) | 服務來源 AP ID                     |
| `notification_title` | String (S) | 通知標題                           |
| `status`             | String (S) | SENT / DELIVERED / FAILED          |
| `platform`           | String (S) | IOS / ANDROID / WEBPUSH            |
| `error_msg`          | String (S) | 失敗原因（可選）                   |

**GSI 索引**:

- `marketing_id-index`: 根據活動查詢
- `transaction_id-status-index`: 根據交易狀態查詢

## 🚀 本地開發

### 使用 Poetry 管理依賴

```bash
# 安裝專案依賴（在根目錄執行）
poetry install

# 進入虛擬環境
poetry shell

# 執行測試
poetry run pytest tests/ -v --cov
```

### 🐳 Docker 化部署（推薦）

我們提供了完整的 Docker 化部署解決方案，包括容器化的 Lambda 函數：

```bash
# 一鍵啟動完整環境（包含 Lambda Docker 部署）
./deploy_docker.sh start

# 構建 Lambda Docker 映像
./deploy_docker.sh build

# 部署 Lambda 函數
./deploy_docker.sh deploy

# 檢查服務狀態
./deploy_docker.sh status

# 執行集成測試
./deploy_docker.sh test

# 查看服務日誌
./deploy_docker.sh logs

# 停止所有服務
./deploy_docker.sh stop

# 清理所有資源
./deploy_docker.sh clean
```

#### Lambda Docker 映像結構

每個 Lambda 函數都有自己的 Dockerfile：

```txt
lambdas/
├── docker-compose.lambda.yml         # Lambda 映像構建配置
├── deploy_docker_lambdas.sh          # Docker 部署腳本
├── stream_processor_lambda/
│   ├── Dockerfile                    # 🐳 Stream 處理器容器
│   ├── .dockerignore                 # Docker 忽略檔案
│   └── app.py
├── query_lambda/
│   ├── Dockerfile                    # 🐳 查詢入口容器
│   ├── .dockerignore
│   └── app.py
└── query_result_lambda/
    ├── Dockerfile                    # 🐳 查詢結果容器
    ├── .dockerignore
    └── app.py
```

### 傳統 Docker Compose 部署

```bash
# 啟動服務
docker compose up -d

# 檢查服務狀態
docker compose ps

# 查看日誌
docker compose logs ecs-handler
```

### LocalStack 初始化

#### Docker 版本（推薦）

```bash
# 使用 Docker 化的 Lambda 部署
docker exec -it localstack-query-service /etc/localstack/init/ready.d/setup_docker.sh
```

#### 傳統版本

```bash
# 使用 ZIP 包部署
docker exec -it localstack-query-service /etc/localstack/init/ready.d/setup.sh
```

## 📋 API 端點

| 端點               | 方法 | 說明               |
| ------------------ | ---- | ------------------ |
| `/query/user`      | GET  | 查詢用戶推播記錄   |
| `/query/marketing` | GET  | 查詢活動推播統計   |
| `/query/fail`      | GET  | 查詢失敗推播記錄   |
| `/health`          | GET  | 健康檢查           |
| `/docs`            | GET  | API 文檔 (Swagger) |

### 查詢參數示例

```bash
# 查詢用戶推播記錄
GET /query/user?user_id=test_user_001&limit=10

# 查詢活動推播記錄
GET /query/marketing?marketing_id=campaign_2024&limit=20

# 查詢失敗記錄
GET /query/fail?transaction_id=tx_002
```

## 🧪 測試

### 單元測試

```bash
# 執行所有測試
poetry run pytest

# 執行特定測試文件
poetry run pytest tests/test_eks_handler.py -v

# 生成覆蓋率報告
poetry run pytest --cov=eks_handler --cov-report=html
```

### 整合測試

```bash
# 確保服務已啟動
docker compose up -d

# 執行整合測試
poetry run pytest tests/test_integration.py -v
```

## 🔧 開發工具

### 代碼格式化

```bash
# 使用 Black 格式化代碼
poetry run black eks_handler/

# 使用 isort 整理 import
poetry run isort eks_handler/
```

### 類型檢查

```bash
# 使用 mypy 進行類型檢查
poetry run mypy eks_handler/
```

### 預提交鉤子

```bash
# 安裝 pre-commit 鉤子
poetry run pre-commit install

# 手動執行所有檢查
poetry run pre-commit run --all-files
```

## 🔍 故障排除

### 常見問題

1. **LocalStack 連接失敗**

   ```bash
   # 檢查 LocalStack 狀態
   docker-compose logs localstack

   # 重啟 LocalStack
   docker-compose restart localstack
   ```

2. **依賴安裝問題**

   ```bash
   # 清理並重新安裝
   poetry env remove --all
   poetry install
   ```

3. **API Gateway 配置問題**

   ```bash
   # 使用根目錄的修復腳本
   cd .. && ./scripts/fix_api_gateway.sh
   ```

## 📖 相關文檔

- [主專案文檔](../README.md)
- [架構設計文檔](../docs/architecture/)
- [測試指南](../docs/testing/)
- [部署指南](../docs/deployment/)
