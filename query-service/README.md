# Query Service - Hexagonal Architecture with CQRS & LocalStack

本專案實現了一個使用六邊形架構與 CQRS 模式的查詢服務，透過 LocalStack 模擬 AWS 服務，包含 API Gateway、Lambda 和 DynamoDB，支援讀寫分離架構。

## 🏗️ CQRS 架構概述

```txt
寫入側: Command Table (寫入) → DynamoDB Stream → Stream Processor Lambda → Query Table (讀取)
查詢側: 使用者 → API Gateway → Query Lambda → EKS Handler → Query Result Lambda → Query Table
```

### 架構優勢

1. **讀寫分離**: 寫入和查詢使用不同的表，優化各自的性能
2. **事件驅動**: 透過 DynamoDB Stream 實現異步資料同步
3. **數據轉換**: Stream 處理器可以根據查詢需求轉換資料格式
4. **可擴展性**: 寫入側和查詢側可以獨立擴展

## 📁 專案結構

```txt
aws-hexagon-notify-test/
├── docs/                             # 📚 專案文檔
│   ├── testing/                      # 測試相關文檔
│   ├── guides/                       # 使用指南
│   ├── architecture/                 # 架構文檔
│   └── project/                      # 專案總結
├── scripts/                          # 🔧 腳本工具
│   ├── testing/                      # 測試腳本
│   ├── queries/                      # 查詢腳本
│   ├── verification/                 # 驗證腳本
│   └── development/                  # 開發輔助腳本
└── query-service/                    # 主要服務代碼
    ├── docker-compose.yml            # Docker Compose 配置
    ├── infra/localstack/setup.sh     # LocalStack 初始化腳本
    ├── lambdas/                      # Lambda 函數
    │   ├── query_lambda/             # 接收 API Gateway 請求的 Lambda
    │   ├── query_result_lambda/      # 查詢 DynamoDB 的 Lambda
    │   └── stream_processor_lambda/  # 處理 DynamoDB Stream 的 Lambda
    ├── eks-handler/                  # 模擬 EKS 的 FastAPI 應用
    │   ├── main.py
    │   ├── Dockerfile
    │   └── requirements.txt
    ├── tests/                        # 測試套件
    │   ├── test_eks_handler.py       # 單元測試
    │   └── test_integration.py       # 整合測試
    ├── requirements.txt
    └── README.md
```

## 🗄️ 資料表設計

### Command Table (command-records) - 寫入側

| 欄位名稱             | 類型       | 說明                      |
| -------------------- | ---------- | ------------------------- |
| `transaction_id`     | String (S) | Partition Key，交易 ID    |
| `created_at`         | Number (N) | Sort Key，毫秒時間戳      |
| `user_id`            | String (S) | 用戶識別碼                |
| `marketing_id`       | String (S) | 活動代碼                  |
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
| `notification_title` | String (S) | 通知標題                           |
| `status`             | String (S) | SENT / DELIVERED / FAILED          |
| `platform`           | String (S) | IOS / ANDROID / WEBPUSH            |
| `error_msg`          | String (S) | 失敗原因（可選）                   |

**GSI 索引**:

- `marketing_id-index`: 根據活動查詢
- `transaction_id-status-index`: 根據交易狀態查詢

## 🚀 快速開始

### 1. 系統驗證

```powershell
# 驗證環境和依賴
.\scripts\verification\verify_system.ps1
```

### 2. 啟動服務

```bash
# 進入專案目錄
cd query-service

# 啟動 Docker Compose
docker-compose up -d
```

### 3. 執行初始化腳本

等待 LocalStack 完全啟動後（約 30 秒），執行初始化腳本：

```bash
# 進入 LocalStack 容器執行初始化
docker exec -it localstack-query-service /etc/localstack/init/ready.d/setup.sh
```

### 4. 執行測試驗證

```powershell
# 快速測試
.\scripts\testing\quick_test.ps1

# 完整測試套件
.\scripts\testing\run_tests.ps1
```

## 📋 API 使用範例

### 使用查詢腳本（推薦）

```powershell
# 手動查詢工具
.\scripts\queries\manual_query.ps1

# 簡單查詢
.\scripts\queries\simple_query.ps1 -UserId "test_user_001"

# 進階查詢
.\scripts\queries\query_services.ps1
```

