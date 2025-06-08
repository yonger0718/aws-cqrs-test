# Pre-commit 和 CI 配置一致性文檔

## 概述

本文檔說明了項目中 pre-commit 和 CI 配置的一致性改進，確保本地開發環境和持續集成環境使用相同的代碼質量檢查標準。

## 修復的問題

### 1. Pre-commit 錯誤修復

#### Flake8 行長度問題

- **問題**: `query-service/eks_handler/main.py:150` 行長度超過 100 字符
- **解決方案**: 將過長的 AWS Lambda ARN 字符串分割為多行

```python
# 修復前
function_name_to_invoke = f"arn:aws:lambda:ap-southeast-1:000000000000:function:query-service-{function_name}"  # noqa: E501

# 修復後
function_name_to_invoke = (
    f"arn:aws:lambda:ap-southeast-1:000000000000:function:query-service-"
    f"{function_name}"
)
```

#### Detect-secrets 配置問題

- **問題**: `.secrets.baseline` 文件未被暫存，導致 detect-secrets 檢查失敗
- **解決方案**: 將 `.secrets.baseline` 添加到 Git 暫存區

### 2. 配置一致性改進

#### Pre-commit 配置優化

- 為 Python 相關工具添加文件過濾規則，只檢查 `query-service/` 目錄下的 Python 文件
- 確保所有工具使用相同的參數配置

#### CI 配置同步

- 更新 `.github/workflows/ci.yml` 中的 Flake8 和 MyPy 參數，與 pre-commit 保持一致
- 移除不必要的排除參數，使用項目標準配置

## 配置標準

### 代碼格式化標準

- **行長度**: 100 字符（所有工具統一）
- **Python 版本**: 3.12
- **格式化工具**: Black + isort

### 質量檢查工具配置

#### Black

```yaml
args: ["--line-length=100"]
files: ^query-service/.*\.py$
```

#### isort

```yaml
args: ["--profile=black", "--line-length=100"]
files: ^query-service/.*\.py$
```

#### Flake8

```yaml
args: ["--max-line-length=100", "--extend-ignore=E203,W503"]
files: ^query-service/.*\.py$
```

#### MyPy

```yaml
args: ["--ignore-missing-imports", "--disable-error-code=misc"]
files: ^query-service/.*\.py$
```

#### Bandit

```yaml
args: ["-ll"]
files: ^query-service/.*\.py$
```

## 一致性檢查工具

創建了 `scripts/check_consistency.py` 腳本來自動檢查 pre-commit 和 CI 配置的一致性：

```bash
python scripts/check_consistency.py
```

該腳本會檢查：

- Black 行長度配置
- isort 行長度配置
- Flake8 最大行長度配置
- MyPy 參數配置

## 最佳實踐

### 開發流程

1. 修改代碼後運行 `pre-commit run --all-files`
2. 確保所有檢查通過再提交
3. CI 會運行相同的檢查確保一致性

### 配置維護

1. 任何工具配置變更都應同時更新 pre-commit 和 CI 配置
2. 定期運行一致性檢查腳本
3. 新增工具時確保遵循統一的配置標準

## 驗證結果

### Pre-commit 檢查結果

```
✅ black....................................................................Passed
✅ isort....................................................................Passed
✅ flake8...................................................................Passed
✅ mypy.....................................................................Passed
✅ bandit...................................................................Passed
✅ check yaml...............................................................Passed
✅ check json...............................................................Passed
✅ check toml...............................................................Passed
✅ fix end of files.........................................................Passed
✅ trim trailing whitespace.................................................Passed
✅ check for added large files..............................................Passed
✅ check for merge conflicts................................................Passed
✅ markdownlint.............................................................Passed
✅ Lint Dockerfiles.........................................................Passed
✅ Detect secrets...........................................................Passed
```

### 測試結果

```
============================= 66 passed, 11 skipped in 2.90s ==============================
```

### 一致性檢查結果

```
✅ Black line-length 配置一致
✅ isort line-length 配置一致
✅ flake8 max-line-length 配置一致
✅ MyPy 參數配置一致

✅ 所有配置檢查通過！pre-commit 和 CI 配置一致
```

## 總結

通過這些改進，我們實現了：

1. **完全一致的代碼質量標準**: pre-commit 和 CI 使用完全相同的工具配置
2. **自動化檢查**: 提供腳本自動驗證配置一致性
3. **清晰的文檔**: 記錄所有配置標準和最佳實踐
4. **零錯誤狀態**: 所有代碼質量檢查和測試都通過

這確保了無論是在本地開發還是 CI 環境中，代碼都遵循相同的質量標準，提高了項目的整體代碼質量和一致性。
