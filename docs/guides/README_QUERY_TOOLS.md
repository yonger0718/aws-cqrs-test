# 🔍 查詢工具使用指南

## 📋 可用的查詢工具

您現在有完整的工具集可以手動查詢系統中的 SQS、DynamoDB 和其他 AWS 服務：

### 🚀 **互動式 PowerShell 工具** (推薦)

```powershell
cd query-service
.\query_services.ps1
```

**功能包含：**

- 🗂️ DynamoDB 表查詢（查看表內容、統計記錄數）
- 📬 SQS 佇列查詢（檢查佇列內容和訊息）
- 🔧 Lambda 函數查詢（列出函數、測試調用）
- 🚀 EKS Handler API 測試（健康檢查、數據查詢）
- 🔍 完整狀態檢查（服務狀態、數據一致性）
- 📊 數據統計分析（按平台、狀態分析）

### 📖 **完整手動查詢指南**

```bash
# 查看詳細的手動查詢指令
cat MANUAL_QUERY_GUIDE.md
```

---

## 🏃‍♂️ 快速開始

### 步驟 1：啟動互動工具

```powershell
.\query_services.ps1
```

### 步驟 2：選擇查詢類型

```txt
請選擇查詢類型：
1. DynamoDB 表查詢     ← 查看資料庫內容
2. SQS 佇列查詢        ← 檢查訊息佇列
3. Lambda 函數查詢     ← 測試 Lambda 函數
4. EKS Handler API 測試 ← 測試 REST API
5. 完整狀態檢查        ← 檢查所有服務
6. 數據統計分析        ← 數據分析報告
0. 結束程式
```

### 步驟 3：查看結果

每個選項都會顯示詳細的查詢結果，包括：

- 📊 數據內容和統計
- ✅ 狀態檢查結果
- 🔍 詳細的錯誤資訊（如果有）

---

## 🗂️ DynamoDB 查詢示例

### 查看表內容

```powershell
# 選擇選項 1，您會看到：
# 1. 所有 DynamoDB 表列表
# 2. command-records 表內容（前 5 筆）
# 3. notification-records 表內容（前 5 筆）
```

**預期輸出：**

```txt
DynamoDB 表列表:
  - command-records
  - notification-records

command-records 表內容 (前 5 筆):
  交易ID: tx_stream_test_1748496975
  用戶ID: stream_test_user
  建立時間: 1748496975544
  ---

總記錄數: 13
```

---

## 📬 SQS 查詢說明

### 檢查 SQS 佇列

```powershell
# 選擇選項 2
# 注意：您的專案主要使用 DynamoDB Stream，可能沒有 SQS 佇列
```

**可能的結果：**

- ✅ 如果有 SQS：顯示佇列列表和內容
- ⚠️ 如果沒有 SQS：顯示 "沒有找到 SQS 佇列或服務未啟用"

---

## 🔧 Lambda 函數測試

### 查看和測試 Lambda

```powershell
# 選擇選項 3，您會看到：
# 1. 所有 Lambda 函數列表
# 2. stream_processor_lambda 詳細資訊
# 3. 測試 Lambda 函數調用
```

**預期輸出：**

```txt
Lambda 函數列表:
  - 函數名稱: stream_processor_lambda
    運行時: python3.9
    狀態: Active
    ---
  - 函數名稱: query_lambda
    運行時: python3.9
    狀態: Active
```

---

## 🚀 EKS Handler API 測試

### REST API 功能測試

```powershell
# 選擇選項 4，測試：
# 1. 健康檢查端點
# 2. 查詢所有推播記錄
# 3. 查詢特定用戶記錄
# 🆕 4. 查詢 SNS 推播記錄
```

**預期輸出：**

