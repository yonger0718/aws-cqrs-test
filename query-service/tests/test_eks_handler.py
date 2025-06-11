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

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

# 設置測試環境
os.environ["ENVIRONMENT"] = "test"

# 導入被測試的模組  # noqa: E402
from eks_handler import QueryService, app  # noqa: E402
from eks_handler.main import (  # noqa: E402
    InternalAPIAdapter,
    NotificationRecord,
    TransactionQueryRequest,
)

# 測試客戶端
client = TestClient(app)


@pytest.mark.unit
class TestAPISchemas:
    """API Schema 測試"""

    def test_transaction_query_request_valid(self) -> None:
        """測試有效的交易查詢請求"""
        request = TransactionQueryRequest(transaction_id="txn-001")
        assert request.transaction_id == "txn-001"

    def test_notification_record_new_schema(self) -> None:
        """測試新 schema 的通知記錄"""
        record = NotificationRecord(
            transaction_id="txn-123",
            token="device-token-abc",
            platform="IOS",
            notification_title="測試通知",
            notification_body="這是測試通知內容",
            status="SENT",
            send_ts=1640995200,
            ap_id="mobile-app-001",
            created_at=1640995200,
        )
        assert record.transaction_id == "txn-123"
        assert record.token == "device-token-abc"
        assert record.notification_body == "這是測試通知內容"


@pytest.mark.unit
class TestTransactionQuery:
    """交易查詢端點測試"""

    @patch("eks_handler.main.InternalAPIAdapter")
    def test_query_transaction_success(self, mock_internal_api_adapter_class: Any) -> None:
        """測試成功查詢交易推播記錄"""
        # 設置 InternalAPIAdapter 的 mock
        mock_internal_api_adapter = mock_internal_api_adapter_class.return_value
        mock_internal_api_adapter.invoke_query_api = AsyncMock(
            return_value={
                "success": True,
                "items": [
                    {
                        "transaction_id": "txn-123",
                        "token": "device-token-abc",
                        "platform": "IOS",
                        "notification_title": "測試通知",
                        "notification_body": "這是測試通知內容",
                        "status": "SENT",
                        "send_ts": 1640995200,
                        "ap_id": "mobile-app-001",
                        "created_at": 1640995200,
                    }
                ],
            }
        )

        # 發送請求
        response = client.post("/query/transaction", json={"transaction_id": "txn-123"})

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["transaction_id"] == "txn-123"
        assert data["data"][0]["notification_body"] == "這是測試通知內容"

    def test_query_transaction_invalid_input(self) -> None:
        """測試無效輸入"""
        # 空交易ID
        response = client.post("/query/transaction", json={"transaction_id": ""})
        assert response.status_code == 422

        # 缺少交易ID
        response = client.post("/query/transaction", json={})
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
                        "transaction_id": "failed-txn",
                        "token": "device-token-xyz",
                        "platform": "ANDROID",
                        "notification_title": "失敗推播",
                        "notification_body": "這是失敗的推播內容",
                        "status": "FAILED",
                        "failed_ts": 1640995200,
                        "ap_id": "mobile-app-001",
                        "created_at": 1640995200,
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

    @patch("eks_handler.main.InternalAPIAdapter")
    def test_query_fail_invalid_input(self, mock_internal_api_adapter_class: Any) -> None:
        """測試無效輸入"""
        # 設置 mock 以防止網路調用
        mock_internal_api_adapter = mock_internal_api_adapter_class.return_value
        mock_internal_api_adapter.invoke_query_api = AsyncMock(
            return_value={
                "success": True,
                "items": [],
            }
        )

        # 空交易ID - 這應該在 Pydantic 驗證層就被攔截
        response = client.post("/query/fail", json={"transaction_id": ""})
        assert response.status_code == 422

        # 缺少交易ID - 這是允許的，因為 transaction_id 是可選的
        response = client.post("/query/fail", json={})
        assert response.status_code == 200


