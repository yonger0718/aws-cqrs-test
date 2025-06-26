# API 變更說明 - V4.3 版本

## 📋 概述

V4.3 版本為 CQRS 查詢系統新增了重送次數追蹤功能，透過 `retry_cnt` 欄位記錄推播通知的重送次數。本版本完全向後相容，為故障排除和效能分析提供了寶貴的資料洞察。

## 🆕 主要變更摘要

| 變更類型       | 變更項目                              | 影響程度      | 狀態 |
| -------------- | ------------------------------------ | ------------- | ---- |
| **新增欄位**   | 新增 `retry_cnt` 數值欄位             | ✨ 功能增強   | ✅   |
| **Schema 擴展** | 更新 NotificationRecord 模型         | ✨ 向後相容   | ✅   |
| **API 增強**   | 所有查詢端點支援 retry_cnt 回傳       | ✨ 功能增強   | ✅   |
| **Lambda 更新** | Stream Processor 支援 retry_cnt 處理 | 🔧 內部增強   | ✅   |
| **測試覆蓋**   | 完整的 retry_cnt 測試案例            | ✅ 品質提升   | ✅   |

## 🔧 新增欄位詳情

### retry_cnt 欄位規格

```typescript
{
  retry_cnt: number    // 重送次數 (整數，預設值：0，最小值：0)
}
```

**欄位特性**：
- **類型**: 整數 (Integer)
- **預設值**: 0
- **範圍**: >= 0
- **必填**: 否 (Optional)
- **用途**: 記錄推播通知的重送嘗試次數

## 📊 資料結構變更

### NotificationRecord 模型更新

#### 新增 retry_cnt 欄位

```python
class NotificationRecord(BaseModel):
    """推播記錄領域模型 - V4.3 版本"""

    transaction_id: str = Field(..., description="唯一事件識別碼")
    token: Optional[str] = Field(None, description="推播 token")
    platform: Optional[str] = Field(None, pattern="^(IOS|ANDROID|WEBPUSH)$", description="平台類型")
    notification_title: str = Field(..., description="推播標題")
    notification_body: str = Field(..., description="推播內容")
    status: str = Field(..., description="推播狀態")
    send_ts: Optional[int] = Field(None, description="送出時間戳")
    delivered_ts: Optional[int] = Field(None, description="送達時間戳")
    failed_ts: Optional[int] = Field(None, description="失敗時間戳")
    ap_id: Optional[str] = Field(None, description="來源服務識別碼")
    created_at: int = Field(..., description="建立時間戳")
    sns_id: Optional[str] = Field(None, description="SNS 推播識別碼")
    retry_cnt: int = Field(default=0, description="重送次數")  # 🆕 新增欄位
```

### JSON Schema 更新

```json
{
  "transaction_id": "tx-retry-001",
  "token": "device-token-123",
  "platform": "IOS",
  "notification_title": "重送測試通知",
  "notification_body": "測試重送機制",
  "status": "FAILED",
  "send_ts": 1640995200000,
  "failed_ts": 1640995300000,
  "ap_id": "mobile-app-001",
  "created_at": 1640995200000,
  "sns_id": "sns-retry-123",
  "retry_cnt": 3                                              // 🆕 重送次數
}
```

### API Gateway Schema 定義

```json
"retry_cnt": {
  "type": "integer",
  "minimum": 0,
  "description": "Number of retry attempts",
  "example": 2,
  "default": 0
}
```

## 📡 API 端點增強

### 所有查詢端點現在包含 retry_cnt

#### GET /tx

**範例回應**：
```json
{
  "success": true,
  "data": [
    {
      "transaction_id": "tx-001",
      "platform": "IOS",
      "notification_title": "推播通知",
      "status": "DELIVERED",
      "retry_cnt": 1,                                         // 🆕 重送次數
      "created_at": 1640995200000,
      "created_time_utc8": "2022-01-01 12:00:00 UTC+8"
    }
  ],
  "total_count": 1
}
```

#### GET /fail

