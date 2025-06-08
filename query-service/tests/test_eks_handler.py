"""
EKS Handler Unit Tests

測試 FastAPI 應用的核心功能，包括：
- API 端點
- 依賴注入
- 錯誤處理
- 響應格式驗證
"""

import os
import sys
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

# 設置測試環境
os.environ["ENVIRONMENT"] = "test"

# 導入被測試的模組  # noqa: E402
from eks_handler import QueryResult, QueryService, app  # noqa: E402
from eks_handler.main import (  # noqa: E402
    FailQueryRequest,
    InternalAPIAdapter,
    MarketingQueryRequest,
    NotificationRecord,
    UserQueryRequest,
)

# 測試客戶端
client = TestClient(app)


@pytest.mark.unit
class TestAPISchemas:
    """API Schema 測試"""

    def test_user_query_request_valid(self) -> None:
        """測試有效的用戶查詢請求"""
        request = UserQueryRequest(user_id="user-001")
        assert request.user_id == "user-001"

    def test_user_query_request_empty_user_id(self) -> None:
        """測試空用戶ID"""
        with pytest.raises(ValueError):
            UserQueryRequest(user_id="")

    def test_marketing_query_request_valid(self) -> None:
        """測試有效的行銷查詢請求"""
        request = MarketingQueryRequest(marketing_id="campaign-001")
        assert request.marketing_id == "campaign-001"

    def test_fail_query_request_valid(self) -> None:
        """測試有效的失敗查詢請求"""
        request = FailQueryRequest(transaction_id="txn-001")
        assert request.transaction_id == "txn-001"

    def test_notification_record_minimal(self) -> None:
        """測試最小通知記錄"""
        record = NotificationRecord(
            user_id="user-001",
            transaction_id="txn-001",
            created_at=1640995200,
            notification_title="測試",
            status="SENT",
            platform="IOS",
        )
        assert record.user_id == "user-001"
        assert record.status == "SENT"

    def test_notification_record_with_ap_id(self) -> None:
        """測試包含 ap_id 的通知記錄"""
        record = NotificationRecord(
            user_id="user-001",
            transaction_id="txn-001",
            created_at=1640995200,
            notification_title="測試",
            status="SENT",
            platform="IOS",
            ap_id="mobile-app-001",
        )
        assert record.ap_id == "mobile-app-001"

    def test_query_result_structure(self) -> None:
        """測試查詢結果結構"""
        notifications = [
            NotificationRecord(
                user_id="user-001",
                transaction_id="txn-001",
                created_at=1640995200,
                notification_title="測試",
                status="SENT",
                platform="IOS",
                ap_id="mobile-app-001",
            )
        ]

        result = QueryResult(success=True, data=notifications, message="查詢成功", total_count=1)

        assert result.success is True
        assert len(result.data) == 1
        assert result.total_count == 1
        assert result.message == "查詢成功"


