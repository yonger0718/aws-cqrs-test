# CQRS + 六邊形架構設計文檔 - V4 版本

## 概述

本專案 V4 版本實現了重新設計的 **CQRS (Command Query Responsibility Segregation)** 與 **六邊形架構 (Hexagonal Architecture)** 結合，專注於 `transaction_id` 為中心的簡化查詢系統，用於構建高性能、可維護的推播通知查詢服務。

## 📐 V4 設計原則

### CQRS 簡化原則

- **專注讀取**: Query Side 專門處理以 `transaction_id` 為核心的查詢
- **事件驅動**: 維持 DynamoDB Stream 進行異步資料同步
- **最終一致性**: 查詢端與命令端保持數據一致性
- **簡化模型**: 統一的 `NotificationRecord` 領域模型

### 六邊形架構精簡化

- **核心領域**: 簡化的業務邏輯，專注於通知記錄查詢
- **清晰端口**: 明確的 `QueryPort` 和 `InternalAPIInvokerPort` 介面
- **依賴反轉**: Internal API Gateway 適配器實現
- **可測試性**: Mock 友好的依賴注入設計

## 🏗️ V4 系統架構圖

```txt
┌─────────────────────────────────────────────────────────────────┐
│                   V4 六邊形架構 + CQRS                          │
│                  (Transaction-centric Design)                  │
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
│              V4 ECS FastAPI Query Service                      │
│                     (六邊形架構)                                │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Web Layer (FastAPI)                     │ │
│  │                                                             │ │
│  │  ┌─────────────┐              ┌─────────────┐              │ │
│  │  │ GET /tx     │              │ GET /fail   │              │ │
│  │  │ POST /query/│              │ POST /query/│              │ │
│  │  │ transaction │              │ fail        │              │ │
│  │  └─────────────┘              └─────────────┘              │ │
│  │                                                             │ │
│  │  ┌─────────────┐              ┌─────────────┐              │ │
│  │  │ GET /health │              │ GET /       │              │ │
│  │  └─────────────┘              └─────────────┘              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │               Application Layer (Services)                  │ │
│  │                                                             │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │                 QueryService                            │ │ │
│  │  │                                                         │ │ │
│  │  │  ┌─────────────────────┐  ┌─────────────────────┐      │ │ │
│  │  │  │ query_transaction_  │  │ query_failed_       │      │ │ │
│  │  │  │ notifications()     │  │ notifications()     │      │ │ │
│  │  │  └─────────────────────┘  └─────────────────────┘      │ │ │
│  │  └─────────────────────────────────────────────────────────┘ │ │
│  │                              │                               │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │                   QueryPort                             │ │ │
│  │  │                  (Interface)                            │ │ │
│  │  └─────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                 Domain Layer (Models)                      │ │
│  │                                                             │ │
│  │  ┌─────────────────────┐      ┌─────────────────────┐      │ │
│  │  │  NotificationRecord │      │    QueryResult      │      │ │
│  │  │                     │      │                     │      │ │
│  │  │ • transaction_id    │      │ • success: bool     │      │ │
│  │  │ • token             │      │ • data: List[...]   │      │ │
│  │  │ • platform          │      │ • message: str      │      │ │
│  │  │ • status            │      │ • total_count: int  │      │ │
│  │  │ • notification_*    │      │                     │      │ │
│  │  │ • timestamps        │      │                     │      │ │
│  │  │ • ap_id             │      │                     │      │ │
│  │  └─────────────────────┘      └─────────────────────┘      │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │            Infrastructure Layer (Adapters)                 │ │
│  │                                                             │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │            InternalAPIAdapter                           │ │ │
│  │  │                                                         │ │ │
│  │  │  ┌───────────────────┐      ┌───────────────────┐      │ │ │
│  │  │  │ invoke_query_api() │ ────▶│ HTTP Client       │      │ │ │
│  │  │  │                   │      │ (httpx)           │      │ │ │
│  │  │  └───────────────────┘      └───────────────────┘      │ │ │
│  │  │                                        │                │ │ │
│  │  │  ┌───────────────────────────────────────────────────┐ │ │ │
│  │  │  │            Endpoint Mapping                      │ │ │ │
│  │  │  │  "transaction" → "/tx"                           │ │ │ │
│  │  │  │  "fail" → "/fail"                                │ │ │ │
│  │  │  └───────────────────────────────────────────────────┘ │ │ │
│  │  └─────────────────────────────────────────────────────────┘ │ │
│  │                              │                               │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │        InternalAPIInvokerPort                           │ │ │
│  │  │               (Interface)                               │ │ │
│  │  └─────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│                              │                                   │
│                              ▼                                   │
│    ┌─────────────────────────────────────────────────────────┐   │
│    │           Internal API Gateway                          │   │
│    │              HTTP Endpoints                             │   │
│    │         /tx?transaction_id=...                          │   │
│    │         /fail?transaction_id=...                        │   │
│    └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🎯 V4 核心組件

### 1. Command Side (寫入端) - 保持不變

**資料表**: `command-records`

- **主鍵**: `transaction_id` (PK) + `created_at` (SK)
- **功能**: 處理所有寫入操作
- **Stream**: 啟用 DynamoDB Stream 觸發同步

### 2. Query Side (查詢端) - 簡化設計

**資料表**: `notification-records`

- **主鍵**: `transaction_id` (PK) + `created_at` (SK)
- **功能**: 以 `transaction_id` 為中心的查詢操作
- **查詢模式**:
  - **交易查詢**: 根據 `transaction_id` 查詢所有相關推播記錄
  - **失敗查詢**: 根據 `transaction_id` + `status=FAILED` 查詢失敗記錄

### 3. Stream Processor (事件處理器) - 保持六邊形架構

**Lambda 函數**: `stream_processor_lambda`

- **觸發**: DynamoDB Stream 事件
- **功能**: 將 Command Side 數據轉換並同步到 Query Side
- **架構**: 維持六邊形架構設計

### 4. ECS FastAPI Query Service (查詢服務) - V4 簡化實現

**ECS Handler**: `eks_handler/main.py`

- **架構**: 六邊形架構 V4
- **簡化層次**: Web → Application → Domain → Infrastructure
- **新特色**: Internal API Gateway 整合

## 🔧 V4 六邊形架構實現

### Domain Layer (領域層) - 統一模型

```python
class NotificationRecord(BaseModel):
    """推播記錄領域模型 - V4 統一設計"""

    transaction_id: str = Field(..., description="唯一事件識別碼")
    token: Optional[str] = Field(None, description="推播 token")
    platform: str = Field(..., pattern="^(IOS|ANDROID|WEBPUSH)$")
    notification_title: str = Field(..., description="推播標題")
    notification_body: str = Field(..., description="推播內容")
    status: str = Field(..., pattern="^(SENT|DELIVERED|FAILED)$")
    send_ts: Optional[int] = Field(None, description="送出時間戳")
    delivered_ts: Optional[int] = Field(None, description="送達時間戳")
    failed_ts: Optional[int] = Field(None, description="失敗時間戳")
    ap_id: Optional[str] = Field(None, description="來源服務識別碼")
    created_at: int = Field(..., description="建立時間戳")

