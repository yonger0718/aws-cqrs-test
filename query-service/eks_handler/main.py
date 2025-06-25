"""
Query Service EKS Handler

CQRS 架構的查詢服務 - Query Side 實現
採用六邊形架構 (Hexagonal Architecture) 設計

版本：v4 - 專注於 transaction_id 基礎查詢的優化版本

主要功能：
1. 交易推播記錄查詢（通過 transaction_id）
2. 失敗推播記錄追蹤（通過 transaction_id + status 過濾）

架構層次：
- Domain Layer: 領域模型與介面
- Application Layer: 應用服務
- Infrastructure Layer: 基礎設施適配器
- Web Layer: FastAPI 路由控制器
"""

import logging
import os
import sys
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# UTC+8 timezone object
UTC_PLUS_8 = timezone(timedelta(hours=8))


def convert_timestamp_to_utc8_string(timestamp: Optional[int]) -> Optional[str]:
    """Convert Unix timestamp to UTC+8 timezone string format"""
    if timestamp is None or timestamp == 0:
        return None

    try:
        # Convert timestamp to datetime in UTC+8
        dt = datetime.fromtimestamp(timestamp / 1000.0, tz=UTC_PLUS_8)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC+8")
    except (ValueError, TypeError, OSError) as e:
        logger.warning(f"Failed to convert timestamp {timestamp}: {e}")
        return None


# ================================
# Domain Models (領域模型)
# ================================


class NotificationRecord(BaseModel):
    """推播記錄領域模型 - 更新以符合新的 schema 並包含時區轉換"""

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

    # UTC+8 時間字串欄位
    send_time_utc8: Optional[str] = Field(None, description="送出時間 (UTC+8)")
    delivered_time_utc8: Optional[str] = Field(None, description="送達時間 (UTC+8)")
    failed_time_utc8: Optional[str] = Field(None, description="失敗時間 (UTC+8)")
    created_time_utc8: Optional[str] = Field(None, description="建立時間 (UTC+8)")


class QueryResult(BaseModel):
    """查詢結果模型"""

    success: bool
    data: List[NotificationRecord] = []
    message: str = ""
    total_count: int = 0
    query_info: Optional[Dict[str, Any]] = None


# ================================
# Application Ports (應用端口)
# ================================


class QueryPort(ABC):
    """查詢服務端口接口"""

    @abstractmethod
    async def query_transaction_notifications(
        self, transaction_id: Optional[str] = None, limit: int = 30
    ) -> QueryResult:
        """查詢交易推播記錄"""
        pass

    @abstractmethod
    async def query_failed_notifications(self, transaction_id: Optional[str] = None) -> QueryResult:
        """查詢失敗推播記錄"""
        pass

    @abstractmethod
    async def query_sns_notifications(self, sns_id: str) -> QueryResult:
        """查詢 SNS 推播記錄"""
        pass