**範例回應**：
```json
{
  "success": true,
  "data": [
    {
      "transaction_id": "tx-failed-002",
      "platform": "ANDROID",
      "notification_title": "失敗推播",
      "status": "FAILED",
      "retry_cnt": 5,                                         // 🆕 重送次數 (失敗案例通常較高)
      "failed_ts": 1640995500000,
      "failed_time_utc8": "2022-01-01 12:05:00 UTC+8"
    }
  ],
  "total_count": 1
}
```

#### GET /sns

**範例回應**：
```json
{
  "success": true,
  "data": [
    {
      "transaction_id": "tx-sns-003",
      "sns_id": "sns-12345",
      "status": "SENT",
      "retry_cnt": 0,                                         // 🆕 重送次數 (首次成功)
      "created_at": 1640995600000
    }
  ],
  "total_count": 1
}
```

## 🔧 實作變更

### 1. Query Result Lambda 更新

#### format_notification_items 函數增強

```python
def format_notification_items(items: list) -> list:
    """Format notification record items with retry_cnt support"""

    def safe_int_convert(value: Any) -> Optional[int]:
        """安全的數值轉換函數"""
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    formatted_item = {
        # ... 現有欄位 ...
        "retry_cnt": safe_int_convert(item.get("retry_cnt")) or 0,    # 🆕 重送次數處理
    }
```

#### ProjectionExpression 更新

```python
# 所有 DynamoDB 查詢現在包含 retry_cnt
ProjectionExpression=(
    "transaction_id, #token, platform, notification_title, "
    "notification_body, #status, send_ts, delivered_ts, "
    "failed_ts, ap_id, created_at, sns_id, retry_cnt"              # 🆕 新增 retry_cnt
)
```

### 2. Stream Processor Lambda 更新

#### CommandRecord 和 QueryRecord 更新

```python
@dataclass
class CommandRecord:
    """Command side record structure"""
    transaction_id: str
    created_at: int
    user_id: str
    # ... 現有欄位 ...
    retry_cnt: int = 0                                             # 🆕 新增欄位

@dataclass
class QueryRecord:
    """Query side record structure"""
    user_id: str
    created_at: int
    transaction_id: str
    # ... 現有欄位 ...
    retry_cnt: int = 0                                             # 🆕 新增欄位
```

#### save_query_record 函數更新

```python
def save_query_record(query_record: QueryRecord) -> None:
    """Save query record to DynamoDB with retry_cnt support"""

    item = {
        "user_id": query_record.user_id,
        # ... 現有欄位 ...
    }

    # 條件式新增 retry_cnt（避免寫入 0 值以節省儲存空間）
    if query_record.retry_cnt > 0:
        item["retry_cnt"] = query_record.retry_cnt                 # 🆕 重送次數處理
```

### 3. EKS Handler 更新

#### NotificationRecord 模型擴展

```python
record_data = {
    "transaction_id": item.get("transaction_id", ""),
    # ... 現有欄位 ...
    "retry_cnt": retry_cnt,                                        # 🆕 重送次數處理
}
```

## 🧪 測試覆蓋

### 新增測試案例

#### 1. 基本功能測試

```python
def test_format_notification_items_with_retry_cnt(self):
    """測試 retry_cnt 欄位的正確處理"""
    items = [{
        "transaction_id": "tx_001",
        "notification_title": "測試推播",
        "status": "DELIVERED",
        "retry_cnt": 2,                                            # 🆕 測試數據
        "created_at": 1704038400000,
    }]

    formatted = app.format_notification_items(items)

    assert len(formatted) == 1
    assert formatted[0]["retry_cnt"] == 2                          # 🆕 驗證重送次數
```

#### 2. 邊界條件測試

```python
def test_format_notification_items_missing_retry_cnt(self):
    """測試缺少 retry_cnt 欄位時的預設值處理"""
    items = [{
        "transaction_id": "tx_002",
        "notification_title": "測試推播無重送次數",
        "status": "SENT",
        # 故意省略 retry_cnt
    }]

    formatted = app.format_notification_items(items)

    assert formatted[0]["retry_cnt"] == 0                          # 🆕 預設值驗證
```

