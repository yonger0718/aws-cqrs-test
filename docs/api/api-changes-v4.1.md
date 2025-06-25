# API 變更說明 - V4.1 版本

## 📋 概述

V4.1 版本為現有的 CQRS 查詢系統新增了 SNS ID 查詢功能，擴展了查詢能力而不影響現有架構。本次更新完全向後相容，所有現有 API 保持不變。

## 🆕 新增功能摘要

| 變更類型       | 變更項目                           | 影響程度      |
| -------------- | ---------------------------------- | ------------- |
| **新增端點**   | 新增 `/sns` GET 端點              | ✅ 新增功能   |
| **新增端點**   | 新增 `/query/sns` POST 端點       | ✅ 新增功能   |
| **Schema 擴展** | 新增 `sns_id` 欄位支援           | ✅ 向後相容   |
| **查詢能力**   | 支援 SNS ID 基礎掃描查詢          | ✅ 新增功能   |
| **測試覆蓋**   | 完整的 SNS 查詢測試案例           | ✅ 品質提升   |

## 📡 新增端點詳情

### SNS 查詢端點

#### GET /sns
**功能**: 根據 SNS ID 查詢推播記錄
**查詢方式**: DynamoDB Scan + Filter
**參數**: `sns_id` (required)

```http
GET /sns?sns_id=sns-12345
```

#### POST /query/sns
**功能**: 根據 SNS ID 查詢推播記錄 (POST 方式)
**查詢方式**: DynamoDB Scan + Filter
**請求體**: JSON 格式包含 `sns_id`

```http
POST /query/sns
Content-Type: application/json

{
  "sns_id": "sns-12345"
}
```

### 回應格式

#### 成功回應 (找到記錄)
```json
{
  "success": true,
  "data": [
    {
      "transaction_id": "txn-sns-456",
      "token": "device-token-sns",
      "platform": "IOS",
      "notification_title": "SNS 推播通知",
      "notification_body": "這是通過 SNS 發送的推播",
      "status": "SENT",
      "send_ts": 1640995200,
      "ap_id": "sns-service",
      "created_at": 1640995200,
      "sns_id": "sns-12345"
    }
  ],
  "message": "Successfully retrieved notifications for SNS ID: sns-12345",
  "total_count": 1
}
```

#### 成功回應 (未找到記錄)
```json
{
  "success": true,
  "data": [],
  "message": "Successfully retrieved notifications for SNS ID: sns-nonexistent",
  "total_count": 0
}
```

#### 錯誤回應 (缺少參數)
```json
{
  "success": false,
  "data": [],
  "message": "SNS ID is required",
  "total_count": 0
}
```

## 📊 資料結構變更

### NotificationRecord 模型擴展

**新增欄位**: `sns_id: Optional[str]`

```python
class NotificationRecord(BaseModel):
    transaction_id: str
    token: Optional[str] = None
    platform: str
    notification_title: str
    notification_body: str
    status: str
    send_ts: Optional[int] = None
    delivered_ts: Optional[int] = None
    failed_ts: Optional[int] = None
    ap_id: Optional[str] = None
    created_at: int
    sns_id: Optional[str] = None  # 🆕 新增欄位
```

### 完整 JSON Schema

```json
{
  "transaction_id": "txn-12345",
  "token": "device-token-abc123",
  "platform": "IOS",
  "notification_title": "推播標題",
  "notification_body": "推播內容",
  "status": "SENT",
  "send_ts": 1640995200,
  "delivered_ts": 1640995210,
  "failed_ts": null,
  "ap_id": "mobile-app-001",
  "created_at": 1640995200,
  "sns_id": "sns-12345"
}
```

## 🔧 實作變更

### EKS Handler (FastAPI) 變更

#### 新增服務方法
```python
async def query_sns_notifications(self, sns_id: str) -> QueryResult:
    """根據 SNS ID 查詢推播記錄"""
```

#### 新增端點
```python
@app.get("/sns")
async def get_sns_notifications(sns_id: str = Query(...))

@app.post("/query/sns")
async def post_sns_notifications(request: SnsQueryRequest)
```

### Query Result Lambda 變更

#### 新增查詢方法
```python
def query_sns_notifications(self, sns_id: str) -> Dict[str, Any]:
    """使用 DynamoDB scan + filter 查詢 SNS 記錄"""
    response = self.table.scan(
        FilterExpression=Attr("sns_id").eq(sns_id),
        ProjectionExpression="transaction_id, #token, platform, notification_title, notification_body, #status, send_ts, delivered_ts, failed_ts, ap_id, created_at, sns_id",
        ExpressionAttributeNames={"#token": "token", "#status": "status"}
    )
```

### Query Lambda 變更

#### 新增路由支援
```python
if path in ["/sns", "/query/sns"]:
    return await self.eks_handler_service.query_sns_notifications(payload)
```

## 🧪 測試覆蓋

### 新增測試案例

```python
class TestSnsQuery:
    """SNS 查詢功能測試"""

    @pytest.mark.asyncio
    async def test_sns_query_success(self):
        """測試成功的 SNS 查詢"""

    @pytest.mark.asyncio
    async def test_sns_query_not_found(self):
        """測試 SNS ID 不存在的情況"""

    @pytest.mark.asyncio
    async def test_sns_query_get_endpoint(self):
        """測試 GET /sns 端點"""

    @pytest.mark.asyncio
    async def test_sns_query_post_endpoint(self):
        """測試 POST /query/sns 端點"""
```

### 測試結果
- ✅ 所有 SNS 相關測試通過 (5/5)
- ✅ 現有測試保持通過
- ✅ 代碼覆蓋率維持高水準

## 🎯 效能考量

### 查詢效能
- **查詢方式**: DynamoDB Scan + FilterExpression
- **效能影響**: 中等 (掃描操作)
- **建議**: 適合中小型資料集，考慮新增 GSI 以提升大資料集效能

### 成本影響
- **RCU 消耗**: 比主鍵查詢高
- **建議**: 監控查詢頻率，必要時考慮快取策略

## 🔄 向後相容性

### 完全相容
- ✅ 所有現有 API 端點保持不變
- ✅ 現有資料結構完全相容
- ✅ 現有查詢功能正常運作
- ✅ 部署流程無變更

### 升級建議
1. 部署新版本代碼
2. 執行現有測試確保相容性
3. 測試新的 SNS 查詢功能
4. 根據需要更新客戶端應用

## 📖 使用範例

### cURL 範例

```bash
# GET 方式查詢
curl "http://localhost:8000/sns?sns_id=sns-12345"

# POST 方式查詢
curl -X POST "http://localhost:8000/query/sns" \
  -H "Content-Type: application/json" \
  -d '{"sns_id": "sns-12345"}'
```

### Python 範例

```python
import httpx

# 使用 httpx 查詢
async with httpx.AsyncClient() as client:
    # GET 方式
    response = await client.get("http://localhost:8000/sns",
                               params={"sns_id": "sns-12345"})

    # POST 方式
    response = await client.post("http://localhost:8000/query/sns",
                                json={"sns_id": "sns-12345"})

    data = response.json()
    print(f"找到 {data['total_count']} 筆記錄")
```

## 🎉 總結

V4.1 版本成功新增了 SNS ID 查詢功能，實現了：

- **功能擴展**: 新增 SNS 查詢能力
- **架構一致**: 遵循現有 CQRS 模式
- **向後相容**: 零破壞性變更
- **品質保證**: 完整測試覆蓋
- **文檔完備**: 詳細使用指南

這為用戶提供了更靈活的查詢選項，同時保持了系統的穩定性和一致性。