### 直接 API 調用

使用初始化時顯示的 API ID 替換 `{API_ID}`：

```bash
# 查詢用戶推播紀錄
curl "http://localhost:4566/restapis/{API_ID}/dev/query/user?user_id=test_user_001"

# 查詢活動推播紀錄
curl "http://localhost:4566/restapis/{API_ID}/dev/query/marketing?marketing_id=campaign_2024_new_year"

# 查詢失敗的推播紀錄
curl "http://localhost:4566/restapis/{API_ID}/dev/query/failures?transaction_id=tx_002"
```

## 🧪 測試 CQRS 功能

### 使用模擬寫入腳本

```bash
# 安裝依賴
pip install boto3

# 執行模擬寫入腳本
python scripts\development\simulate_writes.py
```

腳本提供以下測試選項：

1. **模擬批次推播**: 模擬行銷活動的批次推播
2. **模擬單個推播**: 模擬單一用戶推播
3. **模擬狀態更新**: 模擬推播狀態變更

### 手動寫入測試

```bash
# 直接寫入到命令表
docker exec -it localstack-query-service awslocal dynamodb put-item \
    --table-name command-records \
    --item '{
        "transaction_id": {"S": "tx_manual_test"},
        "created_at": {"N": "1704300000000"},
        "user_id": {"S": "manual_test_user"},
        "marketing_id": {"S": "manual_campaign"},
        "notification_title": {"S": "手動測試推播"},
        "status": {"S": "SENT"},
        "platform": {"S": "IOS"}
    }'
```

## 🛠️ 開發與調試

### 檢查表結構和數據

```python
# 使用表檢查工具
python scripts\testing\check_tables.py
```

### 查看兩個表的內容

```bash
# 查看命令表（寫入側）
docker exec -it localstack-query-service awslocal dynamodb scan --table-name command-records

# 查看查詢表（讀取側）
docker exec -it localstack-query-service awslocal dynamodb scan --table-name notification-records
```

## 🔧 故障排除

### Stream 未正確處理

1. 檢查 Stream 是否啟用：

   ```bash
   docker exec -it localstack-query-service awslocal dynamodb describe-table \
   --table-name command-records --query 'Table.StreamSpecification'
   ```

2. 檢查事件源映射：

   ```bash
   docker exec -it localstack-query-service awslocal lambda list-event-source-mappings
   ```

3. 查看 Stream Processor Lambda 日誌

### 數據未同步到查詢表

1. 確認命令表中有數據
2. 檢查 Stream Processor Lambda 是否正常執行
3. 檢查查詢表是否為空

### Lambda 函數錯誤

查看具體的 Lambda 日誌：

```bash
docker exec -it localstack-query-service awslocal logs tail /aws/lambda/stream_processor_lambda
```

## 🎯 CQRS 模式優勢

### 1. 性能優化

- **寫入優化**: 命令表針對寫入操作優化，key 設計支援快速插入
- **查詢優化**: 查詢表針對讀取操作優化，包含多個 GSI 支援不同查詢模式

### 2. 可擴展性

- **獨立擴展**: 寫入側和查詢側可以獨立調整容量
- **異步處理**: Stream 處理提供天然的異步解耦

### 3. 數據一致性

- **最終一致性**: 透過 DynamoDB Stream 保證最終數據一致
- **錯誤處理**: Lambda 失敗會自動重試，確保數據不丟失

### 4. 業務邏輯分離

- **命令處理**: 專注於業務邏輯執行和狀態變更
- **查詢處理**: 專注於數據展示和復雜查詢

## 🧹 清理環境

```bash
# 停止並移除所有容器
docker-compose down -v

# 清理 LocalStack 數據卷
rm -rf volume/
```

## 📝 注意事項

1. **LocalStack 限制**: 免費版本的 LocalStack 在 DynamoDB Stream 功能上可能有限制
2. **數據持久化**: 重啟後需要重新初始化，數據不會持久化
3. **Stream 延遲**: LocalStack 中的 Stream 處理可能比 AWS 實際環境慢
4. **錯誤重試**: Stream 處理失敗會自動重試，注意避免重複處理

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！特別歡迎針對 CQRS 模式和 DynamoDB Stream 處理的改進建議。
