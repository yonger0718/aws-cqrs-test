# CI/CD 與 Pre-commit 一致性指南

本文檔說明如何確保 **手動檢查**、**Git commit hooks** 和 **CI/CD 管道** 之間的程式碼品質檢查完全一致。

## 🎯 目標

確保以下三個環節使用相同的工具版本和參數：

1. **手動執行** (`make precommit` 或 `poetry precommit`)
2. **Git commit hook** (`.pre-commit-config.yaml`)
3. **CI/CD 管道** (`.github/workflows/ci.yml`)

## 📋 統一配置

### 工具版本統一

所有環境使用相同的工具版本：

| 工具 | 版本 | 配置位置 |
|------|------|----------|
| Black | ^24.10.0 | `pyproject.toml`, `.pre-commit-config.yaml` |
| isort | ^5.13.2 | `pyproject.toml`, `.pre-commit-config.yaml` |
| Flake8 | ^7.1.1 | `pyproject.toml`, `.pre-commit-config.yaml` |
| MyPy | ^1.13.0 | `pyproject.toml`, `.pre-commit-config.yaml` |
| Bandit | ^1.8.3 | `pyproject.toml`, `.pre-commit-config.yaml` |

### 參數統一

所有檢查使用相同的參數：

```bash
# Black 格式化
black --check --line-length=100 query-service/

# isort 排序
isort --check-only --profile=black --line-length=100 query-service/

# Flake8 檢查
flake8 query-service/ --max-line-length=100 --extend-ignore=E203,W503

# MyPy 類型檢查
mypy query-service/ --ignore-missing-imports --disable-error-code=misc

# Bandit 安全檢查
bandit -ll query-service/ --recursive
```

## 🔧 使用方式

### 1. 手動檢查

```bash
# 使用 Makefile (推薦)
make precommit

# 或使用 Poetry script
poetry run precommit

# 或使用統一腳本
poetry run python scripts.py
```

### 2. Git Commit Hook

```bash
# 安裝 pre-commit hooks
poetry run pre-commit install

# 手動執行 pre-commit
poetry run pre-commit run --all-files
```

### 3. CI/CD 檢查

CI 管道自動執行相同的檢查，無需手動操作。

## 📁 檔案結構

```
.
├── .pre-commit-config.yaml     # Pre-commit hooks 配置
├── pyproject.toml              # Poetry 依賴和工具配置
├── scripts.py                  # 統一檢查腳本
├── Makefile                    # 開發命令介面
└── .github/workflows/ci.yml    # CI/CD 配置
```

## 🔄 配置同步

### 更新工具版本時：

1. **更新 `pyproject.toml`** 中的 dev dependencies
2. **更新 `.pre-commit-config.yaml`** 中的 rev 版本
3. **確認 CI 配置** 使用 Poetry 執行工具
4. **執行測試** 確保所有環境一致

```bash
# 更新依賴
make update
```

### 驗證一致性：

```bash
# 本地檢查
make precommit

# 模擬 CI 檢查
make ci-lint

# Git hook 檢查
poetry run pre-commit run --all-files
```

## 🚀 開發流程

### 初始設置

   ```bash
# 完整環境設置
make dev-setup
   ```

### 日常開發

   ```bash
# 程式碼格式化
make format

# 提交前檢查
make precommit

# 執行測試
make test
```

### 提交程式碼

```bash
# Git commit 會自動觸發 pre-commit hooks
git add .
git commit -m "your message"
```

## 🛠️ 故障排除

### 檢查失敗時：

1. **格式化問題**：執行 `make format` 自動修復
2. **導入順序問題**：執行 `make format` 自動修復
3. **類型檢查問題**：根據錯誤訊息修改程式碼
4. **安全問題**：檢查 Bandit 報告並修復

### 版本不一致時：

   ```bash
# 重新安裝依賴
poetry install

# 更新 pre-commit hooks
poetry run pre-commit autoupdate

# 清理快取
make clean
   ```

## 📝 檢查清單

- [ ] 所有工具版本在三個配置文件中一致
- [ ] 所有參數在三個環境中一致
- [ ] Pre-commit hooks 已安裝
- [ ] 本地檢查通過
- [ ] CI 檢查通過
- [ ] 開發團隊了解統一流程

## 🔗 相關檔案

- [`.pre-commit-config.yaml`](../../.pre-commit-config.yaml)
- [`pyproject.toml`](../../pyproject.toml)
- [`scripts.py`](../../scripts.py)
- [`Makefile`](../../Makefile)
- [CI 配置](../../.github/workflows/ci.yml)

---

💡 **提示**：保持三個環境的配置同步是確保程式碼品質的關鍵。建議定期檢查和更新配置。
