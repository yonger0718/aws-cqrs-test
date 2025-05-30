# 🔄 根目錄測試遷移總結

本文檔總結了將專案測試配置從 `query-service` 子目錄遷移到根目錄的完整過程。

## 🎯 目標

- 統一從根目錄執行所有測試
- 清理重複的配置文件
- 提供便利的測試腳本
- 保持與現有工作流的兼容性

## 📋 完成的修改

### 1. 📁 新增根目錄配置

#### `pytest.ini` 根目錄配置文件

```ini
[pytest]
# 測試目錄 - 遞迴搜尋所有子目錄的測試
testpaths =
    query-service/tests

# Python 路徑設定 - 確保可以正確導入模組
pythonpath =
    .
    query-service
    query-service/eks_handler

# 覆蓋率配置
[coverage:run]
source =
    query-service/eks_handler
```

#### 智能路徑檢測

測試文件現在支援從任何目錄運行：

```python
# 根據執行目錄調整導入路徑
if "query-service" in current_dir:
    # 從 query-service 目錄執行
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
else:
    # 從根目錄執行
    sys.path.insert(0, os.path.join(project_root, "query-service"))
```

### 2. 🗑️ 清理重複文件

#### 刪除的文件

- ❌ `query-service/pytest.ini`
- ❌ `query-service/.coverage`
- ❌ `query-service/coverage.xml`
- ❌ `query-service/coverage.json`
- ❌ `query-service/htmlcov/`
- ❌ `query-service/.pytest_cache/`
- ❌ `query-service/.gitignore`

#### 統一的 `.gitignore`

合併了所有忽略規則到根目錄：

```gitignore
# LocalStack specific
volume/
query-service/volume/
.localstack/

# Lambda packages
*.zip
lambda-deployment-*.zip

# Coverage reports (all locations)
htmlcov/
coverage.json
```

### 3. 🚀 新增便利腳本

#### `scripts/run_tests.sh` - 統一測試執行腳本

```bash
# 執行所有測試
./scripts/run_tests.sh --all

# 只執行單元測試
./scripts/run_tests.sh --unit

# 只執行整合測試
./scripts/run_tests.sh --integration

# 生成覆蓋率報告
./scripts/run_tests.sh --coverage

# 快速測試（跳過慢速測試）
./scripts/run_tests.sh --fast

# 詳細輸出
./scripts/run_tests.sh --unit --verbose
```

### 4. 🔄 更新現有腳本

#### `scripts/testing/test_coverage.sh`

- ✅ 支援從根目錄運行
- ✅ 使用新的路徑配置
- ✅ 改進錯誤處理

#### `scripts/README.md`

- ✅ 更新使用說明
- ✅ 新增故障排除指南
- ✅ 清理文檔結構

## 🎉 使用方式

### 從根目錄執行（推薦）

```bash
# 確保在專案根目錄
pwd  # 應該顯示 .../aws-cqrs-test

# 使用統一腳本
./scripts/run_tests.sh --all

# 直接使用 pytest
pytest
pytest -v
pytest --cov=query-service/eks_handler

# 使用覆蓋率腳本
./scripts/testing/test_coverage.sh
```

### 舊方式仍可用

```bash
# 從子目錄執行
cd query-service
pytest tests/test_eks_handler.py -v
```

## 📊 測試結果

### 成功驗證

```bash
$ ./scripts/run_tests.sh --all
ℹ️  執行所有測試...
===== 17 passed, 10 warnings in 2.23s =====
✅ 測試執行完成！

$ ./scripts/run_tests.sh --coverage
Coverage HTML written to dir htmlcov
77.33% 覆蓋率
✅ 覆蓋率報告已生成在 htmlcov/ 目錄
```

### 測試摘要

- ✅ **9 個單元測試**全部通過
- ✅ **8 個整合測試**全部通過
- ✅ **77.33% 覆蓋率**達標（>= 70%）
- ✅ **根目錄和子目錄**都可正常運行

## 🔧 修正的問題

### 原問題

1. ❌ Mock 路徑錯誤：`@patch("main.lambda_client")`
2. ❌ Coverage 路徑錯誤：`source = eks-handler`
3. ❌ 重複配置文件
4. ❌ 分散的測試執行方式

### 修正後

1. ✅ 正確的 Mock 路徑：`@patch("eks_handler.main.lambda_client")`
2. ✅ 正確的 Coverage 路徑：`source = query-service/eks_handler`
3. ✅ 統一的配置管理
4. ✅ 便利的測試腳本

## 💡 最佳實踐

### 推薦工作流

1. **日常開發**：`./scripts/run_tests.sh --fast`
2. **完整測試**：`./scripts/run_tests.sh --all`
3. **覆蓋率檢查**：`./scripts/run_tests.sh --coverage`
4. **深度測試**：`./scripts/testing/test_coverage.sh`

### 故障排除

```bash
# 檢查環境
ls pytest.ini  # 確認在根目錄

# 檢查路徑
python -c "import sys; print('\\n'.join(sys.path))"

# 給腳本權限
chmod +x scripts/run_tests.sh
```

## ✨ 優勢

### 統一性

- 🎯 所有命令從根目錄執行
- 🔄 一致的配置管理
- 📊 統一的覆蓋率報告

### 擴展性

- 📁 容易添加其他服務的測試
- 🛠️ 便利的腳本工具
- 🔗 CI/CD 友好

### 兼容性

- ✅ 保持現有工作流
- 🔄 漸進式遷移
- 📚 完整的文檔支援

## 🏁 結論

根目錄測試遷移已成功完成！現在你可以：

- ✅ 從根目錄統一執行所有測試
- ✅ 使用便利腳本簡化測試流程
- ✅ 享受更清潔的專案結構
- ✅ 保持與現有工作流的兼容性

**下一步建議：**

1. 更新 CI/CD 流水線使用新的腳本
2. 更新團隊文檔和工作流程
3. 考慮添加其他服務的測試到根目錄配置
