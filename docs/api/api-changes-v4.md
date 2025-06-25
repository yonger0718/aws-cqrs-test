# API 變更說明 - V4 版本

## 📋 概述

本文檔詳細說明專案 V4 版本中的重大 API 變更，包括完全重構的端點設計、簡化的資料結構以及專注於 transaction_id 的查詢架構。

**🆕 V4.1 版本更新**: 新增 SNS ID 查詢功能

## 🚨 重大變更摘要

| 變更類型       | 變更項目                           | 影響程度      |
| -------------- | ---------------------------------- | ------------- |
| **架構重構**   | 專注於 transaction_id 基礎查詢     | 🔥 破壞性變更 |
| **端點移除**   | 移除 `/query/user` 和 `/query/marketing` | 🔥 破壞性變更 |
| **端點簡化**   | 新增 `/tx` 和 `/fail` GET 端點     | ✅ 新增功能   |
| **🆕 SNS 查詢** | 新增 `/sns` 和 `/query/sns` 端點  | ✅ 新增功能   |
| **資料結構**   | 簡化為 transaction_id 中心設計     | 🔥 破壞性變更 |
| **🆕 Schema**  | 新增 `sns_id` 欄位支援             | ✅ 向後相容   |
| **架構變更**   | EKS → ECS + Internal API Gateway  | 🔧 內部實作   |

## 📡 端點變更詳情

### 1. 完全重構的 API 設計

#### ❌ V3 版本 (已移除)

```http
GET /query/user?user_id=user_001          # 已移除
GET /query/marketing?marketing_id=camp_01  # 已移除
GET /query/failures?transaction_id=tx_002  # 已重命名
```

#### ✅ V4 版本 (新設計)

```http
# 主要查詢端點
GET /tx?transaction_id=tx_001              # 新增：交易推播記錄查詢
POST /query/transaction                    # 交易查詢 POST 方式

# 失敗查詢端點
GET /fail?transaction_id=tx_002            # 簡化：失敗推播記錄查詢
POST /query/fail                          # 失敗查詢 POST 方式

# 🆕 V4.1 SNS 查詢端點
GET /sns?sns_id=sns_12345                 # 新增：SNS 推播記錄查詢
POST /query/sns                           # SNS 查詢 POST 方式

# 健康檢查
GET /health                               # 保持不變
GET /                                     # 根路徑信息
```

### 2. 範例請求

#### 交易查詢

```bash
# GET 方式 (推薦)
curl "https://api.example.com/tx?transaction_id=tx_001"

# POST 方式
curl -X POST "https://api.example.com/query/transaction" \
  -H "Content-Type: application/json" \
  -d '{"transaction_id": "tx_001"}'
```

#### 失敗查詢

```bash
# GET 方式 (推薦)
curl "https://api.example.com/fail?transaction_id=tx_002"

# GET 方式 (查詢所有失敗記錄)
curl "https://api.example.com/fail"

# POST 方式
curl -X POST "https://api.example.com/query/fail" \
  -H "Content-Type: application/json" \
  -d '{"transaction_id": "tx_002"}'
```

#### SNS 查詢 🆕

```bash
# GET 方式 (推薦)
curl "https://api.example.com/sns?sns_id=sns-12345"

# POST 方式
curl -X POST "https://api.example.com/query/sns" \
  -H "Content-Type: application/json" \
  -d '{"sns_id": "sns-12345"}'
```

## 📊 資料結構變更

### 1. 新的領域模型

#### NotificationRecord (統一模型)

```json
{
  "transaction_id": "tx_001",                    // 主鍵：事件唯一識別碼
  "token": "abcd1234efgh5678",                   // 可選：推播 token
  "platform": "IOS",                            // 必填：IOS/ANDROID/WEBPUSH
  "notification_title": "新年特惠活動",           // 必填：推播標題
  "notification_body": "限時優惠，立即查看！",    // 必填：推播內容
  "status": "SENT",                             // 必填：SENT/DELIVERED/FAILED
  "send_ts": 1640995200000,                     // 可選：送出時間戳
  "delivered_ts": 1640995210000,                // 可選：送達時間戳
  "failed_ts": null,                            // 可選：失敗時間戳
  "ap_id": "mobile-app-001",                    // 可選：應用程式識別碼
  "created_at": 1640995200000,                  // 必填：建立時間戳
  "sns_id": "sns-12345"                         // 🆕 可選：SNS 推播識別碼
}
```