class QueryResult(BaseModel):
    """統一查詢結果模型"""

    success: bool
    data: List[NotificationRecord] = []
    message: str = ""
    total_count: int = 0
```

### Application Layer (應用層) - 簡化服務

```python
class QueryPort(ABC):
    """查詢服務端口接口 - V4 簡化版本"""

    @abstractmethod
    async def query_transaction_notifications(self, transaction_id: str) -> QueryResult:
        """查詢交易推播記錄"""
        pass

    @abstractmethod
    async def query_failed_notifications(self, transaction_id: str) -> QueryResult:
        """查詢失敗推播記錄"""
        pass

class QueryService(QueryPort):
    """查詢應用服務實現 - V4"""

    def __init__(self, internal_api_adapter: InternalAPIInvokerPort):
        self.internal_api_adapter = internal_api_adapter

    async def query_transaction_notifications(self, transaction_id: str) -> QueryResult:
        """查詢交易推播記錄"""
        try:
            result = await self.internal_api_adapter.invoke_query_api(
                "transaction", {"transaction_id": transaction_id}
            )
            return self._process_query_result(result, "交易推播記錄查詢成功")
        except Exception as e:
            logger.error(f"查詢交易推播記錄失敗: {e}")
            return QueryResult(success=False, message=f"查詢失敗: {str(e)}")
