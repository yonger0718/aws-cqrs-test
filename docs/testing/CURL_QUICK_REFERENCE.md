# Curl 快速參考

## ⚡ 一行命令測試

### 設置 URL
```bash
export API_URL="https://your-api-id.execute-api.ap-southeast-1.amazonaws.com"
```

### 健康檢查
```bash
curl -s "$API_URL/health" | jq '.'
```

### 用戶查詢
```bash
curl -s "$API_URL/user?user_id=test_123" | jq '.'
```

### 行銷查詢
```bash
curl -s "$API_URL/marketing?marketing_id=campaign_456" | jq '.'
```

### 失敗查詢
```bash
curl -s "$API_URL/fail?transaction_id=txn_789" | jq '.'
```

---

## 🔍 檢查狀態碼

```bash
# 只看 HTTP 狀態碼
curl -s -o /dev/null -w "%{http_code}\n" "$API_URL/health"

# 狀態碼 + 響應
curl -s -w "HTTP: %{http_code}\n" "$API_URL/health" | jq '.'
```

---

## 📊 簡化輸出

```bash
# 只看成功狀態
curl -s "$API_URL/user?user_id=test_123" | jq '.success'

# 只看記錄數量
curl -s "$API_URL/user?user_id=test_123" | jq '.count'

# 成功狀態 + 記錄數量
curl -s "$API_URL/user?user_id=test_123" | jq '{success, count}'
```

---

## ⚠️ 錯誤測試

```bash
# 缺少參數
curl -s "$API_URL/user" | jq '.'

# 空參數
curl -s "$API_URL/user?user_id=" | jq '.'

# 檢查是否正確返回錯誤
curl -s "$API_URL/user" | jq '.error' | grep -q "Missing" && echo "✅ 錯誤處理正常" || echo "❌ 錯誤處理異常"
```

---

## 🚀 超快驗證

```bash
# 三合一快速檢查
echo "健康檢查:" && curl -s "$API_URL/health" | jq '.status' && \
echo "用戶查詢:" && curl -s "$API_URL/user?user_id=test" | jq '.success' && \
echo "錯誤處理:" && curl -s "$API_URL/user" | jq '.error'
```

---

## 🔧 除錯模式

```bash
# 詳細輸出
curl -v "$API_URL/health"

# 包含時間
curl -s -w "總時間: %{time_total}s\n" "$API_URL/health" | jq '.'

# 檢查 SSL
curl -vvv "$API_URL/health" 2>&1 | grep -i ssl
```