### 2. 查詢結果格式

#### 成功回應

```json
{
  "success": true,
  "data": [
    {
      "transaction_id": "tx_001",
      "token": "abcd1234efgh5678",
      "platform": "IOS",
      "notification_title": "新年特惠活動",
      "notification_body": "限時優惠，立即查看！",
      "status": "SENT",
      "send_ts": 1640995200000,
      "delivered_ts": 1640995210000,
      "failed_ts": null,
      "ap_id": "mobile-app-001",
      "created_at": 1640995200000
    }
  ],
  "message": "查詢成功",
  "total_count": 1
}
```

#### 錯誤回應

```json
{
  "success": false,
  "data": [],
  "message": "查詢失敗：transaction_id 不能為空",
  "total_count": 0
}
```

## 🔧 架構變更

### 1. Internal API Gateway 整合

#### V4 架構圖

```txt
┌─────────────────────────────────────────────────────────────────┐
│                    V4 Architecture (ECS)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Client Request                                                 │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐       │
│  │ ECS Handler │────▶│ Internal    │────▶│ Query Result│       │
│  │ (FastAPI)   │     │ API Gateway │     │ Lambda      │       │
│  └─────────────┘     └─────────────┘     └─────────────┘       │
│                             │                     │             │
│                             ▼                     ▼             │
│                    ┌─────────────┐       ┌─────────────┐       │
│                    │ HTTP Route  │       │ DynamoDB    │       │
│                    │ /tx, /fail  │       │ notification│       │
│                    └─────────────┘       │ -records    │       │
│                                          └─────────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2. HTTP 通信協定

```python
# V4: HTTP 通信
async def invoke_query_api(self, query_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    endpoint_map = {
        "transaction": "/tx",
        "fail": "/fail",
    }

    url = f"{self.internal_api_url}{endpoint_map[query_type]}"

    async with httpx.AsyncClient(timeout=self.timeout) as client:
        response = await client.get(url, params=payload, headers=headers)
        return response.json()
```

## 🧪 測試變更

### 1. 更新的測試案例

```python
class TestV4API:
    """V4 API 測試案例"""

    @pytest.mark.asyncio
    async def test_transaction_query_get(self):
        """測試 GET /tx 端點"""
        response = await self.client.get("/tx?transaction_id=tx_001")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) > 0

    @pytest.mark.asyncio
    async def test_fail_query_get(self):
        """測試 GET /fail 端點"""
        response = await self.client.get("/fail?transaction_id=tx_002")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_fail_query_no_params(self):
        """測試 GET /fail 無參數查詢"""
        response = await self.client.get("/fail")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
```

### 2. 端到端測試

```bash
# V4 端到端測試腳本
#!/bin/bash

echo "🧪 V4 API 端到端測試"

# 測試交易查詢
echo "📋 測試交易查詢 GET /tx"
curl -s "http://localhost:8000/tx?transaction_id=tx_001" | jq '.success'

# 測試失敗查詢
echo "📋 測試失敗查詢 GET /fail"
curl -s "http://localhost:8000/fail?transaction_id=tx_002" | jq '.success'

