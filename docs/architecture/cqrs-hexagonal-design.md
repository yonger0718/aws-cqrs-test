# CQRS + 六邊形架構設計文檔

## 概述

本專案實現了完整的 **CQRS (Command Query Responsibility Segregation)** 與 **六邊形架構 (Hexagonal Architecture)** 結合的設計模式，用於構建高性能、可擴展的推播通知查詢系統。

## 📐 架構設計原則

### CQRS 原則

- **讀寫分離**: Command Side 專責寫入，Query Side 專責查詢
- **事件驅動**: 使用 DynamoDB Stream 進行異步資料同步
- **最終一致性**: 查詢端最終會與命令端保持數據一致

### 六邊形架構原則

- **領域核心**: 業務邏輯與外部依賴隔離
- **端口與適配器**: 明確的接口定義和實現分離
- **依賴反轉**: 高層模組不依賴低層模組，都依賴於抽象

## 🏗️ 系統架構圖

```txt
┌─────────────────────────────────────────────────────────────────┐
│                        六邊形架構 + CQRS                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐ │
│  │   Command Side  │───▶│  DynamoDB    │───▶│   Query Side    │ │
│  │   (Write Path)  │    │   Stream     │    │   (Read Path)   │ │
│  └─────────────────┘    └──────────────┘    └─────────────────┘ │
│           │                      │                      │       │
│           ▼                      ▼                      ▼       │
│    ┌─────────────┐      ┌─────────────┐      ┌─────────────┐    │
│    │ command-    │      │   Stream    │      │notification-│    │
│    │ records     │      │ Processor   │      │ records     │    │
│    │ (Write DB)  │      │  Lambda     │      │ (Read DB)   │    │
│    └─────────────┘      └─────────────┘      └─────────────┘    │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                      FastAPI Query Service                     │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Web Layer (API)                         │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │ │
│  │  │ User Query  │  │Marketing    │  │ Failures    │        │ │
│  │  │ Endpoint    │  │Query        │  │ Query       │        │ │
│  │  │             │  │Endpoint     │  │ Endpoint    │        │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘        │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │               Application Layer (Services)                  │ │
│  │  ┌─────────────┐           ┌─────────────┐                 │ │
│  │  │ QueryService│◄─────────▶│ QueryPort   │ (Interface)     │ │
│  │  │             │           │             │                 │ │
│  │  └─────────────┘           └─────────────┘                 │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                 Domain Layer (Models)                      │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │ │
│  │  │Notification │  │ QueryResult │  │ Value       │        │ │
│  │  │Record       │  │             │  │ Objects     │        │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘        │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │            Infrastructure Layer (Adapters)                 │ │
│  │  ┌─────────────┐           ┌─────────────┐                 │ │
│  │  │LambdaAdapter│◄─────────▶│LambdaInvoker│ (Interface)     │ │
│  │  │             │           │Port         │                 │ │
│  │  └─────────────┘           └─────────────┘                 │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🎯 核心組件

### 1. Command Side (寫入端)

**資料表**: `command-records`

- **主鍵**: `transaction_id` (PK) + `created_at` (SK)
- **功能**: 處理所有寫入操作
- **Stream**: 啟用 DynamoDB Stream 觸發同步

### 2. Query Side (查詢端)

**資料表**: `notification-records`

- **主鍵**: `user_id` (PK) + `created_at` (SK)
- **GSI**:
  - `marketing_id-index`: 行銷活動查詢
  - `transaction_id-status-index`: 失敗記錄查詢
- **功能**: 最佳化的查詢操作

### 3. Stream Processor (事件處理器)

**Lambda 函數**: `stream_processor_lambda`

- **觸發**: DynamoDB Stream 事件
- **功能**: 將 Command Side 數據轉換並同步到 Query Side
- **架構**: 六邊形架構設計，包含領域模型和服務層

### 4. FastAPI Query Service (查詢服務)

**EKS Handler**: `eks_handler`

- **架構**: 六邊形架構
- **層次**: Web Layer → Application Layer → Domain Layer → Infrastructure Layer
- **功能**: 提供 RESTful API 查詢接口

## 🔧 六邊形架構實現

### Domain Layer (領域層)

```python
# 領域模型
class NotificationRecord(BaseModel):
    user_id: str
    transaction_id: str
    created_at: int
    marketing_id: Optional[str] = None
    notification_title: str
    status: str
    platform: str
    error_msg: Optional[str] = None

