# 🔧 專案腳本索引

本目錄包含 AWS CQRS 通知測試專案的所有腳本工具。

## 📁 目錄結構

### 🧪 [testing/](./testing/) - 測試腳本

- **[quick_test.sh](./testing/quick_test.sh)** - 快速測試腳本 (Shell)
  - 快速健康檢查
  - 基本功能驗證
- **[test_full_flow.sh](./testing/test_full_flow.sh)** - 完整流程測試腳本 (Shell)
  - 測試從命令寫入到查詢的完整流程
  - 驗證 DynamoDB Stream 和 Lambda 處理
  - 測試查詢服務和 API Gateway
- **[check_tables.py](./testing/check_tables.py)** - DynamoDB 表檢查工具
  - 檢查表結構
  - 查看樣本數據

### 🔍 [queries/](./queries/) - 查詢腳本

- **[test_query.sh](./queries/test_query.sh)** - 查詢測試工具 (Shell)
  - 測試 API Gateway 和 EKS Handler 查詢功能
  - 支援多種查詢類型
  - 快速結果展示

### ✅ [verification/](./verification/) - 驗證腳本

- **[verify_system.sh](./verification/verify_system.sh)** - 系統驗證工具 (Shell)
  - 環境檢查
  - 服務狀態驗證
  - 依賴項確認

### 🛠️ [development/](./development/) - 開發輔助腳本

- **[simulate_writes.py](./development/simulate_writes.py)** - 數據模擬工具
  - 生成測試數據
  - 模擬推播寫入
  - 測試負載生成

### 🔄 根目錄腳本

- **[restart_services.sh](./restart_services.sh)** - 服務重啟工具

  - 停止並移除現有容器
  - 清理 volume 目錄
  - 重新啟動服務
  - 執行初始化腳本

- **[fix_api_gateway.sh](./fix_api_gateway.sh)** - API Gateway 修復工具
  - 刪除並重建 API Gateway
  - 配置路由和整合
  - 部署 API
  - 測試 API 端點

## 🚀 使用指南

### 新手快速開始

```bash
# 1. 重啟服務
./scripts/restart_services.sh

# 2. 修復 API Gateway (如果需要)
./scripts/fix_api_gateway.sh

# 3. 快速測試
./scripts/testing/quick_test.sh

# 4. 完整流程測試
./scripts/testing/test_full_flow.sh
```

### 查詢操作

```bash
# 查詢測試
./scripts/queries/test_query.sh
```

### 開發輔助

```bash
# 重啟服務
./scripts/restart_services.sh
```

## 📋 腳本需求

### 系統需求

- **Bash Shell** (Linux/macOS/WSL)
- **Python 3.9+** (部分腳本)
- **Docker** (LocalStack 相關功能)
- **AWS CLI** (與 LocalStack 互動)
- **jq** (JSON 處理)

### 權限需求

- 大部分腳本需要執行權限 (`chmod +x script.sh`)
- 網路存取權限（存取 LocalStack 和服務）
- Docker 存取權限

## 🔧 腳本維護

### 開發規範

- Shell 腳本使用 UTF-8 編碼
- Python 腳本遵循 PEP 8 標準
- 所有腳本包含錯誤處理和顏色輸出
- 提供詳細的執行日誌

### 測試

- 所有腳本在 Linux (包括 WSL) 上測試
- 支援 macOS 和 Linux 環境
- 定期更新以支援最新的依賴版本

## 🆘 故障排除

### 常見問題

1. **權限錯誤**: 確保腳本有執行權限 (`chmod +x script.sh`)
2. **LocalStack 連接**: 確認 Docker 容器正在運行
3. **API Gateway 問題**: 執行 `./scripts/fix_api_gateway.sh`
4. **服務啟動失敗**: 檢查 Docker 日誌和容器狀態

### 獲得幫助

- 查看 [../docs/](../docs/) 目錄中的詳細文檔
- 執行腳本時使用 `-h` 或 `--help` 參數查看詳細說明
- 檢查腳本輸出的錯誤訊息和建議