@pytest.mark.unit
class TestHealthAndInfo:
    """健康檢查和資訊端點測試"""

    def test_health_check(self) -> None:
        """測試健康檢查端點"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_root_endpoint(self) -> None:
        """測試根端點"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Query Service"
        assert data["version"] == "4.0.0"
        assert "transaction_query" in data["endpoints"]
        assert "failed_query" in data["endpoints"]


@pytest.mark.unit
class TestQueryService:
    """QueryService 類別測試"""

    @pytest.fixture
    def mock_internal_api_adapter(self) -> Mock:
        """建立 InternalAPIAdapter 的 mock"""
        return Mock(spec=InternalAPIAdapter)

    @pytest.fixture
    def query_service(self, mock_internal_api_adapter: Mock) -> QueryService:
        """建立測試用的 QueryService 實例"""
        return QueryService(mock_internal_api_adapter)

    async def test_query_transaction_notifications_success(
        self, query_service: QueryService, mock_internal_api_adapter: Mock
    ) -> None:
        """測試成功查詢交易通知"""
        # 設定模擬回傳值
        mock_internal_api_adapter.invoke_query_api = AsyncMock(
            return_value={
                "success": True,
                "items": [
                    {
                        "transaction_id": "txn-001",
                        "token": "device-token-001",
                        "platform": "IOS",
                        "notification_title": "交易通知",
                        "notification_body": "您的交易已完成",
                        "status": "DELIVERED",
                        "send_ts": 1640995200,
                        "delivered_ts": 1640995210,
                        "ap_id": "payment-service",
                        "created_at": 1640995200,
                    }
                ],
            }
        )

        # 執行查詢
        result = await query_service.query_transaction_notifications("txn-001")

        # 驗證結果
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0].transaction_id == "txn-001"
        assert result.data[0].status == "DELIVERED"

        # 驗證調用
        mock_internal_api_adapter.invoke_query_api.assert_called_once_with(
            "transaction", {"transaction_id": "txn-001"}
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
                        "transaction_id": "failed-txn",
                        "token": "device-token-failed",
                        "platform": "ANDROID",
                        "notification_title": "失敗推播",
                        "notification_body": "推播失敗",
                        "status": "FAILED",
                        "failed_ts": 1640995200,
                        "ap_id": "mobile-app-001",
                        "created_at": 1640995200,
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

    async def test_query_notifications_failure(
        self, query_service: QueryService, mock_internal_api_adapter: Mock
    ) -> None:
        """測試通知查詢失敗"""
        # 設定模擬回傳失敗結果
        mock_internal_api_adapter.invoke_query_api = AsyncMock(
            return_value={"success": False, "message": "Query failed"}
        )

        # 執行查詢
        result = await query_service.query_transaction_notifications("test-txn")

        # 驗證結果
        assert result.success is False
        assert result.message == "Query failed"
        assert len(result.data) == 0
        assert result.total_count == 0

    async def test_http_exception_propagation(
        self, query_service: QueryService, mock_internal_api_adapter: Mock
    ) -> None:
        """測試 HTTP 異常的傳播"""
        # 設定模擬拋出 HTTPException
        mock_internal_api_adapter.invoke_query_api = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Not found")
        )

        # 驗證異常被正確傳播
        with pytest.raises(HTTPException) as exc_info:
            await query_service.query_transaction_notifications("test-txn")

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Not found"

    async def test_general_exception_handling(
        self, query_service: QueryService, mock_internal_api_adapter: Mock
    ) -> None:
        """測試一般異常處理"""
        # 設定模擬拋出一般異常
        mock_internal_api_adapter.invoke_query_api = AsyncMock(
            side_effect=Exception("Network error")
        )

        # 驗證異常被包裝為 HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await query_service.query_transaction_notifications("test-txn")

        assert exc_info.value.status_code == 500
        assert "Failed to query transaction notifications" in exc_info.value.detail


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
        # 在測試環境中，由於設定不是 production，每次都會創建新實例
        assert adapter1 is not adapter2