```json
健康檢查結果:
{
  "message": "Query Service is running",
  "service": "query-service",
  "version": "1.0.0"
}

查詢結果:
  成功: True
  記錄數: 9
  第一筆記錄範例: {...}

🆕 SNS 查詢結果:
{
  "success": true,
  "data": [...],
  "message": "Successfully retrieved notifications for SNS ID: sns-12345",
  "total_count": 1
}
```

### 手動 SNS 查詢範例 🆕

```powershell
# GET 方式查詢 SNS
Invoke-RestMethod -Uri "http://localhost:8000/sns?sns_id=sns-12345" -Method GET

# POST 方式查詢 SNS
$snsBody = @{ sns_id = "sns-12345" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/query/sns" -Method POST `
    -ContentType "application/json" -Body $snsBody
```

---

## 🔍 完整狀態檢查

### 一鍵檢查所有服務

```powershell
# 選擇選項 5，檢查：
# 1. Docker 容器狀態
# 2. LocalStack 服務狀態
# 3. 數據統計和一致性
```

**預期輸出：**

```txt
1. Docker 容器狀態
NAMES                     STATUS
eks-handler              Up 2 hours
localstack-query-service Up 2 hours (healthy)

2. LocalStack 服務狀態
  dynamodb : available
  lambda : available
  apigateway : available

3. 數據統計
  命令表記錄數: 13
  查詢表記錄數: 9
  ✅ 數據一致性正常
```

---

## 📊 數據統計分析

### 詳細數據分析

```powershell
# 選擇選項 6，查看：
# 1. 按平台統計推播記錄
# 2. 按狀態統計推播記錄
# 3. 最新 5 筆記錄
```

**預期輸出：**

```txt
按平台統計:
  ANDROID: 5 筆
  IOS: 3 筆
  WINDOWS: 1 筆

按狀態統計:
  SENT: 7 筆
  PENDING: 2 筆

最新 5 筆記錄:
  2025-01-28 10:30:15 - stream_test_user - 測試推播通知
  2025-01-28 10:25:43 - user123 - 行銷活動通知
  ...
```

---

## 🛠️ 常見問題解決

### ❌ 如果工具無法啟動

```powershell
# 檢查 PowerShell 執行原則
Get-ExecutionPolicy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 重新執行
.\query_services.ps1
```

### ❌ 如果容器未運行

```powershell
# 回到專案根目錄
cd ..

# 啟動所有服務
docker compose up -d

# 等待服務啟動
Start-Sleep 10

# 重新執行查詢工具
cd query-service
.\query_services.ps1
```

### ❌ 如果 API 無法連接

```powershell
# 檢查容器狀態
docker ps

# 查看 EKS Handler 日誌
docker logs eks-handler

# 重啟服務
docker restart eks-handler
```

---

## 💡 進階使用提示

### 🔍 **手動 HTTP 查詢**

如果您想要手動發送 HTTP 請求：

```powershell
# DynamoDB 表列表
$headers = @{
    "Content-Type" = "application/x-amz-json-1.0"
    "X-Amz-Target" = "DynamoDB_20120810.ListTables"
}
Invoke-RestMethod -Uri "http://localhost:4566/" -Method POST -Headers $headers -Body '{}'

# EKS Handler 查詢
Invoke-RestMethod -Uri "http://localhost:8000/query/user" -Method GET
```

### 📊 **自定義查詢**

您可以修改 `query_services.ps1` 腳本，添加自己的查詢邏輯。

### 🔄 **定期監控**

設定 Windows 排程執行狀態檢查：

```powershell
# 每 5 分鐘檢查一次系統狀態
# 可以將選項 5 的邏輯包裝成獨立腳本
```

---

## 🎯 總結

您現在有了完整的查詢工具集：

1. **✅ 互動式 PowerShell 工具** - 適合日常使用
2. **✅ 完整的手動查詢指南** - 適合深度查詢
3. **✅ 自動化驗證腳本** - 適合系統檢查

**立即開始使用：**

```powershell
.\query_services.ps1
```

**🎉 享受查詢您的 CQRS 架構數據！**
