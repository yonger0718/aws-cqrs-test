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

import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

# 設置日誌
logging.basicConfig(level=logging.INFO)
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


class LambdaInvokerPort(ABC):
    """Lambda 調用端口接口"""

    @abstractmethod
    async def invoke_lambda(self, function_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        pass


# ================================
# Infrastructure Adapters (基礎設施適配器)
# ================================


class LambdaAdapter(LambdaInvokerPort):
    """Lambda 調用適配器"""

    def __init__(self) -> None:
        """初始化 Lambda 客戶端"""
        session = boto3.Session()
        region_name = session.region_name or "ap-southeast-1"

        if self._is_local_development():
            # 開發環境：使用 LocalStack
            self.lambda_client = boto3.client(
                "lambda", endpoint_url="http://localstack:4566", region_name=region_name
            )
        else:
            # 生產環境：使用 AWS Lambda
            self.lambda_client = boto3.client("lambda", region_name=region_name)

        logger.info(f"Lambda client initialized for region: {region_name}")

    def _is_local_development(self) -> bool:
        """檢查是否為本地開發環境"""
        return os.environ.get("ENVIRONMENT", "development") == "development"

    async def invoke_lambda(self, function_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """調用 Lambda 函數"""
        try:
            function_name_with_prefix = f"query-service-{function_name}"
            logger.info(f"Invoking Lambda function: {function_name_with_prefix}")

            response = self.lambda_client.invoke(
                FunctionName=function_name_with_prefix,
                InvocationType="RequestResponse",
                Payload=json.dumps(payload),
            )

            result = json.loads(response["Payload"].read())

            # 處理 Lambda 響應格式
            if "body" in result:
                return json.loads(result["body"])  # type: ignore
            return result  # type: ignore

        except ClientError as e:
            logger.error(f"Lambda invocation error: {e}")
            raise HTTPException(
                status_code=502, detail=f"Failed to invoke Lambda function: {function_name}"
            )
        except Exception as e:
            logger.error(f"Unexpected error invoking Lambda {function_name}: {e}")
            raise HTTPException(status_code=500, detail=str(e))


# ================================
# Application Services (應用服務)
# ================================


class QueryService(QueryPort):
    """查詢應用服務實現"""

    def __init__(self, lambda_adapter: LambdaInvokerPort):
        self.lambda_adapter = lambda_adapter

    async def query_user_notifications(self, user_id: str) -> QueryResult:
        """查詢用戶推播記錄"""
        try:
            payload = {"query_type": "user", "user_id": user_id}
            result = await self.lambda_adapter.invoke_lambda("query_result_lambda", payload)

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
            payload = {"query_type": "marketing", "marketing_id": marketing_id}
            result = await self.lambda_adapter.invoke_lambda("query_result_lambda", payload)

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
            payload = {"query_type": "fail", "transaction_id": transaction_id}
            result = await self.lambda_adapter.invoke_lambda("query_result_lambda", payload)

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
                success=False, message=result.get("message", "Query failed"), total_count=0
            )

        # 轉換為領域模型 (Lambda 返回的是 'items' 字段，不是 'data')
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


# 依賴注入
def get_lambda_adapter() -> LambdaAdapter:
    return LambdaAdapter()


def get_query_service(lambda_adapter: LambdaAdapter = Depends(get_lambda_adapter)) -> QueryService:
    return QueryService(lambda_adapter)


# 初始化 FastAPI 應用
app = FastAPI(
    title="Query Service EKS Handler",
    description="CQRS 架構的查詢服務 - Query Side 實現",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ================================
# API Endpoints (API 端點)
# ================================


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """健康檢查端點"""
    return {
        "status": "healthy",
        "service": "query-service-eks-handler",
        "architecture": "CQRS + Hexagonal",
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
    return await query_service.query_user_notifications(request.user_id)


@app.post("/query/marketing", response_model=QueryResult)
async def query_marketing_notifications(
    request: MarketingQueryRequest, query_service: QueryService = Depends(get_query_service)
) -> QueryResult:
    """
    根據 marketing_id 查詢某活動所觸發的所有推播記錄

    - **marketing_id**: 行銷活動唯一識別碼
    """
    logger.info(f"API: Querying notifications for marketing campaign: {request.marketing_id}")
    return await query_service.query_marketing_notifications(request.marketing_id)


@app.post("/query/fail", response_model=QueryResult)
async def query_failed_notifications(
    request: FailQueryRequest, query_service: QueryService = Depends(get_query_service)
) -> QueryResult:
    """
    根據 transaction_id 查詢失敗的推播記錄

    - **transaction_id**: 交易唯一識別碼
    """
    logger.info(f"API: Querying failed notifications for transaction: {request.transaction_id}")
    return await query_service.query_failed_notifications(request.transaction_id)


@app.get("/")
async def root() -> Dict[str, Any]:
    """根路径資訊"""
    return {
        "service": "Query Service EKS Handler",
        "architecture": "CQRS + Hexagonal Architecture",
        "version": "2.0.0",
        "description": "CQRS 模式的 Query Side 實現，採用六邊形架構設計",
        "endpoints": {
            "user_query": "/query/user",
            "marketing_query": "/query/marketing",
            "fail_query": "/query/fail",
            "health": "/health",
            "docs": "/docs",
        },
        "features": [
            "用戶推播記錄查詢",
            "行銷活動推播統計",
            "失敗推播記錄追蹤",
            "RESTful API 設計",
            "依賴注入架構",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    # 使用環境變數設置主機，避免綁定到所有介面的安全風險  # nosec B104
    # 在生產環境中應設置 HOST=127.0.0.1 或具體的 IP 地址
    host = os.environ.get("HOST", "127.0.0.1")  # 默認使用本地地址
    port = int(os.environ.get("PORT", "8000"))

    logger.info(f"Starting Query Service on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