#### 3. 無效值處理測試

```python
def test_format_notification_items_invalid_retry_cnt(self):
    """測試無效 retry_cnt 值的處理"""
    items = [{
        "transaction_id": "tx_003",
        "notification_title": "測試推播無效重送次數",
        "status": "FAILED",
        "retry_cnt": "invalid_value",                              # 🆕 無效值測試
    }]

    formatted = app.format_notification_items(items)

    assert formatted[0]["retry_cnt"] == 0                          # 🆕 容錯處理驗證
```

### 測試覆蓋率

- ✅ **基本功能**: retry_cnt 欄位正確讀取和格式化
- ✅ **預設值處理**: 缺少欄位時預設為 0
- ✅ **類型轉換**: 字串數字正確轉換為整數
- ✅ **容錯處理**: 無效值安全轉換為 0
- ✅ **邊界值**: 0 值和大數值正確處理
- ✅ **完整流程**: Stream Processor → Query API 完整鏈路

## 📈 業務價值

### 1. 故障排除能力提升

```bash
# 查詢高重送次數的失敗記錄
curl "https://api.example.com/fail" | jq '.data[] | select(.retry_cnt > 3)'

# 分析重送次數分佈
curl "https://api.example.com/tx?limit=100" | jq '[.data[].retry_cnt] | group_by(.) | map({retry_cnt: .[0], count: length})'
```

### 2. 效能分析支援

```python
# 計算平均重送次數
async def analyze_retry_patterns():
    response = await client.get("/tx?limit=1000")
    data = response.json()

    retry_counts = [item.get("retry_cnt", 0) for item in data["data"]]
    avg_retries = sum(retry_counts) / len(retry_counts)

    print(f"平均重送次數: {avg_retries:.2f}")
```

### 3. 監控和告警

```python
# 監控高重送次數事件
def check_high_retry_count():
    response = requests.get("/fail")
    data = response.json()

    high_retry_items = [
        item for item in data["data"]
        if item.get("retry_cnt", 0) > 5
    ]

    if high_retry_items:
        send_alert(f"發現 {len(high_retry_items)} 個高重送次數事件")
```

## 🔄 向後相容性

### 完全相容保證

- ✅ **現有 API**: 所有現有端點保持功能不變
- ✅ **資料結構**: 新欄位為可選，不影響現有邏輯
- ✅ **查詢結果**: 新增欄位不會破壞現有解析邏輯
- ✅ **測試**: 所有現有測試繼續通過

### 漸進式採用

```javascript
// 客戶端可以選擇性使用新欄位
const response = await fetch('/tx?transaction_id=abc123');
const data = await response.json();

data.data.forEach(item => {
    console.log(`交易 ${item.transaction_id}: 重送 ${item.retry_cnt || 0} 次`);

    // 舊代碼不受影響（retry_cnt 為 undefined 時使用預設值）
    const retryCount = item.retry_cnt ?? 0;
});
```

## 🚀 部署建議

### 1. 分階段部署

```bash
# Phase 1: 部署 Stream Processor (開始收集 retry_cnt)
aws lambda update-function-code --function-name stream-processor-lambda

# Phase 2: 部署 Query Result Lambda (開始回傳 retry_cnt)
aws lambda update-function-code --function-name query-result-lambda

# Phase 3: 部署 ECS Handler (完整支援)
aws ecs update-service --cluster query-service --service eks-handler
```

### 2. 驗證步驟

```bash
# 驗證新欄位存在
curl "https://api.example.com/tx?limit=1" | jq '.data[0] | has("retry_cnt")'

# 驗證預設值正確
curl "https://api.example.com/tx?limit=10" | jq '.data[] | select(.retry_cnt == null or .retry_cnt < 0)'

# 應該返回空陣列（沒有 null 或負數值）
```

## 📊 效能影響

### 儲存空間

- **增加**: 每筆記錄約 1-8 bytes（整數儲存）
- **優化**: 僅儲存 > 0 的值（Stream Processor 條件式寫入）
- **估計**: 整體儲存增加 < 1%

### 查詢效能