@pytest.mark.unit
class TestInternalAPIAdapterErrors:
    """Internal API Adapter 錯誤處理測試"""

    @pytest.fixture
    def adapter(self) -> InternalAPIAdapter:
        """創建 Internal API Adapter 實例"""
        return InternalAPIAdapter()

    async def test_invalid_query_type(self, adapter: InternalAPIAdapter) -> None:
        """測試無效查詢類型"""
        with pytest.raises(HTTPException) as exc_info:
            await adapter.invoke_query_api("invalid_type", {"test": "data"})

        assert exc_info.value.status_code == 400
        assert "Unsupported query type" in exc_info.value.detail

    @patch("httpx.AsyncClient")
    async def test_httpx_timeout_exception(
        self, mock_client: Mock, adapter: InternalAPIAdapter
    ) -> None:
        """測試 HTTP 超時異常"""
        # 直接讓 AsyncClient 構造函數拋出超時異常
        mock_client.side_effect = httpx.TimeoutException("Timeout")

        with pytest.raises(HTTPException) as exc_info:
            await adapter.invoke_query_api("transaction", {"transaction_id": "test"})

        assert exc_info.value.status_code == 504
        assert "timed out" in exc_info.value.detail

    @patch("httpx.AsyncClient")
    async def test_httpx_request_exception(
        self, mock_client: Mock, adapter: InternalAPIAdapter
    ) -> None:
        """測試 HTTP 請求異常"""
        # 直接讓 AsyncClient 構造函數拋出請求異常
        mock_client.side_effect = httpx.RequestError("Connection failed")

        with pytest.raises(HTTPException) as exc_info:
            await adapter.invoke_query_api("transaction", {"transaction_id": "test"})

        assert exc_info.value.status_code == 502
        assert "Failed to connect" in exc_info.value.detail

    @patch("httpx.AsyncClient")
    async def test_unexpected_exception(
        self, mock_client: Mock, adapter: InternalAPIAdapter
    ) -> None:
        """測試意外異常"""
        # 讓 AsyncClient 的初始化就拋出異常
        mock_client.side_effect = Exception("Unexpected error")

        with pytest.raises(HTTPException) as exc_info:
            await adapter.invoke_query_api("transaction", {"transaction_id": "test"})

        assert exc_info.value.status_code == 500
        assert "Unexpected error" in exc_info.value.detail


@pytest.mark.unit
class TestQueryServiceErrorHandling:
    """QueryService 錯誤處理測試"""

    @pytest.fixture
    def mock_adapter(self) -> Mock:
        """創建 mock adapter"""
        return Mock(spec=InternalAPIAdapter)

    @pytest.fixture
    def service(self, mock_adapter: Mock) -> QueryService:
        """創建 QueryService 實例"""
        return QueryService(mock_adapter)

    async def test_process_query_result_failure_response(self, service: QueryService) -> None:
        """測試處理失敗的查詢結果"""
        result = {"success": False, "message": "Database error"}

        processed = service._process_query_result(result, "test message")

        assert processed.success is False
        assert processed.message == "Database error"
        assert len(processed.data) == 0
        assert processed.total_count == 0

    async def test_process_query_result_invalid_item(self, service: QueryService) -> None:
        """測試處理包含無效項目的查詢結果"""
        result = {
            "success": True,
            "items": [
                {
                    "transaction_id": "valid-1",
                    "platform": "IOS",
                    "notification_title": "Valid",
                    "notification_body": "Valid body",
                    "status": "DELIVERED",
                    "created_at": 1640995200,
                },
                {
                    # 缺少必需字段的無效項目
                    "transaction_id": "invalid-1",
                    # 缺少其他必需字段
                },
            ],
        }

        processed = service._process_query_result(result, "test message")

        # 應該只有一個有效項目被處理
        assert processed.success is True
        assert len(processed.data) == 1
        assert processed.data[0].transaction_id == "valid-1"
        assert processed.total_count == 1


