# 🛠️ 腳本工具集

這個目錄包含各種自動化腳本，幫助你管理和測試專案。

## 📁 目錄結構

```txt
scripts/
├── 🧪 testing/                    # 測試相關腳本
│   ├── test_coverage.sh           # 覆蓋率測試
│   ├── test_full_flow.sh          # 完整流程測試
│   └── quick_test.sh              # 快速健康檢查
├── 🔍 queries/                    # 查詢工具
├── ✅ verification/               # 驗證腳本
├── 🔧 development/                # 開發工具
├── restart_services.sh            # 服務重啟
└── fix_api_gateway.sh            # API Gateway 修復
```

## 🚀 推薦工作流程

### 🎯 日常開發（使用 Poetry）

```bash
# 1. 安裝依賴
poetry install

# 2. 快速檢查
poetry run pytest tests/ -v

# 3. 覆蓋率檢查
poetry run pytest --cov=query-service/eks_handler --cov-report=html
```

### 🧪 深度測試

```bash
# 1. 系統驗證
./scripts/verification/verify_system.sh

# 2. 重啟服務
./scripts/restart_services.sh

# 3. 完整流程測試
./scripts/testing/test_full_flow.sh

# 4. 覆蓋率測試
./scripts/testing/test_coverage.sh
```

### 🔍 問題排查

```bash
# 1. 快速健康檢查
./scripts/testing/quick_test.sh

# 2. API Gateway 修復
./scripts/fix_api_gateway.sh

# 3. 查詢工具
./scripts/queries/simple_query.sh --all
```

## ⚡ 腳本執行方式

### 從根目錄執行（推薦）

所有腳本現在都支援從專案根目錄執行：

```bash
# 確保在專案根目錄
pwd  # 應該顯示 .../aws-cqrs-test

# 執行任何腳本
./scripts/[category]/[script-name].sh
```

## 📦 Poetry 工作流程

### 基本命令

```bash
# 安裝依賴
poetry install

# 進入虛擬環境
poetry shell

# 執行測試
poetry run pytest

# 運行特定測試
poetry run pytest tests/test_eks_handler.py -v

# 生成覆蓋率報告
poetry run pytest --cov=query-service/eks_handler --cov-report=html
```

### 開發工具

```bash
# 代碼格式化
poetry run black query-service/eks_handler/

# import 排序
poetry run isort query-service/eks_handler/

# 類型檢查
poetry run mypy query-service/eks_handler/

# 預提交檢查
poetry run pre-commit run --all-files
```

## 📊 測試輸出說明

### 成功示例

```txt
======================== test session starts ========================
collected 17 items

tests/test_eks_handler.py::test_health_check PASSED           [ 5%]
tests/test_integration.py::test_query_user PASSED            [10%]
...
======================== 17 passed in 2.23s ========================
```

### 覆蓋率報告

```txt
Name                                Stmts   Miss   Cover   Missing
------------------------------------------------------------------
query-service/eks_handler/main.py      75     17    77%   73, 76-77
------------------------------------------------------------------
TOTAL                                  75     17    77%

Coverage HTML written to htmlcov/index.html
```

## 🔧 故障排除

### 權限問題

```bash
# 給腳本添加執行權限
chmod +x scripts/testing/*.sh
chmod +x scripts/queries/*.sh
```

### Poetry 問題

```bash
# 重新安裝依賴
poetry env remove --all
poetry install

# 檢查虛擬環境
poetry env info

# 更新依賴
poetry update
```

### LocalStack 問題

```bash
# 重啟 LocalStack
cd query-service
docker-compose restart localstack

# 檢查服務狀態
docker-compose ps
```

## 📝 最佳實踐

1. **使用 Poetry** 管理依賴和執行測試
2. **從根目錄執行**腳本
3. **定期執行覆蓋率測試**確保代碼品質
4. **遇到問題時使用快速檢查**腳本診斷

## ✨ 專案特色

### 🔧 依賴管理

- ✅ Poetry 統一依賴管理
- ✅ pyproject.toml 配置
- ✅ 自動化開發工具

### 🧪 測試框架

- ✅ pytest 測試框架
- ✅ 覆蓋率報告
- ✅ 整合測試支援

### 🏗️ 架構設計

- ✅ CQRS 模式實現
- ✅ 六邊形架構
- ✅ 事件驅動同步

現在你的測試工作流程更加統一和高效！