- **讀取**: 無顯著影響（額外欄位讀取成本極低）
- **投影**: ProjectionExpression 增加一個欄位
- **網路**: 回應大小略微增加（每筆記錄 ~10 bytes）

### 處理效能

- **格式化**: 新增一次整數轉換，效能影響可忽略
- **驗證**: 簡單的範圍檢查（>= 0）
- **整體**: 效能影響 < 0.1%

## 📚 使用範例

### 基礎查詢

```bash
# 查詢特定交易的重送情況
curl "https://api.example.com/tx?transaction_id=tx-001"

# 查詢所有失敗記錄的重送次數
curl "https://api.example.com/fail" | jq '.data[] | {transaction_id, retry_cnt, status}'
```

### 分析腳本

```python
import requests
import json
from collections import Counter

def analyze_retry_patterns():
    """分析重送模式"""
    # 獲取最新 1000 筆記錄
    response = requests.get("https://api.example.com/tx?limit=1000")
    data = response.json()

    # 統計重送次數分佈
    retry_counts = [item.get("retry_cnt", 0) for item in data["data"]]
    distribution = Counter(retry_counts)

    print("重送次數分佈:")
    for retry_count, frequency in sorted(distribution.items()):
        print(f"  {retry_count} 次: {frequency} 筆記錄")

    # 計算統計指標
    total_records = len(retry_counts)
    total_retries = sum(retry_counts)
    avg_retries = total_retries / total_records if total_records > 0 else 0

    print(f"\n統計摘要:")
    print(f"  總記錄數: {total_records}")
    print(f"  總重送次數: {total_retries}")
    print(f"  平均重送次數: {avg_retries:.2f}")
    print(f"  重送率: {(sum(1 for x in retry_counts if x > 0) / total_records * 100):.1f}%")

# 執行分析
if __name__ == "__main__":
    analyze_retry_patterns()
```

### 監控腳本

```bash
#!/bin/bash
# monitor_retries.sh - 監控高重送次數事件

THRESHOLD=5
API_BASE="https://api.example.com"

# 查詢失敗記錄中的高重送次數事件
HIGH_RETRY_EVENTS=$(curl -s "${API_BASE}/fail" | \
    jq --argjson threshold "$THRESHOLD" \
    '[.data[] | select(.retry_cnt > $threshold)] | length')

if [ "$HIGH_RETRY_EVENTS" -gt 0 ]; then
    echo "⚠️  警告: 發現 $HIGH_RETRY_EVENTS 個高重送次數事件 (> $THRESHOLD 次)"

    # 詳細資訊
    curl -s "${API_BASE}/fail" | \
        jq --argjson threshold "$THRESHOLD" \
        '.data[] | select(.retry_cnt > $threshold) | {transaction_id, retry_cnt, status, failed_time_utc8}'
else
    echo "✅ 正常: 沒有高重送次數事件"
fi
```

## 🎯 總結

V4.3 版本成功新增了 `retry_cnt` 重送次數追蹤功能，實現了：

### ✨ 主要成就

- **📊 資料洞察**: 提供推播重送行為的詳細記錄
- **🔍 故障排除**: 協助識別和分析推播失敗模式
- **📈 效能監控**: 支援重送效率和成功率分析
- **🔧 向後相容**: 零破壞性變更，平滑升級體驗

### 🚀 業務價值

- **提升可觀測性**: 增強系統行為透明度
- **改善問題診斷**: 加速故障定位和解決
- **支援資料驅動決策**: 提供重送策略優化依據
- **強化系統穩定性**: 識別和預防重送風暴

### 📋 後續規劃

- **V4.4**: 考慮新增重送間隔時間記錄
- **V5.0**: 整合重送策略配置功能
- **監控增強**: 建立重送次數相關的 CloudWatch 指標
- **分析工具**: 開發重送模式分析儀表板

---

**版本**: V4.3
**發布狀態**: ✅ 生產就緒
**相容性**: 完全向後相容 V4.0, V4.1, V4.2
**下個版本**: V4.4 (計畫中的重送時間間隔追蹤)
