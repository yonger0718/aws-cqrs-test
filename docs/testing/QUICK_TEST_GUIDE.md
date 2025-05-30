# 🚀 快速測試指南

## 📋 測試驗證順序

按以下順序執行測試可確保系統完整驗證：

### 🎯 **推薦測試流程**

```bash
# 1. 新環境設置與驗證
./scripts/verification/verify_system.sh

# 2. 服務管理準備
./scripts/restart_services.sh
./scripts/fix_api_gateway.sh  # 修復 API Gateway

# 3. 基本功能驗證
./scripts/testing/quick_test.sh

# 4. 查詢功能測試
./scripts/queries/simple_query.sh --all

# 5. 完整流程驗證
./scripts/testing/test_full_flow.sh

# 6. Python 測試（在 query-service 目錄）
cd query-service
pytest tests/test_eks_handler.py -v
pytest tests/test_integration.py -v
```

---

## 💫 一鍵快速驗證

### 🟢 **系統環境驗證**

```bash
./scripts/verification/verify_system.sh
```

**檢查項目：**

- ✅ 必要工具（Docker、AWS CLI、jq、curl、Python）
- ✅ Docker 服務狀態
- ✅ 專案目錄結構
- ✅ 腳本執行權限
- ✅ LocalStack 和 EKS Handler 容器
- ✅ AWS 資源（DynamoDB 表、Lambda 函數、API Gateway）

### 🟢 **快速健康檢查**

```bash
./scripts/testing/quick_test.sh
```

**檢查項目：**

- ✅ EKS Handler 健康檢查
- ✅ LocalStack 服務狀態
- ✅ DynamoDB 表存在性
- ✅ 基本查詢 API 功能

### 🟢 **簡化查詢工具**

```bash
# 全自動執行
./scripts/queries/simple_query.sh --all

# 或進入互動模式
./scripts/queries/simple_query.sh
```

**功能包括：**

- ✅ 服務狀態檢查
- ✅ DynamoDB 表統計
- ✅ 用戶查詢測試
- ✅ 行銷活動查詢測試

### 🟢 **完整流程測試**

```bash
./scripts/testing/test_full_flow.sh
```

**CQRS 流程驗證：**

- ✅ 插入命令記錄到 command-records 表
- ✅ DynamoDB Stream 觸發處理
- ✅ 資料同步到 notification-records 表
- ✅ 查詢服務正確回傳數據
- ✅ API Gateway 功能測試

---

## 🐍 Python 測試

### 單元測試

```bash
cd query-service
pytest tests/test_eks_handler.py -v
```

**測試覆蓋：**

- ✅ 健康檢查端點
- ✅ 用戶查詢功能
- ✅ 行銷查詢功能
- ✅ 失敗記錄查詢
- ✅ 錯誤處理機制

### 整合測試

```bash
pytest tests/test_integration.py -v
```

**測試覆蓋：**

- ✅ DynamoDB 整合
- ✅ 端到端工作流
- ✅ CQRS 一致性
- ✅ 效能測試

### 覆蓋率測試

```bash
pytest tests/ --cov=. --cov-report=html
```

---

## 📊 預期正常結果

### ✅ Docker 容器

```txt
NAMES                      STATUS                 PORTS
eks-handler                Up X hours             0.0.0.0:8000->8000/tcp
localstack-query-service   Up X hours (healthy)   127.0.0.1:4566->4566/tcp
```

### ✅ EKS Handler 響應

```json
{
  "status": "healthy",
  "service": "query-service-eks-handler"
}
```

### ✅ DynamoDB 表

```json
{
  "TableNames": ["command-records", "notification-records"]
}
```

### ✅ 查詢 API 響應

```json
{
  "success": true,
  "count": 3,
  "items": [
    {
      "user_id": "test_user_001",
      "transaction_id": "test_xxx",
      "marketing_id": "campaign_2024_test",
      "notification_title": "測試通知",
      "status": "DELIVERED",
      "platform": "IOS"
    }
  ]
}
```

### ✅ Python 測試結果

```txt
單元測試:    ✅ 9/9 通過 (100%)   ⏱️ ~0.6s
整合測試:    ✅ 8/8 通過 (100%)   ⏱️ ~0.5s
```

---

## 🚨 故障排除

### ❌ 容器未運行

```bash
# 檢查容器狀態
docker ps

# 重新啟動服務
./scripts/restart_services.sh

# 等待服務完全啟動
sleep 15
```

### ❌ API Gateway 問題

```bash
# 修復 API Gateway 配置
./scripts/fix_api_gateway.sh

# 驗證修復結果
./scripts/queries/test_query.sh
```

### ❌ DynamoDB 連接失敗

```bash
# 檢查 LocalStack 日誌
docker logs localstack-query-service

# 重啟 LocalStack
docker restart localstack-query-service

# 重新初始化
cd query-service && docker exec -it localstack-query-service /etc/localstack/init/ready.d/setup.sh
```

### ❌ Python 測試依賴問題

```bash
cd query-service
pip install -r requirements.txt
pip install -r tests/requirements-test.txt
```

---

## 🎯 測試成功標準

| 測試項目  | 預期結果           | 驗證方式                     |
| --------- | ------------------ | ---------------------------- |
| 系統環境  | 工具齊全，服務運行 | `verify_system.sh`           |
| 基本功能  | 所有服務正常響應   | `quick_test.sh`              |
| 查詢功能  | 正確返回數據       | `simple_query.sh`            |
| CQRS 流程 | Stream 處理成功    | `test_full_flow.sh`          |
| 單元測試  | 9/9 通過           | `pytest test_eks_handler.py` |
| 整合測試  | 8/8 通過           | `pytest test_integration.py` |

---

## 📝 快速檢查清單

- [ ] 系統驗證通過
- [ ] Docker 容器運行
- [ ] LocalStack 健康檢查通過
- [ ] EKS Handler 響應正常
- [ ] DynamoDB 表存在且有數據
- [ ] 查詢 API 返回正確結果
- [ ] CQRS 流程數據同步成功
- [ ] Python 測試全部通過

**當所有項目都打勾時，您的系統就完全可用了！** 🎉

---

## 🔗 相關文檔

- 📋 [完整測試指南](./TESTING_GUIDE.md)
- 🔍 [查詢工具指南](../guides/MANUAL_QUERY_GUIDE.md)
- 🎯 [最終使用指南](../guides/FINAL_USAGE_GUIDE.md)
- 🏗️ [CQRS 架構說明](../architecture/CQRS_SUCCESS.md)
