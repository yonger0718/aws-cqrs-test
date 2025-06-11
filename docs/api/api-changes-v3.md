# API 變更說明 - V3 版本 (已廢棄)

> **⚠️ 注意**: 此文檔為 V3 版本的 API 變更說明，已被 V4 版本取代。最新的 API 變更請參考 [api-changes-v4.md](./api-changes-v4.md)

## 📋 概述

本文檔詳細說明專案 V3 版本中的 API 變更，包括端點重命名、資料結構更新以及新增功能。

## 🔄 主要變更摘要

| 變更類型       | 變更項目                          | 影響程度      |
| -------------- | --------------------------------- | ------------- |
| **端點重命名** | `/query/failures` → `/query/fail` | ⚠️ 破壞性變更 |
| **資料結構**   | 新增 `ap_id` 欄位                 | ✅ 向後相容   |
| **架構變更**   | EKS → ECS + Internal API Gateway  | 🔧 內部實作   |
| **通信協定**   | Lambda 直接調用 → HTTP 通信       | 🔧 內部實作   |

## 📡 端點變更詳情

### 1. 失敗查詢端點重命名

#### 變更前

```http
GET /query/failures?transaction_id=tx_002
```

#### 變更後

```http
GET /query/fail?transaction_id=tx_002
```

#### 範例請求

```bash
# 舊版本 (已廢棄)
curl "https://api.example.com/query/failures?transaction_id=tx_002"

# 新版本
curl "https://api.example.com/query/fail?transaction_id=tx_002"
```

#### 移轉指南

```javascript
// 前端 JavaScript 更新範例
// 舊版本
const oldEndpoint = "/query/failures";

// 新版本
const newEndpoint = "/query/fail";

// 更新 API 調用
async function queryFailures(transactionId) {
  const response = await fetch(
    `${newEndpoint}?transaction_id=${transactionId}`
  );
  return response.json();
}
```

### 2. 其他端點 (無變更)

| 端點               | 方法 | 狀態        | 說明             |
| ------------------ | ---- | ----------- | ---------------- |
| `/query/user`      | GET  | ✅ 保持不變 | 查詢用戶推播記錄 |
| `/query/marketing` | GET  | ✅ 保持不變 | 查詢活動推播統計 |
| `/health`          | GET  | ✅ 保持不變 | 健康檢查         |
| `/docs`            | GET  | ✅ 保持不變 | API 文檔         |

## 📊 資料結構變更

### 1. 新增 `ap_id` 欄位

#### Command Records 表

```json
{
  "transaction_id": "tx_001",
  "created_at": 1640995200000,
  "user_id": "user_001",
  "marketing_id": "campaign_2024",
  "ap_id": "mobile-app-001", // 🆕 新增欄位
  "notification_title": "新年特惠活動",
  "status": "SENT",
  "platform": "IOS",
  "device_token": "abcd1234...",
  "payload": "{\"title\":\"新年特惠\",\"body\":\"限時優惠\"}"
}
```

#### Notification Records 表

```json
{
  "user_id": "user_001",
  "created_at": 1640995200000,
  "transaction_id": "tx_001",
  "marketing_id": "campaign_2024",
  "ap_id": "mobile-app-001", // 🆕 新增欄位
  "notification_title": "新年特惠活動",
  "status": "SENT",
  "platform": "IOS"
}
```

#### 欄位說明

- **欄位名稱**: `ap_id`
- **資料類型**: String (S)
- **必填**: 否 (Optional)
- **用途**: 標識服務來源的 Application ID
- **範例值**:
  - `mobile-app-001`
  - `web-portal-001`
  - `mobile-app-002`
  - `admin-dashboard-001`

### 2. API 回應格式

#### 用戶查詢回應

