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
from datetime import UTC, datetime
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

# ================================
# Domain Models (領域模型)
# ================================


class NotificationRecord(BaseModel):
    """推播記錄領域模型 - 更新以符合新的 schema"""

    transaction_id: str = Field(..., description="唯一事件識別碼")
    token: Optional[str] = Field(None, description="推播 token")
    platform: str = Field(..., pattern="^(IOS|ANDROID|WEBPUSH)$", description="平台類型")
    notification_title: str = Field(..., description="推播標題")
    notification_body: str = Field(..., description="推播內容")
    status: str = Field(..., pattern="^(SENT|DELIVERED|FAILED)$", description="推播狀態")
    send_ts: Optional[int] = Field(None, description="送出時間戳")
    delivered_ts: Optional[int] = Field(None, description="送達時間戳")
    failed_ts: Optional[int] = Field(None, description="失敗時間戳")
    ap_id: Optional[str] = Field(None, description="來源服務識別碼")
    created_at: int = Field(..., description="建立時間戳")


class QueryResult(BaseModel):
    """查詢結果模型"""

    success: bool
    data: List[NotificationRecord] = []
    message: str = ""
    total_count: int = 0


# ================================
# Application Ports (應用端口)
# ================================


class QueryPort(ABC):
    """查詢服務端口接口"""

    @abstractmethod
    async def query_transaction_notifications(self, transaction_id: str) -> QueryResult:
        pass

    @abstractmethod
    async def query_failed_notifications(self, transaction_id: str) -> QueryResult:
        pass


class InternalAPIInvokerPort(ABC):
    """Internal API Gateway 調用端口接口"""

    @abstractmethod
    async def invoke_query_api(self, query_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
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

    async def invoke_query_api(self, query_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """調用 Internal API Gateway 查詢端點"""
        try:
            # 根據查詢類型構建端點 URL - 使用 GET 方法的路徑
            endpoint_map = {
                "transaction": "/tx",
                "fail": "/fail",
            }

            if query_type not in endpoint_map:
                raise ValueError(f"Unsupported query type: {query_type}")

            endpoint = endpoint_map[query_type]
            url = f"{self.internal_api_url}{endpoint}"

            logger.info(f"Invoking Internal API Gateway: {url}")
            logger.info(f"Query parameters: {payload}")

            # 準備請求標頭
            headers = {"Content-Type": "application/json", "User-Agent": "ECS-QueryService/1.0"}

            # 發送 HTTP GET 請求到 Internal API Gateway（使用 query parameters）
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
        except ValueError as e:
            logger.error(f"Invalid query type: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except HTTPException:
            # 重新拋出 HTTPException，不要被通用 exception 處理器捕獲
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Internal API Gateway: {e}")
            raise HTTPException(status_code=500, detail=str(e))


# ================================
# Application Services (應用服務)
# ================================


class QueryService(QueryPort):
    """查詢應用服務實現"""

    def __init__(self, internal_api_adapter: InternalAPIInvokerPort):
        self.internal_api_adapter = internal_api_adapter

    async def query_transaction_notifications(self, transaction_id: str) -> QueryResult:
        """查詢交易推播記錄"""
        try:
            payload = {"transaction_id": transaction_id}
            result = await self.internal_api_adapter.invoke_query_api("transaction", payload)

            return self._process_query_result(
                result,
                f"Successfully retrieved notifications for transaction: {transaction_id}",
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error querying transaction notifications for {transaction_id}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to query transaction notifications: {str(e)}"
            )

    async def query_failed_notifications(self, transaction_id: Optional[str] = None) -> QueryResult:
        """查詢失敗推播記錄"""
        try:
            payload = {}
            if transaction_id and transaction_id.strip():
                payload["transaction_id"] = transaction_id
                message_suffix = f"transaction: {transaction_id}"
            else:
                message_suffix = "all failed notifications"

            result = await self.internal_api_adapter.invoke_query_api("fail", payload)

            return self._process_query_result(
                result,
                f"Successfully retrieved failed notifications for {message_suffix}",
            )

        except HTTPException:
            raise
        except Exception as e:
            error_detail = (
                f"transaction: {transaction_id}" if transaction_id else "all failed notifications"
            )
            logger.error(f"Error querying failed notifications for {error_detail}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to query failed notifications: {str(e)}"
            )

    def _process_query_result(self, result: Dict[str, Any], success_message: str) -> QueryResult:
        """處理查詢結果的共用邏輯"""
        try:
            if not result.get("success", False):
                error_message = result.get("message", "Query failed")
                logger.warning(f"Query failed: {error_message}")
                return QueryResult(success=False, message=error_message, data=[], total_count=0)

            items = result.get("items", [])
            logger.info(f"Query returned {len(items)} items")

            # 轉換資料項目為 NotificationRecord 對象
            notifications = []

            for item in items:
                try:
                    notification = NotificationRecord(**item)
                    notifications.append(notification)
                except Exception as e:
                    logger.warning(f"Failed to parse notification record: {e}, item: {item}")
                    continue

            return QueryResult(
                success=True,
                data=notifications,
                message=success_message,
                total_count=len(notifications),
            )

        except Exception as e:
            logger.error(f"Error processing query result: {e}")
            return QueryResult(
                success=False,
                message=f"Failed to process query result: {str(e)}",
                data=[],
                total_count=0,
            )


# ================================
# Web Layer (Web 層 - FastAPI 路由)
# ================================


# Request/Response 模型
class TransactionQueryRequest(BaseModel):
    transaction_id: str = Field(..., min_length=1, description="交易ID")


class FailQueryRequest(BaseModel):
    transaction_id: Optional[str] = Field(None, min_length=1, description="交易ID（可選）")


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


@app.post("/query/transaction", response_model=QueryResult)
async def query_transaction_notifications(
    request: TransactionQueryRequest, query_service: QueryService = Depends(get_query_service)
) -> QueryResult:
    """
    根據 transaction_id 查詢交易推播記錄

    - **transaction_id**: 交易唯一識別碼
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
    transaction_id: str = Query(..., min_length=1, description="交易唯一識別碼"),
    query_service: QueryService = Depends(get_query_service),
) -> QueryResult:
    """
    根據 transaction_id 查詢交易推播記錄 (GET 方法)

    - **transaction_id**: 交易唯一識別碼
    """
    logger.info(f"API: GET querying transaction notifications for transaction: {transaction_id}")
    try:
        return await query_service.query_transaction_notifications(transaction_id)
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
            "transaction_query": "/query/transaction",
            "failed_query": "/query/fail",
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
