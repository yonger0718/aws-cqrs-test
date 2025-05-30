# 🔍 系統測試驗證指南

## 📋 完整測試驗證流程

這份指南提供了系統性的測試驗證步驟，確保 AWS CQRS 通知系統的完整功能性。

---

## 🎯 推薦驗證順序

### **步驟 1: 環境準備與系統驗證**

```bash
# 檢查系統環境和工具
./scripts/verification/verify_system.sh
```

**預期結果：**

- ✅ 所有必要工具已安裝（Docker、AWS CLI、jq、curl、Python）
- ✅ Docker 服務正在運行
- ✅ 容器狀態健康
- ✅ 腳本有執行權限

### **步驟 2: 服務狀態重置**

```bash
# 重啟所有服務（可選）
./scripts/restart_services.sh

# 修復 API Gateway 配置
./scripts/fix_api_gateway.sh
```

**用途：**

- 🔄 確保所有服務狀態一致
- 🔧 修復可能的配置問題
- 🚀 為測試準備最佳環境

### **步驟 3: 基本功能健康檢查**

```bash
# 快速健康檢查
./scripts/testing/quick_test.sh
```

**驗證項目：**

- ✅ EKS Handler 服務響應 (port 8000)
- ✅ LocalStack 服務可用 (port 4566)
- ✅ DynamoDB 表存在且可訪問
- ✅ 基本 API 端點功能

### **步驟 4: 查詢功能詳細測試**

```bash
# 全自動查詢測試
./scripts/queries/simple_query.sh --all
```

**測試覆蓋：**

- ✅ 服務連接性檢查
- ✅ DynamoDB 表數據統計
- ✅ 用戶查詢 API 測試
- ✅ 行銷活動查詢測試
- ✅ 錯誤處理驗證

### **步驟 5: CQRS 完整流程驗證**

```bash
# 端到端 CQRS 流程測試
./scripts/testing/test_full_flow.sh
```

**CQRS 流程：**

1. ✅ 插入測試命令到 `command-records` 表
2. ✅ DynamoDB Stream 自動觸發
3. ✅ Lambda 函數處理數據轉換
4. ✅ 同步到 `notification-records` 表
5. ✅ 查詢服務返回正確數據
6. ✅ API Gateway 路由功能

### **步驟 6: Python 單元與整合測試**

```bash
cd query-service

# 單元測試
pytest tests/test_eks_handler.py -v

# 整合測試
pytest tests/test_integration.py -v

# 覆蓋率測試（可選）
pytest tests/ --cov=. --cov-report=html
```

**測試範圍：**

- ✅ 所有 API 端點功能
- ✅ DynamoDB 整合測試
- ✅ 錯誤處理和邊界條件
- ✅ 效能和一致性驗證

---

## 📊 驗證成功指標

### 🟢 系統級指標

| 檢查項目        | 成功標準              | 驗證命令              |
| --------------- | --------------------- | --------------------- |
| **容器狀態**    | 2 個容器 Up 狀態      | `docker ps`           |
| **服務響應**    | HTTP 200/健康檢查通過 | `curl localhost:8000` |
| **DynamoDB 表** | 2 個表存在且可訪問    | AWS CLI 查詢          |
| **Lambda 函數** | 函數存在且可執行      | LocalStack API        |

### 🟢 功能級指標

| 測試類型     | 成功標準             | 測試時間 |
| ------------ | -------------------- | -------- |
| **快速測試** | 所有檢查項目通過     | ~30 秒   |
| **查詢測試** | API 返回正確格式數據 | ~45 秒   |
| **流程測試** | CQRS 數據同步成功    | ~60 秒   |
| **單元測試** | 9/9 測試通過         | ~5 秒    |
| **整合測試** | 8/8 測試通過         | ~8 秒    |

### 🟢 數據級指標

```bash
# 預期數據狀態
command-records:      ≥ 3 筆記錄
notification-records: ≥ 3 筆記錄
查詢 API 響應:        JSON 格式，包含 success、count、items
```

---

## 🚨 故障排除指南

### ❌ 環境問題

**症狀：** 工具未安裝或版本不對

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install docker.io awscli jq curl python3 python3-pip

# 檢查版本
docker --version
aws --version
python3 --version
```

### ❌ 容器問題

**症狀：** 容器未運行或不健康

```bash
# 檢查容器狀態
docker ps -a

# 查看容器日誌
docker logs eks-handler
docker logs localstack-query-service

# 重啟問題容器
docker restart eks-handler
docker restart localstack-query-service
```

### ❌ 連接問題

**症狀：** API 無法訪問

```bash
# 檢查端口占用
netstat -tlnp | grep -E "(8000|4566)"

# 測試連接
curl -v http://localhost:8000/health
curl -v http://localhost:4566/health

# 檢查防火牆
sudo ufw status
```

### ❌ 數據問題

**症狀：** DynamoDB 表不存在或數據不同步

```bash
# 重新初始化
cd query-service
docker exec -it localstack-query-service /etc/localstack/init/ready.d/setup.sh

# 檢查表狀態
aws --endpoint-url=http://localhost:4566 dynamodb list-tables
aws --endpoint-url=http://localhost:4566 dynamodb describe-table --table-name command-records
```

### ❌ Python 依賴問題

**症狀：** 測試模組無法導入

```bash
cd query-service
pip install -r requirements.txt
pip install -r tests/requirements-test.txt

# 檢查安裝
pip list | grep -E "(pytest|boto3|fastapi)"
```

---

## 🎯 驗證檢查清單

### 🔍 **逐步驗證清單**

- [ ] **環境驗證** - `verify_system.sh` 通過
- [ ] **服務重啟** - `restart_services.sh` 完成
- [ ] **API 修復** - `fix_api_gateway.sh` 成功
- [ ] **健康檢查** - `quick_test.sh` 全部項目通過
- [ ] **查詢測試** - `simple_query.sh --all` 成功
- [ ] **流程測試** - `test_full_flow.sh` CQRS 同步成功
- [ ] **單元測試** - `pytest test_eks_handler.py` 9/9 通過
- [ ] **整合測試** - `pytest test_integration.py` 8/8 通過

### 🎉 **完成狀態**

當所有項目都勾選時：

- ✅ 您的 AWS CQRS 通知系統完全正常運行
- ✅ 所有核心功能都經過驗證
- ✅ 系統準備好接受實際工作負載
- ✅ 可以開始實際的開發和部署工作

---

## 📈 效能基準

### ⚡ 執行時間基準

```bash
系統驗證:     ~15-30秒
快速測試:     ~30-45秒
查詢測試:     ~45-60秒
流程測試:     ~60-90秒
Python 測試:  ~10-15秒
總驗證時間:   ~3-4分鐘
```

### 📊 資源使用基準

```bash
容器記憶體使用: <1GB
CPU 使用率:     <50%
磁碟空間:       <2GB
網路延遲:       <100ms (本地)
```

---

## 🔗 相關文檔

- 🚀 [快速測試指南](./QUICK_TEST_GUIDE.md) - 簡化版測試流程
- 📋 [完整測試指南](./TESTING_GUIDE.md) - 詳細測試說明
- 🔧 [腳本工具索引](../../scripts/README.md) - 所有腳本說明
- 🎯 [最終使用指南](../guides/FINAL_USAGE_GUIDE.md) - 完整系統使用

**立即開始驗證您的系統：**

```bash
# 開始完整驗證流程
./scripts/verification/verify_system.sh
```

> **💡 提示：** 建議在新環境或重大更改後執行完整驗證流程，確保系統穩定性。