```json
{
  "success": true,
  "data": {
    "user_id": "user_001",
    "notifications": [
      {
        "transaction_id": "tx_001",
        "created_at": 1640995200000,
        "marketing_id": "campaign_2024",
        "ap_id": "mobile-app-001", // 🆕 新增欄位
        "notification_title": "新年特惠活動",
        "status": "SENT",
        "platform": "IOS"
      }
    ],
    "total_count": 1,
    "has_more": false
  },
  "timestamp": 1640995200000
}
```

#### 失敗查詢回應

```json
{
  "success": true,
  "data": {
    "transaction_id": "tx_002",
    "created_at": 1640995200000,
    "user_id": "user_002",
    "marketing_id": "campaign_2024",
    "ap_id": "mobile-app-001", // 🆕 新增欄位
    "notification_title": "新年特惠活動",
    "status": "FAILED",
    "platform": "ANDROID",
    "error_msg": "Invalid device token"
  },
  "timestamp": 1640995200000
}
```

## 🔧 架構變更 (內部實作)

### 1. 通信架構更新

#### 變更前 (EKS)

```txt
API Gateway → Query Lambda → EKS Handler → DynamoDB
```

#### 變更後 (ECS)

```txt
API Gateway → Query Lambda → ECS Handler → Internal API Gateway → Query Result Lambda → DynamoDB
```

### 2. 服務間通信協定

#### 變更前 (Lambda 直接調用)

```python
# 舊版本：直接調用 Lambda
lambda_response = lambda_client.invoke(
    FunctionName='query-result-lambda',
    Payload=json.dumps(request_data)
)
```

#### 變更後 (HTTP 通信)

```python
# 新版本：透過 HTTP 調用
async with httpx.AsyncClient() as client:
    response = await client.post(
        f"{internal_api_url}/query/user",
        json=request_data
    )
```

## 🧪 測試變更

### 1. 單元測試更新

```python
# 測試檔案：test_eks_handler.py → test_ecs_handler.py

class TestQueryService:
    """測試查詢服務 - HTTP 通信架構"""

    @pytest.mark.asyncio
    async def test_query_fail_endpoint(self):
        """測試新的失敗查詢端點"""
        response = await self.client.get(
            "/query/fail",
            params={"transaction_id": "tx_002"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "ap_id" in data["data"]  # 驗證新欄位
```

### 2. 整合測試更新

```bash
# 測試腳本：更新端點路徑
curl -X GET "http://localhost:8000/query/fail?transaction_id=tx_002"

# 驗證回應包含新欄位
jq '.data.ap_id' response.json
```

## 📋 遷移檢查清單

### 前端/客戶端更新

- [ ] 更新失敗查詢端點：`/query/failures` → `/query/fail`
- [ ] 處理新的 `ap_id` 欄位 (可選)
- [ ] 更新 API 文檔和註釋
- [ ] 測試所有查詢功能

### 後端更新

- [ ] 更新路由定義
- [ ] 更新資料模型包含 `ap_id` 欄位
- [ ] 更新測試案例
- [ ] 驗證 HTTP 通信架構

### 資料庫更新

- [ ] Command Records 表新增 `ap_id` 欄位
- [ ] Notification Records 表新增 `ap_id` 欄位
- [ ] 更新測試資料包含 `ap_id`
- [ ] 驗證資料同步功能

## 🔄 向後相容性

### 支援的變更

- ✅ **新增欄位**: `ap_id` 欄位為可選，不影響現有功能
- ✅ **現有端點**: `/query/user` 和 `/query/marketing` 保持不變
- ✅ **回應格式**: 現有欄位格式和結構保持不變

### 破壞性變更

- ⚠️ **端點重命名**: `/query/failures` 不再支援，必須更新為 `/query/fail`

### 移轉期間支援

為了平滑遷移，建議在移轉期間：

1. **雙端點支援** (臨時措施)

```python
# 同時支援舊新端點 (臨時)
@app.get("/query/failures")  # 舊端點 - 標記為廢棄
@app.get("/query/fail")      # 新端點
async def query_failures(transaction_id: str):
    return await query_failure_records(transaction_id)
```

2. **回應中包含遷移提示**

