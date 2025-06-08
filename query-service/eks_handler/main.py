"""
Query Service EKS Handler

CQRS 架構的查詢服務 - Query Side 實現
採用六邊形架構 (Hexagonal Architecture) 設計

主要功能：
1. 用戶推播記錄查詢
2. 行銷活動推播統計
3. 失敗推播記錄追蹤

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
from fastapi import Depends, FastAPI, HTTPException
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
    """推播記錄領域模型"""

    user_id: str
    transaction_id: str
    created_at: int
    marketing_id: Optional[str] = None
    notification_title: str
    status: str = Field(..., pattern="^(SENT|DELIVERED|FAILED)$")
    platform: str = Field(..., pattern="^(IOS|ANDROID|WEBPUSH)$")
    error_msg: Optional[str] = None
    ap_id: Optional[str] = None


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
    async def query_user_notifications(self, user_id: str) -> QueryResult:
        pass

    @abstractmethod
    async def query_marketing_notifications(self, marketing_id: str) -> QueryResult:
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
            # 根據查詢類型構建端點 URL
            endpoint_map = {
                "user": "/query/user",
                "marketing": "/query/marketing",
                "fail": "/query/fail",
            }

            if query_type not in endpoint_map:
                raise ValueError(f"Unsupported query type: {query_type}")

            endpoint = endpoint_map[query_type]
            url = f"{self.internal_api_url}{endpoint}"

            logger.info(f"Invoking Internal API Gateway: {url}")
            logger.info(f"Payload: {payload}")

            # 準備請求標頭
            headers = {"Content-Type": "application/json", "User-Agent": "ECS-QueryService/1.0"}

            # 發送 HTTP POST 請求到 Internal API Gateway
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)

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

    async def query_user_notifications(self, user_id: str) -> QueryResult:
        """查詢用戶推播記錄"""
        try:
            payload = {"user_id": user_id}
            result = await self.internal_api_adapter.invoke_query_api("user", payload)

            return self._process_query_result(
                result, f"Successfully retrieved notifications for user: {user_id}"
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error querying user notifications for {user_id}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to query user notifications: {str(e)}"
            )

    async def query_marketing_notifications(self, marketing_id: str) -> QueryResult:
        """查詢行銷活動推播記錄"""
        try:
            payload = {"marketing_id": marketing_id}
            result = await self.internal_api_adapter.invoke_query_api("marketing", payload)

            return self._process_query_result(
                result,
                f"Successfully retrieved notifications for marketing campaign: {marketing_id}",
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error querying marketing notifications for {marketing_id}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to query marketing notifications: {str(e)}"
            )

    async def query_failed_notifications(self, transaction_id: str) -> QueryResult:
        """查詢失敗推播記錄"""
        try:
            payload = {"transaction_id": transaction_id}
            result = await self.internal_api_adapter.invoke_query_api("fail", payload)

            return self._process_query_result(
                result,
                f"Successfully retrieved failed notifications for transaction: {transaction_id}",
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error querying failed notifications for {transaction_id}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to query failed notifications: {str(e)}"
            )

    def _process_query_result(self, result: Dict[str, Any], success_message: str) -> QueryResult:
        """處理查詢結果"""
        if not result.get("success", False):
            return QueryResult(
                success=False, message=result.get("message", "Query failed"), data=[], total_count=0
            )

        # 轉換為領域模型 (API Gateway 返回的是 'items' 字段，不是 'data')
        items = result.get("items", result.get("data", []))
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


# ================================
# Web Layer (Web 層 - FastAPI 路由)
# ================================


# Request/Response 模型
class UserQueryRequest(BaseModel):
    user_id: str = Field(..., min_length=1, description="用戶ID")


class MarketingQueryRequest(BaseModel):
    marketing_id: str = Field(..., min_length=1, description="行銷活動ID")


class FailQueryRequest(BaseModel):
    transaction_id: str = Field(..., min_length=1, description="交易ID")


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
    title="Query Service ECS Handler",
    description="CQRS 架構的查詢服務 - Query Side 實現 (ECS版本)",
    version="3.0.0",
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


@app.post("/query/user", response_model=QueryResult)
async def query_user_notifications(
    request: UserQueryRequest, query_service: QueryService = Depends(get_query_service)
) -> QueryResult:
    """
    根據 user_id 查詢該用戶最近的推播記錄

    - **user_id**: 用戶唯一識別碼
    """
    logger.info(f"API: Querying notifications for user: {request.user_id}")
    try:
        return await query_service.query_user_notifications(request.user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in user query endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/query/marketing", response_model=QueryResult)
async def query_marketing_notifications(
    request: MarketingQueryRequest, query_service: QueryService = Depends(get_query_service)
) -> QueryResult:
    """
    根據 marketing_id 查詢某活動所觸發的所有推播記錄

    - **marketing_id**: 行銷活動唯一識別碼
    """
    logger.info(f"API: Querying notifications for marketing campaign: {request.marketing_id}")
    try:
        return await query_service.query_marketing_notifications(request.marketing_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in marketing query endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/query/fail", response_model=QueryResult)
async def query_failed_notifications(
    request: FailQueryRequest, query_service: QueryService = Depends(get_query_service)
) -> QueryResult:
    """
    根據 transaction_id 查詢失敗的推播記錄

    - **transaction_id**: 交易唯一識別碼
    """
    logger.info(f"API: Querying failed notifications for transaction: {request.transaction_id}")
    try:
        return await query_service.query_failed_notifications(request.transaction_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in failed query endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/")
async def root() -> Dict[str, Any]:
    """根端點"""
    return {
        "message": "Query Service ECS Handler",
        "architecture": "CQRS + Hexagonal Architecture",
        "version": "3.0.0",
        "description": "通過 Internal API Gateway 調用 Lambda 的 ECS 查詢服務",
        "endpoints": {
            "health_check": "/health",
            "user_query": "/query/user",
            "marketing_query": "/query/marketing",
            "failed_query": "/query/fail",
            "docs": "/docs",
            "redoc": "/redoc",
        },
    }


if __name__ == "__main__":
    import uvicorn

    # 使用環境變數設置主機，避免綁定到所有介面的安全風險  # nosec B104
    # 在生產環境中應設置 HOST=127.0.0.1 或具體的 IP 地址
    host = os.environ.get("HOST", "127.0.0.1")  # 默認使用本地地址
    port = int(os.environ.get("PORT", "8000"))

    logger.info(f"Starting Query Service on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