# 測試所有失敗查詢
echo "📋 測試所有失敗查詢 GET /fail (無參數)"
curl -s "http://localhost:8000/fail" | jq '.total_count'
```

## 📋 遷移檢查清單

### 🔥 破壞性變更處理

- [ ] **移除舊端點**: 停止使用 `/query/user` 和 `/query/marketing`
- [ ] **更新端點路徑**: `/query/failures` → `/fail`
- [ ] **重構查詢邏輯**: 改為以 `transaction_id` 為中心
- [ ] **更新資料模型**: 使用新的 `NotificationRecord` 結構

### ✅ 新功能採用

- [ ] **採用 GET 端點**: 使用簡化的 `/tx` 和 `/fail` 端點
- [ ] **處理新回應格式**: 適應統一的 `QueryResult` 結構
- [ ] **整合 HTTP 客戶端**: 使用 `httpx` 進行異步 HTTP 通信
- [ ] **採用新測試案例**: 更新到 V4 測試覆蓋範圍

### 🔧 技術債務處理

- [ ] **更新 API 文檔**: 移除舊端點的文檔說明
- [ ] **更新監控配置**: 調整日誌和指標收集
- [ ] **清理舊程式碼**: 移除不再使用的查詢邏輯
- [ ] **更新部署腳本**: 適應新的 ECS 架構

## 🚀 部署注意事項

### 1. 環境變數配置

```bash
# V4 必需的環境變數
INTERNAL_API_URL=https://internal-api-gateway.amazonaws.com/v1
REQUEST_TIMEOUT=5
ENVIRONMENT=production
```

### 2. 服務健康檢查

```bash
# 檢查 V4 服務狀態
curl http://localhost:8000/health

# 預期回應
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "v4.0.0"
}
```

### 3. 監控和告警

```bash
# 監控新端點使用情況
aws logs filter-log-events \
  --log-group-name /ecs/query-service \
  --filter-pattern "GET /tx"

aws logs filter-log-events \
  --log-group-name /ecs/query-service \
  --filter-pattern "GET /fail"
```

## 📞 支援和文檔

### 📚 相關文檔

1. **[架構設計文檔](../architecture/cqrs-hexagonal-design-v4.md)** - V4 六邊形架構詳解
2. **[部署指南](../deployment/ecs-deployment.md)** - ECS 部署相關問題
3. **[測試指南](../testing/VERIFICATION_GUIDE.md)** - V4 驗證測試流程

### 🔄 API 演進歷程

| 版本 | 主要特性                       | 狀態     |
| ---- | ------------------------------ | -------- |
| V1   | 基礎 CQRS 實現                 | 已廢棄   |
| V2   | 六邊形架構整合                 | 已廢棄   |
| V3   | ECS + Internal API Gateway     | 已廢棄   |
| V4   | Transaction-centric 簡化設計   | 🟢 當前版本 |

### 📅 V4 發布時程

| 階段           | 時間   | 項目                         |
| -------------- | ------ | ---------------------------- |
| **V4.0 Beta**  | Week 1 | 內部測試和 API 驗證          |
| **V4.0 RC**    | Week 2 | 整合測試和效能調校           |
| **V4.0 GA**    | Week 3 | 正式發布和文檔更新           |
| **舊版廢棄**   | Week 4 | 停止支援 V3 及以前版本的端點  |

## 💡 最佳實踐建議

### 1. 錯誤處理

```python
# 建議的錯誤處理模式
try:
    response = await client.get(f"/tx?transaction_id={tx_id}")
    data = response.json()

    if not data["success"]:
        logger.warning(f"查詢失敗: {data['message']}")
        return None

    return data["data"]

except httpx.RequestError as e:
    logger.error(f"請求失敗: {e}")
    raise
```

### 2. 快取策略

```python
# 建議的快取實現
@lru_cache(maxsize=100)
async def get_transaction_notifications(transaction_id: str):
    """帶快取的交易查詢"""
    response = await client.get(f"/tx?transaction_id={transaction_id}")
    return response.json()
```

### 3. 批次查詢

```python
# 批次查詢建議
async def batch_query_transactions(transaction_ids: List[str]):
    """批次查詢多個交易"""
    tasks = []
    for tx_id in transaction_ids:
        task = client.get(f"/tx?transaction_id={tx_id}")
        tasks.append(task)

    responses = await asyncio.gather(*tasks, return_exceptions=True)
    return [r.json() for r in responses if not isinstance(r, Exception)]
```

---

**V4 版本專注於簡化和效能優化，為後續的企業級擴展奠定堅實基礎。** 🚀
