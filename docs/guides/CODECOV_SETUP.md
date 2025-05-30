# 📊 Codecov 設置指南

## 🎯 設置 Codecov 服務

本指南將幫助您在專案中設置 Codecov 服務，以追蹤測試覆蓋率並在 README 中顯示 badge。

---

## 📋 前置條件

- ✅ GitHub 倉庫已建立
- ✅ 專案包含測試和覆蓋率配置
- ✅ GitHub Actions CI/CD 已設置

---

## 🚀 Codecov 設置步驟

### **步驟 1: 註冊 Codecov 帳號**

1. 前往 [codecov.io](https://codecov.io)
2. 使用 GitHub 帳號登入
3. 授權 Codecov 存取您的 GitHub 倉庫

### **步驟 2: 添加倉庫到 Codecov**

1. 在 Codecov 控制台中，點擊 "Add new repository"
2. 選擇您的 `aws-cqrs-test` 倉庫
3. 複製 Codecov 提供的 **Upload Token**

### **步驟 3: 設置 GitHub Secrets**

1. 前往您的 GitHub 倉庫
2. 點擊 **Settings** → **Secrets and variables** → **Actions**
3. 點擊 **New repository secret**
4. 添加以下 secret：
   - **Name**: `CODECOV_TOKEN`
   - **Value**: 從 Codecov 複製的 Upload Token

### **步驟 4: 更新 README Badge**

1. 在 Codecov 倉庫頁面中，點擊 **Settings** → **Badge**
2. 複製 Markdown badge 代碼
3. 替換 README.md 中的 badge：

```markdown
[![codecov](https://codecov.io/gh/yonger0718/aws-cqrs-test/branch/main/graph/badge.svg?token=YOUR_ACTUAL_TOKEN)](https://codecov.io/gh/yonger0718/aws-cqrs-test)
```

將 `YOUR_ACTUAL_TOKEN` 替換為您的實際 token。

---

## 🧪 測試 Codecov 整合

### **本地測試覆蓋率**

```bash
# 生成本地覆蓋率報告
./scripts/testing/test_coverage.sh

# 查看 HTML 報告
xdg-open query-service/htmlcov/index.html  # Linux
open query-service/htmlcov/index.html      # macOS
```

### **觸發 CI/CD 流程**

```bash
# 提交更改以觸發 GitHub Actions
git add .
git commit -m "feat: 添加 Codecov 整合"
git push origin main
```

### **驗證 Codecov 上傳**

1. 檢查 GitHub Actions 是否成功運行
2. 查看 Codecov 儀表板中的覆蓋率報告
3. 確認 README badge 顯示正確的覆蓋率百分比

---

## 📊 Codecov 功能

### **覆蓋率報告**

- 📈 **總體覆蓋率**: 整個專案的覆蓋率統計
- 📁 **檔案覆蓋率**: 每個檔案的詳細覆蓋率
- 🔄 **覆蓋率趨勢**: 隨時間變化的覆蓋率圖表
- 🎯 **未覆蓋行數**: 精確顯示未測試的程式碼行

### **Pull Request 整合**

- 📝 **PR 評論**: 自動在 PR 中添加覆蓋率報告
- 📊 **覆蓋率差異**: 顯示 PR 對覆蓋率的影響
- ✅ **品質檢查**: 設置覆蓋率閾值以自動通過/失敗 PR

### **通知設置**

- 📧 **Email 通知**: 覆蓋率下降時發送提醒
- 💬 **Slack 整合**: 將覆蓋率報告發送到 Slack 頻道
- 🔔 **GitHub 狀態檢查**: 在 PR 中顯示覆蓋率狀態

---

## ⚙️ 進階配置

### **自定義覆蓋率閾值**

編輯 `codecov.yml`：

```yaml
coverage:
  status:
    project:
      default:
        target: 80% # 設置專案整體目標
        threshold: 5% # 允許的覆蓋率下降幅度
    patch:
      default:
        target: 70% # 新代碼的覆蓋率目標
```

### **忽略特定檔案**

```yaml
ignore:
  - "docs/"
  - "scripts/"
  - "**/*.md"
  - "*/tests/*"
```

### **多環境覆蓋率**

```yaml
flags:
  unittests:
    paths:
      - query-service/eks_handler/
  integration:
    paths:
      - query-service/tests/
```

---

## 🚨 常見問題

### ❌ Token 無法上傳

**解決方案：**

1. 確認 `CODECOV_TOKEN` secret 已正確設置
2. 檢查 token 是否過期
3. 驗證 GitHub Actions 有正確的權限

### ❌ 覆蓋率檔案未找到

**解決方案：**

1. 確認 `coverage.xml` 檔案已生成
2. 檢查檔案路徑是否正確
3. 驗證 pytest 覆蓋率配置

### ❌ Badge 未顯示

**解決方案：**

1. 檢查 badge URL 是否正確
2. 確認倉庫為 public 或已正確設置權限
3. 等待 Codecov 處理第一次上傳（可能需要幾分鐘）

---

## 📈 覆蓋率改進建議

### **提高覆蓋率的方法**

1. **添加邊界條件測試**

   ```python
   def test_edge_cases():
       # 測試空輸入、null 值、極值等
   ```

2. **測試錯誤處理**

   ```python
   def test_error_handling():
       # 測試異常情況和錯誤處理邏輯
   ```

3. **模擬外部依賴**

   ```python
   @mock.patch('boto3.client')
   def test_with_mock(mock_client):
       # 測試外部 API 呼叫
   ```

### **覆蓋率目標建議**

- 🎯 **新專案**: 70-80%
- 🎯 **成熟專案**: 80-90%
- 🎯 **核心業務邏輯**: 90%+
- 🎯 **工具和腳本**: 60-70%

---

## 🔗 相關資源

- 📚 [Codecov 官方文檔](https://docs.codecov.io)
- 🧪 [測試覆蓋率最佳實踐](https://codecov.io/blog/python-code-coverage-best-practices/)
- 🔧 [Python Coverage 工具](https://coverage.readthedocs.io)
- 📊 [覆蓋率指標解釋](https://codecov.io/blog/what-is-code-coverage/)

---

**🎉 設置完成後，您將擁有專業的覆蓋率追蹤和可視化能力！**