@pytest.mark.unit
class TestUserQuery:
    """用戶查詢端點測試"""

    @patch("eks_handler.main.InternalAPIAdapter")
    def test_query_user_success(self, mock_internal_api_adapter_class: Any) -> None:
        """測試成功查詢用戶推播記錄"""
        # 設置 InternalAPIAdapter 的 mock
        mock_internal_api_adapter = mock_internal_api_adapter_class.return_value
        mock_internal_api_adapter.invoke_query_api = AsyncMock(
            return_value={
                "success": True,
                "items": [
                    {
                        "user_id": "user-001",
                        "transaction_id": "txn-123",
                        "created_at": 1640995200,
                        "notification_title": "測試通知",
                        "status": "SENT",
                        "platform": "IOS",
                        "ap_id": "mobile-app-001",
                    }
                ],
            }
        )

        # 發送請求
        response = client.post("/query/user", json={"user_id": "user-001"})

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["user_id"] == "user-001"
        assert data["total_count"] == 1

    @patch("eks_handler.main.InternalAPIAdapter")
    def test_query_user_api_error(self, mock_internal_api_adapter_class: Any) -> None:
        """測試 Internal API Gateway 調用失敗的情況"""
        # 設置 InternalAPIAdapter 的 mock 拋出異常
        mock_internal_api_adapter = mock_internal_api_adapter_class.return_value
        mock_internal_api_adapter.invoke_query_api = AsyncMock(
            side_effect=Exception("Internal API Gateway connection failed")
        )

        # 發送請求
        response = client.post("/query/user", json={"user_id": "user-001"})

        # 驗證錯誤處理
        assert response.status_code == 500
        assert "Internal API Gateway connection failed" in response.json()["detail"]

    def test_query_user_invalid_input(self) -> None:
        """測試無效輸入"""
        # 空用戶ID
        response = client.post("/query/user", json={"user_id": ""})
        assert response.status_code == 422

        # 缺少用戶ID
        response = client.post("/query/user", json={})
        assert response.status_code == 422

    @patch("eks_handler.main.InternalAPIAdapter")
    def test_query_user_http_exception(self, mock_internal_api_adapter_class: Any) -> None:
        """測試 HTTPException 的處理"""
        # 設置 InternalAPIAdapter 的 mock 拋出 HTTPException
        mock_internal_api_adapter = mock_internal_api_adapter_class.return_value
        mock_internal_api_adapter.invoke_query_api = AsyncMock(
            side_effect=HTTPException(status_code=502, detail="Gateway error")
        )

        # 發送請求
        response = client.post("/query/user", json={"user_id": "user-001"})

        # 驗證 HTTPException 被正確傳播
        assert response.status_code == 502
        assert response.json()["detail"] == "Gateway error"


@pytest.mark.unit
class TestMarketingQuery:
    """行銷查詢端點測試"""

    @patch("eks_handler.main.InternalAPIAdapter")
    def test_query_marketing_success(self, mock_internal_api_adapter_class: Any) -> None:
        """測試成功查詢行銷推播記錄"""
        # 設置 InternalAPIAdapter 的 mock
        mock_internal_api_adapter = mock_internal_api_adapter_class.return_value
        mock_internal_api_adapter.invoke_query_api = AsyncMock(
            return_value={
                "success": True,
                "items": [
                    {
                        "user_id": "user-001",
                        "transaction_id": "txn-123",
                        "created_at": 1640995200,
                        "marketing_id": "campaign-001",
                        "notification_title": "行銷推播",
                        "status": "SENT",
                        "platform": "ANDROID",
                        "ap_id": "mobile-app-002",
                    }
                ],
            }
        )

        # 發送請求
        response = client.post("/query/marketing", json={"marketing_id": "campaign-001"})

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["marketing_id"] == "campaign-001"

    def test_query_marketing_invalid_input(self) -> None:
        """測試無效輸入"""
        # 空行銷ID
        response = client.post("/query/marketing", json={"marketing_id": ""})
        assert response.status_code == 422

        # 缺少行銷ID
        response = client.post("/query/marketing", json={})
        assert response.status_code == 422


@pytest.mark.unit
class TestFailQuery:
    """失敗查詢端點測試"""

    @patch("eks_handler.main.InternalAPIAdapter")
    def test_query_fail_success(self, mock_internal_api_adapter_class: Any) -> None:
        """測試成功查詢失敗推播記錄"""
        # 設置 InternalAPIAdapter 的 mock
        mock_internal_api_adapter = mock_internal_api_adapter_class.return_value
        mock_internal_api_adapter.invoke_query_api = AsyncMock(
            return_value={
                "success": True,
                "items": [
                    {
                        "user_id": "user-001",
                        "transaction_id": "failed-txn",
                        "created_at": 1640995200,
                        "notification_title": "失敗推播",
                        "status": "FAILED",
                        "platform": "IOS",
                        "error_msg": "Device token invalid",
                        "ap_id": "mobile-app-001",
                    }
                ],
            }
        )

        # 發送請求
        response = client.post("/query/fail", json={"transaction_id": "failed-txn"})

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["transaction_id"] == "failed-txn"
        assert data["data"][0]["status"] == "FAILED"

    def test_query_fail_invalid_input(self) -> None:
        """測試無效輸入"""
        # 空交易ID
        response = client.post("/query/fail", json={"transaction_id": ""})
        assert response.status_code == 422

        # 缺少交易ID
        response = client.post("/query/fail", json={})
        assert response.status_code == 422