```json
{
  "success": true,
  "data": {...},
  "deprecation_warning": "端點 /query/failures 已廢棄，請使用 /query/fail",
  "timestamp": 1640995200000
}
```

## 📚 範例程式碼

### 1. 前端 JavaScript 更新

```javascript
class QueryService {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  // 更新失敗查詢方法
  async queryFailures(transactionId) {
    const response = await fetch(
      `${this.baseUrl}/query/fail?transaction_id=${transactionId}`
    );

    if (!response.ok) {
      throw new Error(`查詢失敗: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
  }

  // 處理新的 ap_id 欄位
  displayNotification(notification) {
    console.log(`通知來源: ${notification.ap_id || "未知"}`);
    console.log(`標題: ${notification.notification_title}`);
    console.log(`狀態: ${notification.status}`);
  }
}
```

### 2. Python 客戶端更新

```python
import httpx
from typing import Optional, Dict, Any

class QueryServiceClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    async def query_failures(self, transaction_id: str) -> Dict[str, Any]:
        """查詢失敗記錄 - 使用新端點"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/query/fail",
                params={"transaction_id": transaction_id}
            )
            response.raise_for_status()
            return response.json()

    def extract_ap_id(self, notification: Dict[str, Any]) -> Optional[str]:
        """提取 ap_id 欄位"""
        return notification.get("ap_id")
```

### 3. 測試案例更新

```python
import pytest
from fastapi.testclient import TestClient

class TestAPIChanges:

    def test_new_fail_endpoint(self, client: TestClient):
        """測試新的失敗查詢端點"""
        response = client.get("/query/fail?transaction_id=tx_002")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True

        # 驗證包含新欄位
        notification = data["data"]
        assert "ap_id" in notification

    def test_ap_id_field_optional(self, client: TestClient):
        """測試 ap_id 欄位為可選"""
        # 測試沒有 ap_id 的資料也能正常查詢
        response = client.get("/query/user?user_id=legacy_user")
        assert response.status_code == 200

        data = response.json()
        notifications = data["data"]["notifications"]

        # ap_id 可能為 None 或不存在
        for notification in notifications:
            ap_id = notification.get("ap_id")
            if ap_id is not None:
                assert isinstance(ap_id, str)
```

## 🚀 部署注意事項

### 1. 資料庫遷移

```sql
-- 在部署前執行資料庫遷移
-- 注意：這是概念性 SQL，DynamoDB 實際上是 NoSQL

-- 為現有記錄設定預設的 ap_id（可選）
UPDATE command-records
SET ap_id = 'legacy-system'
WHERE ap_id IS NULL;

UPDATE notification-records
SET ap_id = 'legacy-system'
WHERE ap_id IS NULL;
```

### 2. 監控和告警

```bash
# 監控新端點的使用情況
aws logs filter-log-events \
  --log-group-name /ecs/query-service \
  --filter-pattern "POST /query/fail"

# 監控是否有對舊端點的調用
aws logs filter-log-events \
  --log-group-name /ecs/query-service \
  --filter-pattern "GET /query/failures"
```

## 📞 支援和問題回報

如果在遷移過程中遇到問題，請參考：

1. **[ECS 遷移指南](../architecture/ecs-migration-guide.md)** - 了解架構變更詳情
2. **[部署指南](../deployment/ecs-deployment.md)** - 部署相關問題
3. **[測試指南](../testing/VERIFICATION_GUIDE.md)** - 驗證遷移結果

## 📅 時程安排

| 階段           | 時間   | 項目                       |
| -------------- | ------ | -------------------------- |
| **V3.0 Beta**  | Week 1 | 內部測試和驗證             |
| **V3.0 RC**    | Week 2 | 客戶端更新和整合測試       |
| **V3.0 GA**    | Week 3 | 正式發布                   |
| **舊端點廢棄** | Week 6 | 停止支援 `/query/failures` |

請確保在舊端點廢棄前完成所有客戶端的更新。