@pytest.mark.unit
class TestAPIEndpointErrors:
    """API 端點錯誤處理測試"""

    @patch("eks_handler.main.InternalAPIAdapter")
    def test_transaction_endpoint_unexpected_error(self, mock_adapter_class: Any) -> None:
        """測試交易端點意外錯誤"""
        mock_adapter = mock_adapter_class.return_value
        mock_adapter.invoke_query_api = AsyncMock(side_effect=RuntimeError("Unexpected error"))

        response = client.post("/query/transaction", json={"transaction_id": "test-txn"})

        assert response.status_code == 500
        # 實際的錯誤訊息包含具體的錯誤描述
        assert "Failed to query transaction notifications" in response.json()["detail"]

    @patch("eks_handler.main.InternalAPIAdapter")
    def test_get_transaction_endpoint_unexpected_error(self, mock_adapter_class: Any) -> None:
        """測試 GET 交易端點意外錯誤"""
        mock_adapter = mock_adapter_class.return_value
        mock_adapter.invoke_query_api = AsyncMock(side_effect=RuntimeError("Unexpected error"))

        response = client.get("/tx?transaction_id=test-txn")

        assert response.status_code == 500
        # 檢查是否包含錯誤相關訊息
        detail = response.json()["detail"]
        assert any(keyword in detail for keyword in ["Internal server error", "Failed to query"])

    @patch("eks_handler.main.InternalAPIAdapter")
    def test_fail_endpoint_unexpected_error(self, mock_adapter_class: Any) -> None:
        """測試失敗端點意外錯誤"""
        mock_adapter = mock_adapter_class.return_value
        mock_adapter.invoke_query_api = AsyncMock(side_effect=RuntimeError("Unexpected error"))

        response = client.post("/query/fail", json={"transaction_id": "test-txn"})

        assert response.status_code == 500
        # 檢查是否包含錯誤相關訊息
        detail = response.json()["detail"]
        assert "Failed to query failed notifications" in detail

    @patch("eks_handler.main.InternalAPIAdapter")
    def test_get_fail_endpoint_unexpected_error(self, mock_adapter_class: Any) -> None:
        """測試 GET 失敗端點意外錯誤"""
        mock_adapter = mock_adapter_class.return_value
        mock_adapter.invoke_query_api = AsyncMock(side_effect=RuntimeError("Unexpected error"))

        response = client.get("/fail?transaction_id=test-txn")

        assert response.status_code == 500
        # 檢查是否包含錯誤相關訊息
        detail = response.json()["detail"]
        assert "Failed to query failed notifications" in detail

    def test_get_transaction_empty_parameter(self) -> None:
        """測試 GET 交易端點空參數驗證"""
        response = client.get("/tx?transaction_id=")
        assert response.status_code == 422

    def test_get_fail_empty_parameter(self) -> None:
        """測試 GET 失敗端點空參數驗證"""
        response = client.get("/fail?transaction_id=")
        assert response.status_code == 422


@pytest.mark.unit
class TestEnvironmentConfiguration:
    """環境配置測試"""

    @patch.dict(os.environ, {"ENVIRONMENT": "development"})
    def test_is_local_development_true(self) -> None:
        """測試本地開發環境檢測"""
        adapter = InternalAPIAdapter()
        assert adapter._is_local_development() is True

    @patch.dict(os.environ, {"ENVIRONMENT": "production"})
    def test_is_local_development_false(self) -> None:
        """測試生產環境檢測"""
        adapter = InternalAPIAdapter()
        assert adapter._is_local_development() is False

    @patch.dict(os.environ, {})
    def test_default_environment(self) -> None:
        """測試默認環境配置"""
        # 清除 ENVIRONMENT 環境變數
        if "ENVIRONMENT" in os.environ:
            del os.environ["ENVIRONMENT"]

        adapter = InternalAPIAdapter()
        # 默認環境應該是 development
        assert adapter._is_local_development() is True