```

### Infrastructure Layer (基礎設施層) - HTTP 適配器

```python
class InternalAPIInvokerPort(ABC):
    """Internal API Gateway 調用端口接口"""

    @abstractmethod
    async def invoke_query_api(self, query_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        pass

class InternalAPIAdapter(InternalAPIInvokerPort):
    """Internal API Gateway 調用適配器 - V4"""

    def __init__(self) -> None:
        self.internal_api_url = os.environ.get(
            "INTERNAL_API_URL",
            "https://internal-api-gateway.amazonaws.com/v1"
        ).rstrip("/")
        self.timeout = int(os.environ.get("REQUEST_TIMEOUT", "5"))

    async def invoke_query_api(self, query_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """調用 Internal API Gateway 查詢端點"""
        endpoint_map = {
            "transaction": "/tx",
            "fail": "/fail",
        }

        if query_type not in endpoint_map:
            raise ValueError(f"Unsupported query type: {query_type}")

        endpoint = endpoint_map[query_type]
        url = f"{self.internal_api_url}{endpoint}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=payload, headers={
                "Content-Type": "application/json",
                "User-Agent": "ECS-QueryService/1.0"
            })

            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=502,
                    detail=f"Internal API Gateway error: {response.status_code}"
                )
```

### Web Layer (Web 層) - 簡化端點

```python
# FastAPI 路由 - V4 簡化設計
@app.get("/tx")
async def get_transaction_notifications_by_id(
    transaction_id: str = Query(..., min_length=1, description="交易唯一識別碼"),
    query_service: QueryService = Depends(get_query_service)
) -> QueryResult:
    """查詢交易推播記錄 - GET 方式"""
    logger.info(f"收到交易查詢請求: transaction_id={transaction_id}")

    try:
        result = await query_service.query_transaction_notifications(transaction_id)
        logger.info(f"交易查詢完成: success={result.success}, count={result.total_count}")
        return result
    except Exception as e:
        logger.error(f"交易查詢異常: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/fail")
