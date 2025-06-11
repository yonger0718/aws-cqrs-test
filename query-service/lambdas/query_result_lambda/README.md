# Query Result Lambda - GSI 修改說明

## 🚨 當前狀態

由於目前 AWS 環境中的 `notification-records` 表尚未建立 Global Secondary Index (GSI)，我們已將 GSI 查詢功能暫時**註解**掉，並使用 `scan` 操作作為臨時解決方案。

## 📋 修改內容

### 1. 查詢方法修改

#### `query_marketing_notifications`
- **註解掉**: `marketing_id-index` GSI 查詢
- **臨時方案**: 使用 `table.scan()` 搭配 `FilterExpression`

#### `query_failed_notifications`
- **註解掉**: `transaction_id-status-index` GSI 查詢
- **臨時方案**: 使用 `table.scan()` 搭配 `FilterExpression`

### 2. 錯誤處理改善

修復了 PowerTools ServiceError 初始化問題：
- 正確重新拋出 `BadRequestError`
- 使用 `InternalServerError` 替代字典回傳
- 保持一致的錯誤處理模式

## ⚠️ 效能影響

使用 `scan` 操作的影響：
- **延遲增加**: scan 操作需要檢查整個表
- **成本上升**: 消耗更多 RCU (Read Capacity Units)
- **擴展性限制**: 表資料增長時效能下降

## 🎯 建議的 GSI 配置

為了恢復最佳效能，建議在 AWS 環境中建立以下 GSI：

### GSI 1: `marketing_id-index`
```json
{
  "IndexName": "marketing_id-index",
  "KeySchema": [
    {"AttributeName": "marketing_id", "KeyType": "HASH"},
    {"AttributeName": "created_at", "KeyType": "RANGE"}
  ],
  "Projection": {"ProjectionType": "ALL"},
  "ProvisionedThroughput": {
    "ReadCapacityUnits": 5,
    "WriteCapacityUnits": 5
  }
}
```

### GSI 2: `transaction_id-status-index`
```json
{
  "IndexName": "transaction_id-status-index",
  "KeySchema": [
    {"AttributeName": "transaction_id", "KeyType": "HASH"},
    {"AttributeName": "status", "KeyType": "RANGE"}
  ],
  "Projection": {"ProjectionType": "ALL"},
  "ProvisionedThroughput": {
    "ReadCapacityUnits": 5,
    "WriteCapacityUnits": 5
  }
}
```

## 🔄 恢復 GSI 查詢

建立 GSI 後，只需要取消註解程式碼中的對應部分：

```python
# 1. 取消註解 marketing_id 查詢
response = self.table.query(
    IndexName="marketing_id-index",
    KeyConditionExpression=Key("marketing_id").eq(marketing_id),
    ScanIndexForward=False,
)

# 2. 取消註解 transaction_id-status 查詢
response = self.table.query(
    IndexName="transaction_id-status-index",
    KeyConditionExpression=(
        Key("transaction_id").eq(transaction_id) & Key("status").eq("FAILED")
    ),
)
```

## 📊 監控建議

在使用 scan 操作期間，建議監控：
- **RCU 消耗**: 觀察讀取單位消耗量
- **回應時間**: 監控 API 回應延遲
- **錯誤率**: 注意是否有逾時錯誤

## 🚀 部署步驟

1. **測試環境**: 當前修改已可正常運行
2. **效能測試**: 評估 scan 操作的效能影響
3. **GSI 建立**: 根據使用量決定是否建立 GSI
4. **程式碼恢復**: GSI 建立後恢復最佳化查詢