# 查詢結果
class QueryResult(BaseModel):
    success: bool
    data: List[NotificationRecord] = []
    message: str = ""
    total_count: int = 0
```

### Application Layer (應用層)

```python
# 端口接口
class QueryPort(ABC):
    @abstractmethod
    async def query_user_notifications(self, user_id: str) -> QueryResult:
        pass

# 應用服務
class QueryService(QueryPort):
    def __init__(self, lambda_adapter: LambdaInvokerPort):
        self.lambda_adapter = lambda_adapter
```

### Infrastructure Layer (基礎設施層)

```python
# 適配器實現
class LambdaAdapter(LambdaInvokerPort):
    async def invoke_lambda(self, function_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Lambda 調用實現
```

### Web Layer (Web 層)

```python
# FastAPI 路由
@app.post("/query/user", response_model=QueryResult)
async def query_user_notifications(
    request: UserQueryRequest,
    query_service: QueryService = Depends(get_query_service)
):
    return await query_service.query_user_notifications(request.user_id)
```

## 📊 查詢類型

### 1. 用戶查詢

- **端點**: `POST /query/user`
- **用途**: 根據 `user_id` 查詢個人推播記錄
- **索引**: 主表查詢 (`user_id` + `created_at`)

### 2. 行銷活動查詢

- **端點**: `POST /query/marketing`
- **用途**: 根據 `marketing_id` 查詢活動推播統計
- **索引**: GSI `marketing_id-index`

### 3. 失敗記錄查詢

- **端點**: `POST /query/failures`
- **用途**: 根據 `transaction_id` 查詢失敗記錄
- **索引**: GSI `transaction_id-status-index`

## 🔄 資料流程

### 寫入流程

1. 命令寫入 `command-records` 表
2. DynamoDB Stream 觸發 `stream_processor_lambda`
3. Lambda 處理事件並轉換數據格式
4. 同步寫入 `notification-records` 表

### 查詢流程

1. 客戶端調用 FastAPI 端點
2. Web Layer 接收請求並驗證
3. Application Layer 處理業務邏輯
4. Infrastructure Layer 調用 Lambda 查詢
5. 返回結構化的查詢結果

## 💡 設計優勢

### CQRS 優勢

- **性能最佳化**: 讀寫分離，各自最佳化
- **擴展性**: 可獨立擴展讀寫端
- **數據一致性**: 事件驅動確保最終一致性

### 六邊形架構優勢

- **可測試性**: 領域邏輯易於單元測試
- **可維護性**: 清晰的層次分離
- **可擴展性**: 易於添加新的適配器
- **技術無關性**: 核心邏輯不依賴特定技術

## 🛠️ 開發指南

### 新增查詢類型

1. 在 Domain Layer 定義新的查詢模型
2. 在 QueryPort 接口新增方法
3. 在 QueryService 實現業務邏輯
4. 在 Web Layer 新增 API 端點

### 新增外部依賴

1. 定義新的 Port 接口
2. 實現對應的 Adapter
3. 通過依賴注入集成到應用服務

### 測試策略

- **單元測試**: 測試領域模型和應用服務
- **整合測試**: 測試適配器與外部系統集成
- **端到端測試**: 測試完整的 API 流程

## 📝 最佳實踐

1. **領域模型純淨**: 不包含技術細節
2. **接口明確**: 清晰定義端口契約
3. **依賴注入**: 使用 FastAPI 的依賴注入系統
4. **錯誤處理**: 在適配器層處理技術異常
5. **日誌記錄**: 在各層記錄適當的日誌信息