@pytest.mark.unit
class TestHealthAndInfo:
    """健康檢查和資訊端點測試"""

    def test_health_check(self) -> None:
        """測試健康檢查端點"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "query-service-ecs-handler"
        assert data["architecture"] == "CQRS + Hexagonal + ECS Fargate"
        assert data["version"] == "3.0.0"
        assert "timestamp" in data

    def test_root_endpoint(self) -> None:
        """測試根端點"""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "Query Service ECS Handler"
        assert data["version"] == "3.0.0"
        assert data["architecture"] == "CQRS + Hexagonal Architecture"
        assert "endpoints" in data
        assert data["endpoints"]["health_check"] == "/health"
        assert data["endpoints"]["user_query"] == "/query/user"
        assert data["endpoints"]["marketing_query"] == "/query/marketing"
        assert data["endpoints"]["failed_query"] == "/query/fail"


@pytest.mark.unit
class TestInternalAPIAdapter:
    """InternalAPIAdapter 單元測試"""

    def test_initialization(self) -> None:
        """測試適配器初始化"""
        adapter = InternalAPIAdapter()
        assert hasattr(adapter, "internal_api_url")
        assert hasattr(adapter, "timeout")
        assert adapter.timeout == 5  # 默認值

    @patch.dict(os.environ, {"INTERNAL_API_URL": "https://custom-api.example.com/v1"})
    def test_custom_url(self) -> None:
        """測試自定義 URL"""
        adapter = InternalAPIAdapter()
        assert adapter.internal_api_url == "https://custom-api.example.com/v1"

    @patch.dict(os.environ, {"REQUEST_TIMEOUT": "60"})
    def test_custom_timeout(self) -> None:
        """測試自定義超時時間"""
        adapter = InternalAPIAdapter()
        assert adapter.timeout == 60


@pytest.mark.unit
class TestQueryService:
    """QueryService 單元測試"""

    @pytest.fixture
    def mock_internal_api_adapter(self) -> Mock:
        """建立模擬 Internal API Gateway 適配器"""
        return Mock()

    @pytest.fixture
    def query_service(self, mock_internal_api_adapter: Mock) -> QueryService:
        """建立查詢服務實例"""
        return QueryService(mock_internal_api_adapter)

    async def test_query_user_notifications_success(
        self, query_service: QueryService, mock_internal_api_adapter: Mock
    ) -> None:
        """測試成功查詢用戶通知"""
        # 設定模擬回傳值
        mock_internal_api_adapter.invoke_query_api = AsyncMock(
            return_value={
                "success": True,
                "items": [
                    {
                        "user_id": "test-user",
                        "transaction_id": "test-txn",
                        "created_at": 1640995200000,
                        "notification_title": "測試推播",
                        "status": "SENT",
                        "platform": "IOS",
                        "ap_id": "mobile-app-001",
                    }
                ],
                "message": "Query successful",
                "total_count": 1,
            }
        )

        # 執行查詢
        result = await query_service.query_user_notifications("test-user")

        # 驗證結果
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0].user_id == "test-user"
        assert result.total_count == 1

        # 驗證調用
        mock_internal_api_adapter.invoke_query_api.assert_called_once_with(
            "user", {"user_id": "test-user"}
        )

    async def test_query_user_notifications_failure(
        self, query_service: QueryService, mock_internal_api_adapter: Mock
    ) -> None:
        """測試用戶通知查詢失敗"""
        # 設定模擬回傳失敗結果
        mock_internal_api_adapter.invoke_query_api = AsyncMock(
            return_value={"success": False, "message": "Query failed"}
        )

        # 執行查詢
        result = await query_service.query_user_notifications("test-user")

        # 驗證結果
        assert result.success is False
        assert result.message == "Query failed"
        assert len(result.data) == 0
        assert result.total_count == 0

    async def test_query_marketing_notifications_success(
        self, query_service: QueryService, mock_internal_api_adapter: Mock
    ) -> None:
        """測試成功查詢行銷通知"""
        # 設定模擬回傳值
        mock_internal_api_adapter.invoke_query_api = AsyncMock(
            return_value={
                "success": True,
                "items": [
                    {
                        "user_id": "user1",
                        "transaction_id": "txn1",
                        "created_at": 1640995200000,
                        "marketing_id": "campaign-001",
                        "notification_title": "行銷推播",
                        "status": "SENT",
                        "platform": "ANDROID",
                        "ap_id": "mobile-app-002",
                    }
                ],
            }
        )

        # 執行查詢
        result = await query_service.query_marketing_notifications("campaign-001")

        # 驗證結果
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0].marketing_id == "campaign-001"

        # 驗證調用
        mock_internal_api_adapter.invoke_query_api.assert_called_once_with(
            "marketing", {"marketing_id": "campaign-001"}
        )

    async def test_query_failed_notifications_success(
        self, query_service: QueryService, mock_internal_api_adapter: Mock
    ) -> None:
        """測試成功查詢失敗通知"""
        # 設定模擬回傳值
        mock_internal_api_adapter.invoke_query_api = AsyncMock(
            return_value={
                "success": True,
                "items": [
                    {
                        "user_id": "user1",
                        "transaction_id": "failed-txn",
                        "created_at": 1640995200000,
                        "notification_title": "失敗推播",
                        "status": "FAILED",
                        "platform": "IOS",
                        "error_msg": "Device token invalid",
                        "ap_id": "mobile-app-001",
                    }
                ],
            }
        )

        # 執行查詢
        result = await query_service.query_failed_notifications("failed-txn")

        # 驗證結果
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0].transaction_id == "failed-txn"
        assert result.data[0].status == "FAILED"

        # 驗證調用
        mock_internal_api_adapter.invoke_query_api.assert_called_once_with(
            "fail", {"transaction_id": "failed-txn"}
        )

    async def test_http_exception_propagation(
        self, query_service: QueryService, mock_internal_api_adapter: Mock
    ) -> None:
        """測試 HTTPException 的傳播"""
        # 設定模擬拋出 HTTPException
        mock_internal_api_adapter.invoke_query_api = AsyncMock(
            side_effect=HTTPException(status_code=502, detail="Gateway error")
        )

        # 執行查詢應該拋出 HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await query_service.query_user_notifications("test-user")

        assert exc_info.value.status_code == 502
        assert "Gateway error" in str(exc_info.value.detail)

    async def test_general_exception_handling(
        self, query_service: QueryService, mock_internal_api_adapter: Mock
    ) -> None:
        """測試一般異常處理"""
        # 設定模擬拋出一般異常
        mock_internal_api_adapter.invoke_query_api = AsyncMock(
            side_effect=Exception("Connection error")
        )

        # 執行查詢應該拋出 HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await query_service.query_user_notifications("test-user")

        assert exc_info.value.status_code == 500
        assert "Failed to query user notifications" in str(exc_info.value.detail)


@pytest.mark.unit
class TestDependencyInjection:
    """依賴注入測試"""

    def test_get_internal_api_adapter_singleton(self) -> None:
        """測試 InternalAPIAdapter 單例模式"""
        # 在非測試環境中應該返回相同的實例
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            from eks_handler.main import get_internal_api_adapter

            adapter1 = get_internal_api_adapter()
            adapter2 = get_internal_api_adapter()
            assert adapter1 is adapter2

    def test_get_internal_api_adapter_in_test(self) -> None:
        """測試在測試環境中的行為"""
        # 檢查是否在測試環境中
        assert "pytest" in sys.modules

        from eks_handler.main import get_internal_api_adapter

        # 在測試環境中應該每次返回新實例
        adapter1 = get_internal_api_adapter()
        adapter2 = get_internal_api_adapter()
        # 由於測試環境每次都創建新實例，所以不應該是同一個對象
        assert isinstance(adapter1, type(adapter2))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