@pytest.mark.unit
class TestStartupAndConfiguration:
    """啟動和配置測試"""

    @patch("eks_handler.main.get_internal_api_adapter")
    async def test_startup_event(self, mock_get_adapter: Mock) -> None:
        """測試應用啟動事件"""
        mock_adapter = Mock()
        mock_get_adapter.return_value = mock_adapter

        from eks_handler.main import startup_event

        # 調用啟動事件
        await startup_event()

        # 驗證適配器被初始化
        mock_get_adapter.assert_called_once()

    def test_internal_api_adapter_init_with_env_vars(self) -> None:
        """測試 Internal API Adapter 使用環境變數初始化"""
        with patch.dict(
            os.environ,
            {"INTERNAL_API_URL": "https://test-api.example.com/v2/", "REQUEST_TIMEOUT": "10"},
        ):
            adapter = InternalAPIAdapter()

            assert adapter.internal_api_url == "https://test-api.example.com/v2"
            assert adapter.timeout == 10

    def test_internal_api_adapter_init_defaults(self) -> None:
        """測試 Internal API Adapter 使用默認值初始化"""
        # 確保環境變數不存在
        env_vars_to_remove = ["INTERNAL_API_URL", "REQUEST_TIMEOUT"]
        original_values = {}

        for var in env_vars_to_remove:
            if var in os.environ:
                original_values[var] = os.environ[var]
                del os.environ[var]

        try:
            adapter = InternalAPIAdapter()

            assert adapter.internal_api_url == "https://internal-api-gateway.amazonaws.com/v1"
            assert adapter.timeout == 5
        finally:
            # 恢復原始環境變數
            for var, value in original_values.items():
                os.environ[var] = value


@pytest.mark.unit
class TestFailedNotificationsEdgeCases:
    """失敗通知查詢的邊界案例測試"""

    @pytest.fixture
    def mock_internal_api_adapter(self) -> Mock:
        """建立 InternalAPIAdapter 的 mock"""
        return Mock(spec=InternalAPIAdapter)

    @pytest.fixture
    def query_service(self, mock_internal_api_adapter: Mock) -> QueryService:
        """建立測試用的 QueryService 實例"""
        return QueryService(mock_internal_api_adapter)

    async def test_query_failed_notifications_empty_transaction_id(
        self, query_service: QueryService, mock_internal_api_adapter: Mock
    ) -> None:
        """測試查詢失敗通知時傳入空字符串的 transaction_id"""
        mock_internal_api_adapter.invoke_query_api = AsyncMock(
            return_value={"success": True, "items": []}
        )

        # 傳入空字符串
        result = await query_service.query_failed_notifications("   ")

        # 應該調用時不包含 transaction_id
        mock_internal_api_adapter.invoke_query_api.assert_called_once_with("fail", {})
        assert result.success is True

    async def test_query_failed_notifications_none_transaction_id(
        self, query_service: QueryService, mock_internal_api_adapter: Mock
    ) -> None:
        """測試查詢失敗通知時傳入 None 的 transaction_id"""
        mock_internal_api_adapter.invoke_query_api = AsyncMock(
            return_value={"success": True, "items": []}
        )

        # 傳入 None
        result = await query_service.query_failed_notifications(None)

        # 應該調用時不包含 transaction_id
        mock_internal_api_adapter.invoke_query_api.assert_called_once_with("fail", {})
        assert result.success is True

    async def test_query_failed_notifications_exception_without_transaction_id(
        self, query_service: QueryService, mock_internal_api_adapter: Mock
    ) -> None:
        """測試查詢失敗通知時發生異常且沒有 transaction_id"""
        mock_internal_api_adapter.invoke_query_api = AsyncMock(
            side_effect=Exception("Database error")
        )

        with pytest.raises(HTTPException) as exc_info:
            await query_service.query_failed_notifications(None)

        assert exc_info.value.status_code == 500
        assert "Failed to query failed notifications" in exc_info.value.detail


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
