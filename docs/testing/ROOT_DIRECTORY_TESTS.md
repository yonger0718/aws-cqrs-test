# 🧪 根目錄測試執行指南

本文檔說明如何從專案根目錄執行所有測試，而無需進入 `query-service` 子目錄。

## 📋 配置說明

### 根目錄配置文件

項目根目錄現在包含 `pytest.ini` 配置文件，支援：

- **testpaths**: 自動發現 `query-service/tests` 下的所有測試
- **pythonpath**: 正確的模組導入路徑設定
- **覆蓋率配置**: 指向正確的源碼目錄

### 測試文件調整

測試文件 (`query-service/tests/test_eks_handler.py`) 已調整為支援從任何目錄運行：

```python
# 根據執行目錄調整導入路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
query_service_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(query_service_dir)

# 如果從根目錄執行，添加 query-service 目錄到路徑
if "query-service" in current_dir:
    # 從 query-service 目錄執行
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "eks_handler"))
else:
    # 從根目錄執行
    sys.path.insert(0, os.path.join(project_root, "query-service"))
    sys.path.insert(0, os.path.join(project_root, "query-service", "eks_handler"))
```

## 🚀 使用方式

### 方式一：直接使用 pytest

```bash
# 在專案根目錄執行

# 執行所有測試
pytest

# 執行所有測試（詳細輸出）
pytest -v

# 執行特定測試文件
pytest query-service/tests/test_eks_handler.py -v

# 執行測試並生成覆蓋率報告
pytest --cov=query-service/eks_handler --cov-report=html -v

# 執行特定測試類別
pytest -k "TestUserQuery" -v

# 跳過慢速測試
pytest -m "not slow" -v
```

### 方式二：使用便利腳本

我們提供了 `scripts/run_tests.sh` 腳本來簡化測試執行：

```bash
# 顯示幫助
./scripts/run_tests.sh --help

# 執行所有測試
./scripts/run_tests.sh --all

# 只執行單元測試
./scripts/run_tests.sh --unit

# 只執行整合測試
./scripts/run_tests.sh --integration

# 執行測試並生成覆蓋率報告
./scripts/run_tests.sh --coverage

# 執行快速測試（跳過慢速測試）
./scripts/run_tests.sh --fast

# 組合選項：執行單元測試並生成覆蓋率報告
./scripts/run_tests.sh --unit --coverage --verbose
```

## 📊 測試結果示例

### 從根目錄執行所有測試

```bash
$ pytest -v

=================================== test session starts ===================================
platform linux -- Python 3.12.10, pytest-7.4.3, pluggy-1.6.0
rootdir: /mnt/d/develop/projects/aws-cqrs-test
configfile: pytest.ini
testpaths: query-service/tests
collected 17 items

query-service/tests/test_eks_handler.py::TestHealthCheck::test_health_endpoint PASSED [  5%]
query-service/tests/test_eks_handler.py::TestRootEndpoint::test_root_endpoint PASSED [ 11%]
query-service/tests/test_eks_handler.py::TestUserQuery::test_query_user_success PASSED [ 17%]
query-service/tests/test_eks_handler.py::TestUserQuery::test_query_user_lambda_error PASSED [ 23%]
...
query-service/tests/test_integration.py::TestPerformance::test_concurrent_requests PASSED [100%]

============================= 17 passed, 10 warnings in 2.23s ===============================
```

### 覆蓋率報告

```bash
$ pytest --cov=query-service/eks_handler --cov-report=term

---------- coverage: platform linux, python 3.12.10-final-0 ----------
Name                                Stmts   Miss   Cover   Missing
------------------------------------------------------------------
query-service/eks_handler/main.py      75     17  77.33%   73, 76-77, 108-115, 143-150
------------------------------------------------------------------
TOTAL                                  75     17  77.33%
```

## 🔧 故障排除

### 導入錯誤

如果遇到模組導入錯誤，請確認：

1. 你在專案根目錄（包含 `pytest.ini` 的目錄）
2. Python 路徑設定正確
3. 所有依賴套件已安裝

### 路徑問題

測試文件會自動檢測執行目錄並調整導入路徑。如果仍有問題：

```bash
# 檢查當前目錄
pwd

# 確認文件結構
ls -la query-service/
ls -la query-service/tests/
ls -la query-service/eks_handler/
```

### Mock 問題

確保 mock 路徑正確：

```python
@patch("eks_handler.main.lambda_client")  # ✅ 正確
# 而不是
@patch("main.lambda_client")              # ❌ 錯誤
```

## ✅ 優勢

### 從根目錄運行測試的優勢

1. **統一性**: 所有命令都從根目錄執行
2. **自動發現**: pytest 自動發現所有子目錄的測試
3. **擴展性**: 容易添加其他服務的測試
4. **CI/CD 友好**: 簡化持續整合設定
5. **覆蓋率統一**: 可以生成整個專案的覆蓋率報告

### 仍可從子目錄運行

原有的從 `query-service` 目錄運行測試的方式仍然有效：

```bash
cd query-service
pytest tests/test_eks_handler.py -v
```

## 📝 總結

現在你可以：

- ✅ 從根目錄執行所有測試
- ✅ 使用便利腳本簡化測試執行
- ✅ 生成統一的覆蓋率報告
- ✅ 保持與現有工作流的兼容性

選擇最適合你工作流程的方式！
