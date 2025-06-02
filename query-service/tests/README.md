# 測試說明文檔

本專案採用分層測試策略，分為單元測試和整合測試兩個層級。

## 📋 測試架構

### 🧪 單元測試 (`@pytest.mark.unit`)

- **目的**: 測試業務邏輯和 API 端點
- **範圍**: FastAPI 應用程式、路由控制器、服務層
- **覆蓋率**: 目標 >75%，當前達到 85%
- **執行速度**: 快速（<5秒）
- **依賴**: 無外部服務，使用 Mock

### 🔗 整合測試 (`@pytest.mark.integration`)

- **目的**: 測試外部服務互動
- **範圍**: DynamoDB、LocalStack、HTTP API
- **覆蓋率**: 不收集（主要測試外部互動）
- **執行速度**: 較慢（需要外部服務）
- **依賴**: LocalStack、DynamoDB

## 🚀 執行測試

### 快速執行單元測試

```bash
# 僅執行單元測試 + 覆蓋率
./scripts/testing/run-unit-tests.sh

# 或使用 pytest 直接執行
poetry run pytest -m unit --cov=query-service/eks_handler
```

### 執行整合測試

```bash
# 需要先啟動 LocalStack
cd query-service && docker compose up -d localstack

# 執行整合測試
./scripts/testing/run-integration-tests.sh

# 或使用 pytest 直接執行
poetry run pytest -m integration
```

### 執行所有測試

```bash
# 自動檢測環境並執行所有可用測試
./scripts/testing/run-all-tests.sh
```

## 📊 覆蓋率報告

### 為什麼只有單元測試收集覆蓋率？

1. **單元測試**：
   - ✅ 直接執行 `eks_handler` 程式碼
   - ✅ 測試業務邏輯分支
   - ✅ 覆蓋率有意義且可追蹤

2. **整合測試**：
   - ❌ 主要測試外部服務 API 呼叫
   - ❌ 不直接執行業務邏輯
   - ❌ 覆蓋率為 0% 是預期結果

### 覆蓋率報告位置

- **HTML 報告**: `htmlcov/index.html`
- **XML 報告**: `coverage.xml` (CI/CD 使用)

## 🏗️ CI/CD 整合

### GitHub Actions 工作流程

1. **單元測試階段**：
   - 執行單元測試
   - 收集覆蓋率
   - 上傳到 Codecov

2. **整合測試階段**：
   - 啟動 LocalStack 服務
   - 建立 DynamoDB 表格
   - 執行整合測試（不收集覆蓋率）

### 本地開發建議

```bash
# 開發時快速驗證
poetry run pytest -m unit -x --ff

# 提交前完整檢查
./scripts/testing/run-all-tests.sh
```

## 🎯 測試標準

### 覆蓋率要求

- **最低要求**: 75%
- **當前達成**: 85%
- **目標**: 維持在 80% 以上

### 測試品質要求

- 每個 API 端點都有對應測試
- 錯誤處理路徑都有測試覆蓋
- 邊界條件和異常情況都有測試

## 🔧 故障排除

### 常見問題

1. **整合測試失敗**：

   ```bash
   # 檢查 LocalStack 是否運行
   curl http://localhost:4566/_localstack/health

   # 重新啟動 LocalStack
   cd query-service && docker compose down && docker compose up -d localstack
   ```

2. **覆蓋率下降**：
   - 檢查是否有新增但未測試的程式碼
   - 執行 `poetry run pytest -m unit --cov=query-service/eks_handler --cov-report=html`
   - 開啟 `htmlcov/index.html` 查看詳細報告

3. **測試執行緩慢**：
   - 優先執行單元測試：`poetry run pytest -m unit`
   - 整合測試僅在需要時執行