class InternalAPIInvokerPort(ABC):
    """Internal API Gateway 調用端口接口"""

    @abstractmethod
    async def invoke_transaction_query(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """調用交易查詢端點"""
        pass

    @abstractmethod
    async def invoke_failed_query(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """調用失敗查詢端點"""
        pass

    @abstractmethod
    async def invoke_sns_query(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """調用 SNS 查詢端點"""
        pass


# ================================
# Infrastructure Adapters (基礎設施適配器)
# ================================


class InternalAPIAdapter(InternalAPIInvokerPort):
    """Internal API Gateway 調用適配器"""

    def __init__(self) -> None:
        """初始化 Internal API Gateway 客戶端"""
        # 從環境變數獲取 Internal API Gateway URL
        self.internal_api_url = os.environ.get(
            "INTERNAL_API_URL", "https://internal-api-gateway.amazonaws.com/v1"
        ).rstrip("/")

        # 設置請求超時時間
        self.timeout = int(os.environ.get("REQUEST_TIMEOUT", "5"))

        logger.info(f"Internal API Gateway adapter initialized with URL: {self.internal_api_url}")
        logger.info(f"Request timeout: {self.timeout}s")

    def _is_local_development(self) -> bool:
        """檢查是否為本地開發環境"""
        env = os.environ.get("ENVIRONMENT", "development")
        # 在測試環境中，只有當環境變量不是production時才視為本地開發環境
        if "pytest" in sys.modules:
            return env != "production"
        return env in ("development", "test")

    async def invoke_transaction_query(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """調用交易查詢端點"""
        return await self._invoke_api_endpoint("/tx", payload)

    async def invoke_failed_query(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """調用失敗查詢端點"""
        return await self._invoke_api_endpoint("/fail", payload)

    async def invoke_sns_query(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """調用 SNS 查詢端點"""
        return await self._invoke_api_endpoint("/sns", payload)

    async def _invoke_api_endpoint(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """統一的 API 端點調用方法 - 統一使用 GET 請求"""
        try:
            url = f"{self.internal_api_url}{endpoint}"

            logger.info(f"Invoking Internal API Gateway: {url}")
            logger.info(f"Query parameters: {payload}")

            # 準備請求標頭
            headers = {"Content-Type": "application/json", "User-Agent": "ECS-QueryService/1.0"}

            # 統一使用 GET 方法 - 所有查詢都是 GET 語義
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=payload, headers=headers)

                # 記錄響應狀態
                logger.info(f"Internal API Gateway response status: {response.status_code}")

                # 檢查響應狀態
                if response.status_code == 200:
                    result: Dict[str, Any] = response.json()
                    logger.info(f"Internal API Gateway response: {result}")
                    return result
                else:
                    error_text = response.text
                    logger.error(
                        f"Internal API Gateway error: {response.status_code} - {error_text}"
                    )
                    raise HTTPException(
                        status_code=502,
                        detail=f"Internal API Gateway error: {response.status_code} - {error_text}",
                    )

        except httpx.TimeoutException:
            logger.error(f"Request to Internal API Gateway timed out after {self.timeout}s")
            raise HTTPException(
                status_code=504,
                detail=f"Request to Internal API Gateway timed out after {self.timeout}s",
            )
        except httpx.RequestError as e:
            logger.error(f"Request to Internal API Gateway failed: {e}")
            raise HTTPException(
                status_code=502, detail=f"Failed to connect to Internal API Gateway: {str(e)}"
            )
        except HTTPException:
            # 重新拋出 HTTPException，不要被通用 exception 處理器捕獲
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Internal API Gateway: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # 舊方法保持向後兼容，但標記為 deprecated
    async def invoke_query_api(self, query_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """@deprecated: 使用專門的方法 invoke_transaction_query, invoke_failed_query, invoke_sns_query"""
        if query_type == "tx" or query_type == "transaction":
            return await self.invoke_transaction_query(payload)
        elif query_type == "fail":
            return await self.invoke_failed_query(payload)
        elif query_type == "sns":
            return await self.invoke_sns_query(payload)
        else:
            raise ValueError(f"Unsupported query type: {query_type}")


# ================================
# Application Services (應用服務)
# ================================


class QueryService(QueryPort):
    """查詢應用服務實現"""

    def __init__(self, internal_api_adapter: InternalAPIInvokerPort):
        self.internal_api_adapter = internal_api_adapter

    async def query_transaction_notifications(
        self, transaction_id: Optional[str] = None, limit: int = 30
    ) -> QueryResult:
        """查詢交易推播記錄 - 支持可選 transaction_id 和限制筆數"""
        try:
            # ECS 應該調用 Internal API Gateway 來查詢資料
            payload: Dict[str, Any] = {}
            if transaction_id:
                payload["transaction_id"] = transaction_id
            payload["limit"] = limit

            response_data = await self.internal_api_adapter.invoke_transaction_query(payload)

            if not response_data.get("success", False):
                logger.warning(f"Query failed: {response_data}")
                return QueryResult(
                    success=False,
                    message=response_data.get("message", "查詢失敗"),
                    total_count=0,
                )

            items = response_data.get("items", [])
            processed_records = await self._process_notification_records(items)

            query_type = "specific" if transaction_id else "recent"
            message = response_data.get("message", f"查詢完成 ({query_type})")

            return QueryResult(
                success=True,
                data=processed_records,
                message=message,
                total_count=len(processed_records),
                query_info=response_data.get(
                    "query_info",
                    {"transaction_id": transaction_id, "limit": limit, "query_type": query_type},
                ),
            )

        except Exception as e:
            logger.error(f"Error querying transaction notifications: {e}")
            raise HTTPException(status_code=500, detail=f"查詢服務錯誤: {str(e)}")

    async def query_failed_notifications(self, transaction_id: Optional[str] = None) -> QueryResult:
        """查詢失敗推播記錄"""
        try:
            payload: Dict[str, Any] = {}
            if transaction_id and transaction_id.strip():
                payload["transaction_id"] = transaction_id

            response_data = await self.internal_api_adapter.invoke_failed_query(payload)

            if not response_data.get("success", False):
                logger.warning(f"Failed query failed: {response_data}")
                return QueryResult(
                    success=False,
                    message=response_data.get("message", "查詢失敗"),
                    total_count=0,
                )

            items = response_data.get("items", [])
            processed_records = await self._process_notification_records(items)

            return QueryResult(
                success=True,
                data=processed_records,
                message=response_data.get("message", "失敗記錄查詢完成"),
                total_count=len(processed_records),
            )

        except Exception as e:
            logger.error(f"Error querying failed notifications: {e}")
            raise HTTPException(status_code=500, detail=f"查詢服務錯誤: {str(e)}")

    async def query_sns_notifications(self, sns_id: str) -> QueryResult:
        """查詢 SNS 推播記錄"""
        try:
            payload: Dict[str, Any] = {"sns_id": sns_id}
            response_data = await self.internal_api_adapter.invoke_sns_query(payload)

            if not response_data.get("success", False):
                logger.warning(f"SNS query failed: {response_data}")
                return QueryResult(
                    success=False,
                    message=response_data.get("message", "查詢失敗"),
                    total_count=0,
                )

            items = response_data.get("items", [])
            processed_records = await self._process_notification_records(items)

            return QueryResult(
                success=True,
                data=processed_records,
                message=response_data.get("message", "SNS 推播記錄查詢完成"),
                total_count=len(processed_records),
            )

        except Exception as e:
            logger.error(f"Error querying SNS notifications: {e}")
            raise HTTPException(status_code=500, detail=f"查詢服務錯誤: {str(e)}")

    async def _process_notification_records(
        self, items: List[Dict[str, Any]]
    ) -> List[NotificationRecord]:
        """處理推播記錄並轉換時間戳為 UTC+8 格式"""
        records = []

        for item in items:
            try:
                # 轉換時間戳為 UTC+8 字串
                send_time_utc8 = convert_timestamp_to_utc8_string(item.get("send_ts"))
                delivered_time_utc8 = convert_timestamp_to_utc8_string(item.get("delivered_ts"))
                failed_time_utc8 = convert_timestamp_to_utc8_string(item.get("failed_ts"))
                created_time_utc8 = convert_timestamp_to_utc8_string(item.get("created_at"))

                # 處理 platform 欄位：空字符串視為 None
                platform = item.get("platform")
                if platform == "":
                    platform = None

                record_data = {
                    "transaction_id": item.get("transaction_id", ""),
                    "token": item.get("token"),
                    "platform": platform,
                    "notification_title": item.get("notification_title", ""),
                    "notification_body": item.get("notification_body", ""),
                    "status": item.get("status", ""),
                    "send_ts": item.get("send_ts"),
                    "delivered_ts": item.get("delivered_ts"),
                    "failed_ts": item.get("failed_ts"),
                    "ap_id": str(item.get("ap_id")) if item.get("ap_id") is not None else None,
                    "created_at": int(item.get("created_at", 0)),
                    "sns_id": item.get("sns_id"),
                    "send_time_utc8": send_time_utc8,
                    "delivered_time_utc8": delivered_time_utc8,
                    "failed_time_utc8": failed_time_utc8,
                    "created_time_utc8": created_time_utc8,
                }

                # 只保留非 None 值
                record_data = {k: v for k, v in record_data.items() if v is not None}

                record = NotificationRecord(**record_data)
                records.append(record)

            except Exception as e:
                logger.error(f"Error processing notification record: {e}, item: {item}")
                continue

        return records


# ================================
# Web Layer (Web 層 - FastAPI 路由)
# ================================


# Request/Response 模型
class TransactionQueryRequest(BaseModel):
    transaction_id: str = Field(..., min_length=1, description="交易ID")


class FailQueryRequest(BaseModel):
    transaction_id: Optional[str] = Field(None, min_length=1, description="交易ID（可選）")


class SnsQueryRequest(BaseModel):
    sns_id: str = Field(..., min_length=1, description="SNS 推播識別碼")


# 全局單例實例
_internal_api_adapter: Optional[InternalAPIAdapter] = None
_query_service: Optional[QueryService] = None


# 依賴注入
def get_internal_api_adapter() -> InternalAPIAdapter:
    """獲取Internal API Gateway適配器實例，支持測試中的Mock替換"""
    global _internal_api_adapter
    # 在測試環境中不使用緩存，以便Mock能正確工作
    if "pytest" in sys.modules:
        # 在測試環境中檢查是否為生產環境設定
        env = os.environ.get("ENVIRONMENT", "development")
        if env == "production":
            # 只有在明確設定為 production 時才使用 singleton
            if _internal_api_adapter is None:
                _internal_api_adapter = InternalAPIAdapter()
            return _internal_api_adapter
        else:
            # 測試環境中每次返回新實例
            return InternalAPIAdapter()
    if _internal_api_adapter is None:
        _internal_api_adapter = InternalAPIAdapter()
    return _internal_api_adapter


def get_query_service(
    internal_api_adapter: InternalAPIAdapter = Depends(get_internal_api_adapter),
) -> QueryService:
    """獲取查詢服務實例，總是使用最新的internal_api_adapter以支持測試"""
    return QueryService(internal_api_adapter)


# 初始化 FastAPI 應用
app = FastAPI(
    title="Query Service API",
    description="CQRS 查詢服務 API - 專注於高效的交易推播記錄查詢",
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.on_event("startup")
async def startup_event() -> None:
    """應用啟動時初始化服務"""
    logger.info("Initializing ECS services...")
    # 預先初始化 Internal API adapter 以觸發除錯日誌
    adapter = get_internal_api_adapter()
    logger.info(f"ECS services initialized successfully with adapter: {adapter}")


# ================================
# API Endpoints (API 端點)
# ================================


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """健康檢查端點"""
    return {
        "status": "healthy",
        "service": "query-service-ecs-handler",
        "architecture": "CQRS + Hexagonal + ECS Fargate",
        "version": "3.0.0",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.post("/query/transaction", response_model=QueryResult, deprecated=True)
async def query_transaction_notifications(
    request: TransactionQueryRequest, query_service: QueryService = Depends(get_query_service)
) -> QueryResult:
    """
    根據 transaction_id 查詢交易推播記錄 (Legacy 端點)

    **⚠️ DEPRECATED**: 建議使用 `GET /tx` 端點，支援更多功能

    - **transaction_id**: 交易唯一識別碼（必填）

    **限制**:
    - 只支援特定 transaction_id 查詢
    - 不支援最新記錄查詢
    - 不支援 limit 參數

    **推薦**: 使用 `GET /tx?transaction_id={id}&limit={num}` 獲得完整功能
    """
    logger.info(
        f"API: Querying transaction notifications for transaction: {request.transaction_id}"
    )
    try:
        return await query_service.query_transaction_notifications(request.transaction_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in transaction query endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/tx")
async def get_transaction_notifications_by_id(
    transaction_id: Optional[str] = Query(None, min_length=1, description="交易唯一識別碼（可選）"),
    limit: int = Query(30, ge=1, le=100, description="查詢筆數限制（1-100，預設30）"),
    query_service: QueryService = Depends(get_query_service),
) -> QueryResult:
    """
    根據 transaction_id 查詢交易推播記錄，或查詢最新記錄 (GET 方法)

    - **transaction_id**: 交易唯一識別碼（可選）
    - **limit**: 當未指定 transaction_id 時，返回最新記錄的數量限制
    """
    if transaction_id:
        logger.info(
            f"API: GET querying transaction notifications for transaction: {transaction_id}"
        )
    else:
        logger.info(f"API: GET querying recent transaction notifications (limit: {limit})")

    try:
        return await query_service.query_transaction_notifications(transaction_id, limit)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in GET transaction query endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/query/fail", response_model=QueryResult)
async def query_failed_notifications(
    request: Optional[FailQueryRequest] = None,
    query_service: QueryService = Depends(get_query_service),
) -> QueryResult:
    """
    根據 transaction_id 查詢失敗推播記錄，或查詢所有失敗記錄

    - **transaction_id**: 交易唯一識別碼（可選，如不提供則查詢所有失敗記錄）
    """
    transaction_id = request.transaction_id if request else None
    logger.info(f"API: Querying failed notifications for transaction: {transaction_id or 'all'}")
    try:
        return await query_service.query_failed_notifications(transaction_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in failed query endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/fail")
async def get_failed_notifications(
    transaction_id: Optional[str] = Query(None, min_length=1, description="交易唯一識別碼（可選）"),
    query_service: QueryService = Depends(get_query_service),
) -> QueryResult:
    """
    查詢失敗推播記錄 (GET 方法)

    - **transaction_id**: 交易唯一識別碼（可選，如不提供則查詢所有失敗記錄）
    """
    logger.info(
        f"API: GET querying failed notifications for transaction: {transaction_id or 'all'}"
    )
    try:
        return await query_service.query_failed_notifications(transaction_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in GET failed query endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/query/sns", response_model=QueryResult)
async def query_sns_notifications(
    request: SnsQueryRequest, query_service: QueryService = Depends(get_query_service)
) -> QueryResult:
    """
    根據 sns_id 查詢推播記錄

    - **sns_id**: SNS 推播識別碼
    """
    logger.info(f"API: Querying SNS notifications for sns_id: {request.sns_id}")
    try:
        return await query_service.query_sns_notifications(request.sns_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in SNS query endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/sns")
async def get_sns_notifications_by_id(
    sns_id: str = Query(..., min_length=1, description="SNS 推播識別碼"),
    query_service: QueryService = Depends(get_query_service),
) -> QueryResult:
    """
    根據 sns_id 查詢推播記錄 (GET 方法)

    - **sns_id**: SNS 推播識別碼
    """
    logger.info(f"API: GET querying SNS notifications for sns_id: {sns_id}")
    try:
        return await query_service.query_sns_notifications(sns_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in GET SNS query endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/")
async def root() -> Dict[str, Any]:
    """
    API 根端點，提供服務資訊和可用端點清單
    """
    return {
        "service": "Query Service",
        "version": "4.0.0",
        "description": "CQRS 查詢服務 - 專注於高效的交易推播記錄查詢",
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "endpoints": {
            "transaction_query": "/tx",  # 推薦使用 - 支援可選參數和最新記錄查詢
            "transaction_query_legacy": "/query/transaction",  # Legacy - 僅支援特定交易查詢
            "failed_query": "/query/fail",
            "failed_query_get": "/fail",  # GET 方法
            "sns_query": "/query/sns",
            "sns_query_get": "/sns",  # GET 方法
            "docs": "/docs",
            "health": "/health",
        },
        "architecture": "Hexagonal Architecture with CQRS",
        "optimization": "Optimized for transaction_id based primary key queries",
    }


if __name__ == "__main__":
    import uvicorn

    # 使用環境變數設置主機，避免綁定到所有介面的安全風險  # nosec B104
    # 在生產環境中應設置 HOST=127.0.0.1 或具體的 IP 地址
    host = os.environ.get("HOST", "127.0.0.1")  # 默認使用本地地址
    port = int(os.environ.get("PORT", "8000"))

    logger.info(f"Starting Query Service on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
