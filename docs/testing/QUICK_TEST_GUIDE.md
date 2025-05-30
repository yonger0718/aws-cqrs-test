# 🚀 快速測試指南

## 💫 一鍵驗證工具

您有三種方式可以快速驗證整個系統：

### 1️⃣ **PowerShell 腳本 (推薦)**

```powershell
.\verify_system.ps1
```

### 2️⃣ **Windows Batch 腳本**

```cmd
verify_system.bat
```

### 3️⃣ **Python 測試腳本**

```bash
python test_stream.py
python test_api.py
```

---

## 🔧 手動驗證指令 (選擇性)

### ✅ 快速狀態檢查

```bash
# 檢查容器狀態
docker ps

# 檢查 EKS Handler
curl http://localhost:8000/

# 檢查 DynamoDB 表數量
aws --endpoint-url=http://localhost:4566 dynamodb list-tables
```

### 📊 數據一致性檢查

```bash
# 命令表記錄數
aws --endpoint-url=http://localhost:4566 dynamodb scan --table-name command-records --select COUNT

# 查詢表記錄數
aws --endpoint-url=http://localhost:4566 dynamodb scan --table-name notification-records --select COUNT
```

### 🧪 API 功能測試

```bash
# 查詢所有記錄
curl "http://localhost:8000/query/user"

# 查詢特定用戶
curl "http://localhost:8000/query/user?user_id=stream_test_user"
```

### 🎯 Stream 處理測試

```bash
# 執行完整的 CQRS 測試
python test_stream.py
```

---

## 📋 預期正常結果

### ✅ Docker 容器

```txt
NAMES               STATUS              PORTS
eks-handler         Up X hours          0.0.0.0:8000->8000/tcp
localstack-...      Up X hours          0.0.0.0:4566->4566/tcp
```

### ✅ EKS Handler 響應

```json
{
  "message": "Query Service is running",
  "service": "query-service",
  "version": "1.0.0"
}
```

### ✅ DynamoDB 表

```json
{
  "TableNames": ["command-records", "notification-records"]
}
```

### ✅ API 查詢響應

```json
{
  "success": true,
  "count": X,
  "items": [...]
}
```

### ✅ CQRS Stream 測試

```txt
==============================
命令表記錄數: X
查詢表記錄數: Y (Y <= X)
==============================
✅ 找到同步的記錄: {...}
```

---

## 🚨 故障排除

### ❌ 容器未運行

```bash
# 重新啟動所有服務
docker compose up -d

# 等待服務啟動
sleep 10

# 重新初始化
./infra/localstack/setup.sh
```

### ❌ API 無法連接

```bash
# 檢查 EKS Handler 日誌
docker logs eks-handler

# 重啟 EKS Handler
docker restart eks-handler
```

### ❌ DynamoDB 錯誤

```bash
# 檢查 LocalStack 日誌
docker logs localstack-query-service

# 重啟 LocalStack
docker restart localstack-query-service
```

### ❌ Stream 不同步

```bash
# 檢查 Lambda 函數
aws --endpoint-url=http://localhost:4566 lambda list-functions

# 檢查事件源映射
aws --endpoint-url=http://localhost:4566 lambda list-event-source-mappings
```

---

## 🎯 測試成功標準

| 項目        | 預期結果        | 測試方式                         |
| ----------- | --------------- | -------------------------------- |
| Docker 容器 | 2 個容器運行    | `docker ps`                      |
| EKS Handler | HTTP 200 響應   | `curl localhost:8000`            |
| DynamoDB 表 | 2 個表存在      | `aws dynamodb list-tables`       |
| 數據同步    | Query ≤ Command | 記錄數比較                       |
| API 查詢    | JSON 格式響應   | `curl localhost:8000/query/user` |
| Stream 處理 | 5 秒內同步      | `python test_stream.py`          |

---

## 📄 生成測試報告

所有驗證腳本都會自動生成測試報告：

- **PowerShell**: `verification_report_YYYYMMDD_HHMMSS.md`
- **Python**: 控制台輸出詳細結果
- **手動測試**: 需要自行記錄結果

---

**🎉 測試通過後，您的 CQRS 架構就完全可用了！**
