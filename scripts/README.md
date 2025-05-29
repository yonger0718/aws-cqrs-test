# 🔧 專案腳本索引

本目錄包含 AWS Hexagon 通知測試專案的所有腳本工具。

## 📁 目錄結構

### 🧪 [testing/](./testing/) - 測試腳本

- **[run_tests.ps1](./testing/run_tests.ps1)** - 主要測試執行腳本
  - 執行單元測試和整合測試
  - 生成覆蓋率報告
  - 自動安裝依賴
- **[quick_test.ps1](./testing/quick_test.ps1)** - 快速測試腳本
  - 快速健康檢查
  - 基本功能驗證
- **[check_tables.py](./testing/check_tables.py)** - DynamoDB 表檢查工具
  - 檢查表結構
  - 查看樣本數據

### 🔍 [queries/](./queries/) - 查詢腳本

- **[manual_query.ps1](./queries/manual_query.ps1)** - 手動查詢工具
  - 互動式查詢介面
  - 支援多種查詢類型
- **[simple_query.ps1](./queries/simple_query.ps1)** - 簡化查詢工具
  - 單一參數查詢
  - 快速結果展示
- **[query_services.ps1](./queries/query_services.ps1)** - 服務查詢工具
  - 批次查詢功能
  - 進階查詢選項

### ✅ [verification/](./verification/) - 驗證腳本

- **[verify_system.ps1](./verification/verify_system.ps1)** - 系統驗證工具 (PowerShell)
  - 環境檢查
  - 服務狀態驗證
  - 依賴項確認
- **[verify_system.bat](./verification/verify_system.bat)** - 系統驗證工具 (批次檔)
  - 相容於較舊的 Windows 環境
  - 基本環境檢查

### 🛠️ [development/](./development/) - 開發輔助腳本

- **[simulate_writes.py](./development/simulate_writes.py)** - 數據模擬工具
  - 生成測試數據
  - 模擬推播寫入
  - 測試負載生成

## 🚀 使用指南

### 新手快速開始

```powershell
# 1. 系統驗證
.\verification\verify_system.ps1

# 2. 快速測試
.\testing\quick_test.ps1

# 3. 完整測試
.\testing\run_tests.ps1
```

### 查詢操作

```powershell
# 手動查詢
.\queries\manual_query.ps1

# 簡單查詢
.\queries\simple_query.ps1 -UserId "user-001"

# 服務查詢
.\queries\query_services.ps1 -QueryType "user" -Params @{user_id="user-001"}
```

### 開發輔助

```python
# 生成測試數據
python development\simulate_writes.py
```

## 📋 腳本需求

### 系統需求

- **PowerShell 5.1+** (Windows)
- **Python 3.9+** (部分腳本)
- **Docker** (LocalStack 相關功能)

### 權限需求

- 大部分腳本需要管理員權限
- 網路存取權限（存取 LocalStack 和服務）

## 🔧 腳本維護

### 開發規範

- PowerShell 腳本使用 UTF-8 編碼
- Python 腳本遵循 PEP 8 標準
- 所有腳本包含錯誤處理
- 提供詳細的執行日誌

### 測試

- 所有腳本在 Windows 10/11 上測試
- 支援 PowerShell Core (跨平台)
- 定期更新以支援最新的依賴版本

## 🆘 故障排除

### 常見問題

1. **權限錯誤**: 以管理員身份執行 PowerShell
2. **執行策略**: 執行 `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
3. **LocalStack 連接**: 確認 Docker 容器正在運行
4. **Python 依賴**: 確認已安裝 `requirements.txt` 中的套件

### 獲得幫助

- 查看 [../docs/](../docs/) 目錄中的詳細文檔
- 執行腳本時使用 `-Help` 參數查看詳細說明
- 檢查腳本輸出的錯誤訊息和建議
