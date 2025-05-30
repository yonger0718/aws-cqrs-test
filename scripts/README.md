# 🛠️ 腳本工具集

這個目錄包含各種自動化腳本，幫助你管理和測試專案。

## 📁 目錄結構

```txt
scripts/
├── 🧪 testing/                    # 測試相關腳本
│   ├── test_coverage.sh           # 覆蓋率測試（已更新支援根目錄）
│   ├── test_full_flow.sh          # 完整流程測試
│   └── quick_test.sh              # 快速健康檢查
├── 🔍 queries/                    # 查詢工具
├── ✅ verification/               # 驗證腳本
├── 🔧 development/                # 開發工具
├── 🆕 run_tests.sh                # 統一測試執行腳本（新增）
├── restart_services.sh            # 服務重啟
└── fix_api_gateway.sh            # API Gateway 修復
```

## 🆕 新增功能

### 統一測試執行腳本

現在可以從專案根目錄統一執行所有測試：

```bash
# 在專案根目錄執行
./scripts/run_tests.sh --help

# 常用命令
./scripts/run_tests.sh --all         # 執行所有測試
./scripts/run_tests.sh --unit        # 只執行單元測試
./scripts/run_tests.sh --integration # 只執行整合測試
./scripts/run_tests.sh --coverage    # 生成覆蓋率報告
./scripts/run_tests.sh --fast        # 快速測試（跳過慢速）
```

### 覆蓋率測試腳本（已更新）

`testing/test_coverage.sh` 已更新為支援從根目錄運行：

```bash
# 在專案根目錄執行
./scripts/testing/test_coverage.sh
```

## 🚀 推薦工作流程

### 🎯 日常開發

```bash
# 1. 快速檢查（從根目錄）
./scripts/run_tests.sh --fast --verbose

# 2. 完整測試
./scripts/run_tests.sh --all

# 3. 覆蓋率檢查
./scripts/run_tests.sh --coverage
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

### 舊方式（仍然支援）

你仍然可以進入子目錄執行特定腳本：

```bash
cd query-service
pytest tests/test_eks_handler.py -v
```

## 📊 測試輸出說明

### 成功示例

```txt
🧪 測試執行腳本
ℹ️  執行所有測試...
===== 17 passed, 10 warnings in 2.23s =====
✅ 測試執行完成！
```

### 覆蓋率報告

```txt
Name                                Stmts   Miss   Cover   Missing
------------------------------------------------------------------
query-service/eks_handler/main.py      75     17  77.33%   73, 76-77
------------------------------------------------------------------
TOTAL                                  75     17  77.33%

✅ 覆蓋率 (77%) 符合要求 (>= 70%)
```

## 🔧 故障排除

### 權限問題

```bash
# 給腳本添加執行權限
chmod +x scripts/run_tests.sh
chmod +x scripts/testing/*.sh
```

### 路徑問題

```bash
# 確認在正確目錄
ls pytest.ini  # 應該存在

# 檢查檔案結構
ls -la query-service/
ls -la query-service/tests/
```

### 依賴問題

```bash
# 安裝測試依賴
pip install -r query-service/requirements.txt

# 檢查 Python 路徑
python -c "import sys; print('\\n'.join(sys.path))"
```

## 📝 最佳實踐

1. **始終從根目錄執行**腳本
2. **使用新的統一腳本** `./scripts/run_tests.sh`
3. **定期執行覆蓋率測試**確保代碼品質
4. **遇到問題時使用快速檢查**腳本診斷

## ✨ 更新摘要

### 🆕 新增

- ✅ 統一測試執行腳本 (`run_tests.sh`)
- ✅ 根目錄 pytest 配置
- ✅ 智能路徑檢測和調整

### 🔄 更新

- ✅ 覆蓋率測試腳本支援根目錄執行
- ✅ 清理重複配置文件
- ✅ 統一 .gitignore 規則

### 🗑️ 清理

- ✅ 移除重複的 pytest.ini
- ✅ 移除重複的覆蓋率文件
- ✅ 移除重複的 .gitignore

現在你的測試工作流程更加統一和高效！
