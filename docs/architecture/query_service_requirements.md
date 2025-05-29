
# Query Service - Hexagonal Architecture with LocalStack

本文件描述如何在本地使用 AWS + LocalStack 模擬查詢側六邊形架構，透過 Docker Compose 啟動整體查詢流程：

```
使用者 -> API Gateway -> Lambda Adapter -> EKS 模擬 Handler -> Lambda Adapter -> DynamoDB (Read-only)
```

---

## 🎯 任務目標

建立一個查詢 API：

- 輸入 `user_id`，從 DynamoDB 中查詢該用戶的最新推播紀錄（最多 10 筆，依照 `created_at` 倒序）
- 模擬 EKS handler 作為應用核心處理層
- 所有服務皆能在 LocalStack 中運行
- 使用 Docker Compose 管理服務組件

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

---

## 🗂️ API Gateway 配置

- 路徑：`/query?user_id=xxx`
- 綁定 Lambda：`query_lambda`
- Lambda 負責轉呼叫模擬 EKS handler HTTP 端點

---

## 🔁 Lambda 流程說明

### 1. `query_lambda`
- 接收 API Gateway 請求
- 呼叫 EKS handler（HTTP）

### 2. EKS handler（FastAPI）
- 解析 user_id
- 呼叫 `query_result_lambda`

### 3. `query_result_lambda`
- 查詢 DynamoDB
- 根據 `user_id` 與 `created_at`（倒序）回傳最多 10 筆

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
   curl "http://localhost:4566/restapis/.../query?user_id=test_user"
   ```

---

## ✅ 任務成果目標

- 完整專案目錄與程式碼
- Docker Compose 一鍵啟動
- Lambda 建立與部署腳本
- 可運行的模擬測試環境

---