async def get_failed_notifications(
    transaction_id: Optional[str] = Query(None, min_length=1, description="交易唯一識別碼（可選）"),
    query_service: QueryService = Depends(get_query_service)
) -> QueryResult:
    """查詢失敗推播記錄 - GET 方式"""
    logger.info(f"收到失敗查詢請求: transaction_id={transaction_id}")

    try:
        result = await query_service.query_failed_notifications(transaction_id)
        logger.info(f"失敗查詢完成: success={result.success}, count={result.total_count}")
        return result
    except Exception as e:
        logger.error(f"失敗查詢異常: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

## 📊 V4 查詢類型 (簡化)

### 1. 交易推播記錄查詢

- **端點**: `GET /tx` 或 `POST /query/transaction`
- **用途**: 根據 `transaction_id` 查詢該交易的所有推播記錄
- **索引**: 主表查詢 (`transaction_id`)

### 2. 失敗推播記錄查詢

- **端點**: `GET /fail` 或 `POST /query/fail`
- **用途**: 根據 `transaction_id` 查詢失敗的推播記錄，支援無參數查詢所有失敗記錄
- **索引**: 主表查詢 + Status 過濾

## 🔄 V4 資料流程

### 寫入流程 (保持不變)

1. 命令寫入 `command-records` 表
2. DynamoDB Stream 觸發 `stream_processor_lambda`
3. Lambda 處理事件並轉換資料格式
4. 同步資料到 `notification-records` 表

### 查詢流程 (V4 簡化)

1. 客戶端呼叫 `/tx` 或 `/fail` 端點
2. FastAPI 路由接收請求
3. `QueryService` 處理業務邏輯
4. `InternalAPIAdapter` 呼叫 Internal API Gateway
5. 查詢 `notification-records` 表
6. 返回統一的 `QueryResult` 格式

## 🎭 V4 優勢與特色

### ✅ 簡化優勢

- **減少端點**: 從 3 個查詢端點簡化為 2 個核心端點
- **統一模型**: 單一 `NotificationRecord` 領域模型
- **專注職責**: 以 `transaction_id` 為中心的查詢責任
- **提升效能**: 減少複雜的查詢邏輯和索引維護

### ✅ 架構優勢

- **保持六邊形**: 維持清晰的架構分層和依賴反轉
- **HTTP 整合**: 透過 Internal API Gateway 的微服務通信
- **依賴注入**: FastAPI 原生的依賴注入系統
- **可測試性**: Mock 友好的端口與適配器設計

### ✅ 開發體驗

- **清晰意圖**: GET 方式直觀，POST 方式完整
- **錯誤處理**: 統一的異常處理和日誌記錄
- **API 文檔**: Pydantic 模型自動生成 OpenAPI 規範
- **類型安全**: 完整的 Python 類型提示

## 🔍 V4 與前版本對比

| 特性                   | V3 版本                              | V4 版本                        |
| ---------------------- | ------------------------------------ | ------------------------------ |
| **查詢端點**           | 3 個端點 (user/marketing/failures)  | 2 個端點 (tx/fail)             |
| **領域模型**           | 3 個不同的回應模型                   | 1 個統一的 NotificationRecord  |
| **查詢邏輯**           | 複雜的多維度查詢                     | 簡化的 transaction_id 中心查詢 |
| **HTTP 方法**          | 僅 POST                              | GET + POST 雙支援              |
| **Architecture**       | EKS 直接 Lambda 調用                 | ECS + Internal API Gateway     |
| **資料索引**           | 多個 GSI                             | 主鍵查詢 + 簡單過濾            |
| **效能**               | 多索引查詢，較慢                     | 單一索引，高效能               |
| **維護性**             | 複雜的業務邏輯                       | 簡化的責任分離                 |

## 🧪 V4 測試策略

### 單元測試

```python
class TestQueryServiceV4:
    """V4 查詢服務單元測試"""

    @pytest.mark.asyncio
    async def test_query_transaction_notifications(self):
        # 測試交易查詢功能

    @pytest.mark.asyncio
    async def test_query_failed_notifications(self):
        # 測試失敗查詢功能

    @pytest.mark.asyncio
    async def test_internal_api_adapter(self):
        # 測試 Internal API 適配器
```

### 整合測試

```python
class TestV4Integration:
    """V4 整合測試"""

    @pytest.mark.asyncio
    async def test_end_to_end_transaction_query(self):
        # 端到端交易查詢測試

    @pytest.mark.asyncio
    async def test_end_to_end_fail_query(self):
        # 端到端失敗查詢測試
```

## 🚀 V4 部署考量

### 環境變數

```bash
# V4 專用環境變數
INTERNAL_API_URL=https://internal-api-gateway.amazonaws.com/v1
REQUEST_TIMEOUT=5
ENVIRONMENT=production
```

### 監控指標

- **端點響應時間**: `/tx` 和 `/fail` 端點的回應時間
- **成功率**: `QueryResult.success` 的百分比
- **錯誤分布**: HTTP 狀態碼和錯誤類型分析

---

**V4 版本透過簡化設計實現了更高的效能和可維護性，同時保持了六邊形架構的核心原則。** 🎯
