
# Query Service - Hexagonal Architecture with LocalStack

本文件描述如何在本地使用 AWS + LocalStack 模擬查詢側六邊形架構，透過 Docker Compose 啟動整體查詢流程：

```
使用者 -> API Gateway -> Lambda Adapter(QueryLambda Adapter) -> EKS 模擬 Handler(QueryHandler) -> Lambda Adapter(QueryResultLambda Adapter) -> DynamoDB (Read-only)
```

---

## 🎯 任務目標

建立一組查詢 API，包含以下功能：

1. 根據 `user_id` 查詢該用戶最近的推播紀錄（最多 10 筆，依照 `created_at` 倒序）
2. 根據 `marketing_id` 查詢某活動所觸發的所有推播紀錄
3. 根據 `transaction_id` 查詢失敗的推播紀錄（`status = FAILED`）

模擬架構中，EKS handler 作為應用核心處理層；所有組件皆可在 LocalStack 中運行，並由 Docker Compose 管理。

---

## 🧱 專案目錄結構

```
query-service/
├── docker-compose.yml                # 啟動 LocalStack + EKS handler
├── infra/localstack/setup.sh         # DynamoDB 建表初始化腳本
├── lambdas/
│   ├── query_lambda/app.py           # Lambda: 接 API Gateway 請求
│   └── query_result_lambda/app.py    # Lambda: 查詢 DynamoDB 回傳結果
├── eks-handler/main.py               # 模擬 EKS handler（用 FastAPI）
├── requirements.txt
```

---

## 🧩 DynamoDB Table Schema

| 欄位名稱             | 類型       | 說明                                   |
|----------------------|------------|----------------------------------------|
| `user_id`            | String (S) | Partition Key，也可以改為 token 等識別 |
| `created_at`         | Number (N) | Sort Key，毫秒時間戳，支援倒序查詢     |
| `transaction_id`     | String (S) | 對應 Command 表主鍵                    |
| `marketing_id`       | String (S) | 活動代碼，可為空                        |
| `notification_title` | String (S) | 通知標題                                |
| `status`             | String (S) | SENT / DELIVERED / FAILED              |
| `error_msg`          | String (S) | 失敗原因，可為空                        |
| `platform`           | String (S) | ANDROID / IOS / WEBPUSH                |

可依需求建立 GSI：

- GSI on `marketing_id`
- GSI on `transaction_id` + `status`

---

## 🗂️ API Gateway 配置

設計以下三種查詢路由：

1. `/query/user?user_id=xxx`
2. `/query/marketing?marketing_id=xxx`
3. `/query/failures?transaction_id=xxx`

所有路由綁定到同一個 `query_lambda`，內部由 handler 判斷執行不同查詢邏輯。

---

## 🔁 Lambda 與 Handler 說明

### 1. `query_lambda`
- 接收 API Gateway 請求
- 呼叫對應的內部 EKS handler

### 2. EKS handler（FastAPI）
- 根據 URL 路由與參數執行三種邏輯之一
- 呼叫 `query_result_lambda`，傳入條件（user_id / marketing_id / transaction_id）

### 3. `query_result_lambda`
- 查詢 DynamoDB
- 支援以下三種模式：
  - 根據 `user_id` 與 `created_at` 倒序查詢最近紀錄
  - 根據 `marketing_id` 查詢全部紀錄（GSI）
  - 根據 `transaction_id` 查詢 `status = FAILED` 的紀錄（GSI）

---

## 🧪 測試與驗證

1. 啟動 Docker Compose：
   ```bash
   docker-compose up
   ```

2. 初始化 DynamoDB 表：
   ```bash
   chmod +x infra/localstack/setup.sh
   docker exec -it <localstack_container_id> /etc/localstack/init/ready.d/setup.sh
   ```

3. 呼叫 API：
   ```bash
   curl "http://localhost:4566/restapis/.../query/user?user_id=test_user"
   curl "http://localhost:4566/restapis/.../query/marketing?marketing_id=abc123"
   curl "http://localhost:4566/restapis/.../query/failures?transaction_id=tx_456"
   ```

---

## ✅ 任務成果目標

- 完整專案目錄與程式碼
- Docker Compose 一鍵啟動
- Lambda 建立與部署腳本
- 可運行的模擬查詢環境，支援多種條件查詢

---
