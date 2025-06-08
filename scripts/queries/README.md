# DynamoDB 查詢工具集

這個目錄包含了用於檢查和測試 DynamoDB 表以及查詢 API 的工具集。

## 🚀 新工具（推薦使用）

### 1. 表檢查工具 - `inspect_tables.sh` / `table_inspector.py`

**功能**: 檢查 DynamoDB 表的完整內容，包括表結構、統計信息和實際數據。

```bash
# 檢查所有表（每表顯示 10 筆記錄）
./scripts/queries/inspect_tables.sh

# 檢查特定表
./scripts/queries/inspect_tables.sh --table command-records

# 檢查特定表並指定顯示記錄數
./scripts/queries/inspect_tables.sh --table notification-records --limit 20

# 顯示幫助
./scripts/queries/inspect_tables.sh --help
```

**特色**:

- ✅ 避免 AWS CLI 相容性問題
- 📊 美觀的表格顯示
- 🔍 詳細的表結構信息
- 📈 項目統計
- 🎨 彩色輸出

### 2. 修復版查詢工具 - `fixed_query.sh` / `fixed_query.py`

**功能**: 全面檢查服務狀態、DynamoDB 表統計和 API 端點測試。

```bash
# 執行所有檢查
./scripts/queries/fixed_query.sh

# 只檢查服務狀態
./scripts/queries/fixed_query.sh --mode services

# 只檢查 DynamoDB 表統計
./scripts/queries/fixed_query.sh --mode dynamodb

# 只測試 API 端點
./scripts/queries/fixed_query.sh --mode api

# 顯示幫助
./scripts/queries/fixed_query.sh --help
```

**檢查項目**:

- 🩺 LocalStack 健康檢查
- 🔧 EKS Handler 服務狀態
- 📊 DynamoDB 表列表和記錄計數
- 🧪 查詢 API 端點測試
  - 健康檢查端點
  - 用戶查詢端點
  - 行銷活動查詢端點
  - 失敗記錄查詢端點

## 📜 舊工具（可能有問題）

### `test_query.sh`

- ⚠️ 存在 AWS CLI 相容性問題
- 📝 可能無法正常執行 API Gateway 查詢

### `simple_query.sh`

- ⚠️ 依賴有問題的 AWS CLI
- 📝 功能相對簡單

## 🛠️ 工具選擇建議

### 查看表內容

```bash
# 推薦：檢查所有表
./scripts/queries/inspect_tables.sh

# 推薦：檢查特定表
./scripts/queries/inspect_tables.sh --table command-records --limit 50
```

### 快速健康檢查

```bash
# 推薦：全面檢查
./scripts/queries/fixed_query.sh

# 推薦：只檢查服務
./scripts/queries/fixed_query.sh --mode services
```

### 詳細 API 測試

```bash
# 推薦：只測試 API
./scripts/queries/fixed_query.sh --mode api
```

## 🔧 環境要求

- Poetry（用於依賴管理）
- Python 3.12+
- 已安裝的依賴：
  - `boto3`
  - `requests`
  - `rich`
  - `click`

## 📋 服務端點

- **LocalStack**: `http://localhost:4566`
- **EKS Handler**: `http://localhost:8000`
- **AWS 區域**: `ap-southeast-1`

## 🚨 故障排除

### AWS CLI 相容性問題

如果遇到 `ImportError: cannot import name 'is_s3express_bucket'` 錯誤：

- 使用新的 Python 工具（`inspect_tables.sh` 或 `fixed_query.sh`）
- 避免直接使用 `aws` 命令行工具

### 連接問題

如果工具顯示連接失敗：

1. 確保 LocalStack 正在運行
2. 確保 EKS Handler 正在運行
3. 檢查端點 URL 是否正確

### 表沒有數據

如果表中沒有數據：

- 這是正常的，表示系統目前沒有記錄
- 可以使用測試數據填充工具添加測試數據

## 📚 進階使用

### 直接使用 Python 工具

```bash
# 使用 Poetry 直接執行 Python 工具
poetry run python scripts/queries/table_inspector.py --help
poetry run python scripts/queries/fixed_query.py --help

# 檢查特定表
poetry run python scripts/queries/table_inspector.py --table command-records --limit 100

# 執行特定檢查
poetry run python scripts/queries/fixed_query.py --mode api
```

### 自定義端點

```bash
# 使用不同的端點
./scripts/queries/inspect_tables.sh --endpoint http://localhost:4567
./scripts/queries/fixed_query.sh --aws-endpoint http://localhost:4567 --eks-endpoint http://localhost:8001
```
