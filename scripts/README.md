# Scripts 目錄

本目錄包含專案所需的各種腳本和工具，按功能分類組織。

## 📁 目錄結構

```txt
scripts/
├── ci-cd/              # CI/CD 相關腳本
├── deployment/         # 部署相關腳本
├── development/        # 開發工具腳本
├── infrastructure/     # 基礎設施管理腳本
├── testing/           # 測試相關腳本
├── queries/           # 查詢和資料操作腳本
└── verification/      # 驗證和檢查腳本
```

## 🚀 CI/CD 腳本 (`ci-cd/`)

### `simple_test.sh`
快速測試腳本，用於基本功能驗證
```bash
./scripts/ci-cd/simple_test.sh
```

### `check_consistency.py`
檢查 CI 和 pre-commit 配置一致性
```bash
python scripts/ci-cd/check_consistency.py
```

## 🚀 部署腳本 (`deployment/`)

### `cloudshell_quick_start.sh`
Google Cloud Shell 快速啟動腳本
```bash
./scripts/deployment/cloudshell_quick_start.sh
```

### `deploy_api_gateway_proxy.sh`
部署 API Gateway 代理設定
```bash
./scripts/deployment/deploy_api_gateway_proxy.sh
```

### `restart_services.sh`
重啟服務腳本
```bash
./scripts/deployment/restart_services.sh
```

## 🛠️ 開發腳本 (`development/`)

### `setup_env.sh`
設定開發環境
```bash
./scripts/development/setup_env.sh
```

### `simulate_writes.py`
模擬寫入操作用於測試
```bash
python scripts/development/simulate_writes.py
```

## 🏗️ 基礎設施腳本 (`infrastructure/`)

### `fix_api_gateway.sh`
修復 API Gateway 配置問題
```bash
./scripts/infrastructure/fix_api_gateway.sh
```

### `fix_scripts.sh`
修復各種腳本問題
```bash
./scripts/infrastructure/fix_scripts.sh
```

## 🧪 測試腳本 (`testing/`)

### 完整測試套件
```bash
./scripts/testing/run-all-tests.sh        # 執行所有測試
./scripts/testing/run-unit-tests.sh       # 僅執行單元測試
./scripts/testing/run-integration-tests.sh # 僅執行整合測試
```

### 測試覆蓋率
```bash
./scripts/testing/test_coverage.sh        # 生成測試覆蓋率報告
```

### 資料操作
```bash
python scripts/testing/populate_test_data.py  # 填充測試資料
```

### 完整流程測試
```bash
./scripts/testing/test_full_flow.sh       # 完整流程測試
./scripts/testing/quick_test.sh           # 快速測試
```

## ✅ 驗證腳本 (`verification/`)

驗證系統各部分功能是否正常運作。

## 🔍 查詢腳本 (`queries/`)

各種資料查詢和操作腳本。

## 📋 使用指南

### 腳本執行權限
確保腳本有執行權限：
```bash
chmod +x scripts/**/*.sh
```

### Poetry 環境
部分 Python 腳本需要在 Poetry 環境中執行：
```bash
poetry run python scripts/development/simulate_writes.py
```

### 環境變數
部分腳本可能需要特定環境變數，請參考各腳本內部註釋。

## 🔧 維護注意事項

1. **路徑更新**: 移動腳本後請確保所有引用路徑都已更新
2. **權限管理**: 新增腳本時記得設定適當的執行權限
3. **文檔同步**: 修改腳本功能時請同步更新此文檔
4. **版本控制**: 重要變更請記錄在 Git commit 中

## 📚 相關文檔

- [開發工作流程](../docs/development/)
- [部署指南](../docs/deployment/)
- [測試指南](../docs/testing/)
- [CI/CD 配置](../.github/workflows/)
