# 🧪 測試指南

本文件說明如何在 Query Service 專案中執行測試和設置 CI/CD 流程。

## 📋 目錄

- [環境準備](#️-環境準備)
- [執行測試](#-執行測試)
- [CI/CD 流程](#-cicd-流程)
- [Pre-commit Hooks](#-pre-commit-hooks)
- [測試覆蓋率](#-測試覆蓋率)
- [故障排除](#-故障排除)

## 🛠️ 環境準備

### 1. 安裝 Python 3.12

```bash
# Windows (使用 Python 官方安裝程式)
# 或使用 Chocolatey
choco install python --version=3.12.0

# 驗證安裝
python --version
```

### 2. 安裝測試依賴

```powershell
# 進入專案目錄
cd query-service

# 安裝應用程式依賴
pip install -r requirements.txt

# 安裝測試依賴
pip install -r tests/requirements-test.txt
```

### 3. 啟動必要服務

```powershell
# 啟動 LocalStack 和其他服務
docker-compose up -d

# 驗證服務狀態
.\verify_system.ps1
```

## 🚀 執行測試

### 使用自動化腳本（推薦）

```powershell
# 執行所有測試
.\run_tests.ps1

# 只執行單元測試
.\run_tests.ps1 -TestType unit

# 只執行整合測試
.\run_tests.ps1 -TestType integration

# 執行覆蓋率測試
.\run_tests.ps1 -TestType coverage

# 詳細輸出模式
.\run_tests.ps1 -Verbose

# 安裝依賴並執行測試
.\run_tests.ps1 -InstallDeps
```

### 手動執行測試

```bash
# 單元測試
pytest tests/test_eks_handler.py -v

# 整合測試
pytest tests/test_integration.py -v -s

# 所有測試with覆蓋率
pytest tests/ --cov=. --cov-report=html

# 執行特定測試
pytest tests/test_eks_handler.py::TestHealthCheck -v

# 使用標記執行測試
pytest -m unit  # 只執行單元測試
pytest -m integration  # 只執行整合測試
```

## 🔄 CI/CD 流程

### GitHub Actions 工作流程

專案使用 GitHub Actions 進行持續整合和部署：

1. **程式碼品質檢查** (`lint`)

   - Black 格式檢查
   - isort import 排序
   - Flake8 語法檢查
   - MyPy 類型檢查

2. **單元測試** (`unit-tests`)

   - 執行所有單元測試
   - 生成覆蓋率報告
   - 上傳到 Codecov

3. **整合測試** (`integration-tests`)

   - 啟動 LocalStack 服務
   - 建立測試資源
   - 執行端到端測試

4. **安全掃描** (`security-scan`)

   - Trivy 漏洞掃描
   - Safety 依賴檢查

5. **Docker 建置** (`docker-build`)

   - 建置 Docker 映像
   - 推送到 Docker Hub

6. **部署** (`deploy`)
   - 部署到 EKS（需配置）

### 設置 GitHub Secrets

在 GitHub 儲存庫設置以下 Secrets：

```yaml
DOCKER_USERNAME: <你的 Docker Hub 使用者名稱>
DOCKER_PASSWORD: <你的 Docker Hub 密碼>
AWS_ACCESS_KEY_ID: <AWS 存取金鑰>
AWS_SECRET_ACCESS_KEY: <AWS 秘密金鑰>
SLACK_WEBHOOK: <Slack 通知 Webhook URL>（可選）
```

## 🪝 Pre-commit Hooks

### 安裝 pre-commit

```bash
pip install pre-commit

# 安裝 git hooks
pre-commit install

# 手動執行所有 hooks
pre-commit run --all-files
```

### 包含的檢查

- **Black**: Python 程式碼格式化
- **isort**: Import 語句排序
- **Flake8**: 程式碼風格檢查
- **MyPy**: 靜態類型檢查
- **Bandit**: 安全性檢查
- **Hadolint**: Dockerfile 檢查
- **detect-secrets**: 秘密洩漏檢測

## 📊 測試覆蓋率

### 查看覆蓋率報告

```bash
# 生成 HTML 報告
pytest --cov=. --cov-report=html

# 在瀏覽器中開啟報告
start htmlcov/index.html  # Windows
```

### 覆蓋率目標

- 單元測試覆蓋率：> 80%
- 整體覆蓋率：> 70%
- 關鍵路徑覆蓋率：100%

## 🔧 故障排除

### 常見問題

#### 1. ImportError: No module named 'eks_handler'

```bash
# 確保在正確的目錄執行測試
cd query-service
python -m pytest tests/
```

#### 2. LocalStack 連接失敗

```bash
# 檢查 LocalStack 是否運行
docker ps | grep localstack

# 重啟 LocalStack
docker-compose restart localstack
```

#### 3. 測試超時

```bash
# 增加測試超時時間
pytest --timeout=300 tests/
```

#### 4. 覆蓋率不準確

```bash
# 清理快取並重新執行
find . -type d -name __pycache__ -exec rm -r {} +
pytest --cov=. --cov-report=html --no-cov-on-fail
```

## 📝 最佳實踐

1. **寫測試時遵循 AAA 模式**

   - Arrange (準備)
   - Act (執行)
   - Assert (斷言)

2. **使用有意義的測試名稱**

   ```python
   def test_user_query_returns_notifications_for_valid_user_id():
       # 而不是 test_query_1()
   ```

3. **保持測試獨立**

   - 每個測試應該能獨立執行
   - 使用 fixtures 管理測試數據

4. **模擬外部依賴**

   ```python
   @patch('eks_handler.main.lambda_client')
   def test_with_mock(mock_client):
       # 測試邏輯
   ```

5. **定期執行測試**
   - 提交前執行本地測試
   - PR 時自動執行 CI 測試

## 🎯 測試策略

### 測試金字塔

```text
         /\
        /  \    端到端測試 (10%)
       /    \
      /      \  整合測試 (30%)
     /        \
    /          \ 單元測試 (60%)
   /____________\
```

### 測試類型分配

- **單元測試**: 測試單個函數和類別
- **整合測試**: 測試組件間的互動
- **端到端測試**: 測試完整的使用者流程

---

**💡 提示**: 定期更新測試和依賴，確保專案的健康狀態！
