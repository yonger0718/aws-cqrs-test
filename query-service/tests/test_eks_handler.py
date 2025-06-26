"""
EKS Handler Unit Tests

測試 FastAPI 應用的核心功能，包括：
- API 端點
- 依賴注入
- 錯誤處理
- 響應格式驗證
- 時間戳轉換功能
- 可選參數支援
"""

import os
import sys
from typing import Any, Dict, List
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
    SnsQueryRequest,
    TransactionQueryRequest,
    convert_timestamp_to_utc8_string,
)

# 測試客戶端
client = TestClient(app)


@pytest.mark.unit
class TestTimestampConversion:
    """時間戳轉換功能測試"""

    def test_convert_timestamp_to_utc8_string_valid(self) -> None:
        """測試有效時間戳轉換"""
        # 測試 Unix 時間戳 (毫秒)
        timestamp = 1640995200000  # 2022-01-01 00:00:00 UTC -> 2022-01-01 08:00:00 UTC+8
        result = convert_timestamp_to_utc8_string(timestamp)
        assert result == "2022-01-01 08:00:00 UTC+8"

    def test_convert_timestamp_to_utc8_string_none(self) -> None:
        """測試 None 時間戳"""
        result = convert_timestamp_to_utc8_string(None)
        assert result is None

    def test_convert_timestamp_to_utc8_string_zero(self) -> None:
        """測試零時間戳"""
        result = convert_timestamp_to_utc8_string(0)
        assert result is None

    def test_convert_timestamp_to_utc8_string_invalid(self) -> None:
        """測試無效時間戳"""
        # 測試超出範圍的時間戳
        invalid_timestamp = 999999999999999999
        result = convert_timestamp_to_utc8_string(invalid_timestamp)
        assert result is None


@pytest.mark.unit
class TestAPISchemas:
    """API Schema 測試"""

    def test_transaction_query_request_valid(self) -> None:
        """測試有效的交易查詢請求"""
        request = TransactionQueryRequest(transaction_id="txn-001")
        assert request.transaction_id == "txn-001"

    def test_notification_record_new_schema(self) -> None:
        """測試新增的 schema 欄位是否正確"""
        # 使用完整的 UTC+8 轉換測試數據
        record = NotificationRecord(
            transaction_id="txn-123",
            token="device-token-abc",
            platform="IOS",
            notification_title="測試通知",
            notification_body="這是測試通知內容",
            status="SENT",
            send_ts=1640995200000,  # 2022-01-01 00:00:00 UTC = 2022-01-01 08:00:00 UTC+8
            delivered_ts=None,
            failed_ts=None,
            ap_id="mobile-app-001",
            created_at=1640995200000,
            sns_id="sns-12345",
            # 添加 UTC+8 時間字串欄位
            send_time_utc8=convert_timestamp_to_utc8_string(1640995200000),
            delivered_time_utc8=None,
            failed_time_utc8=None,
            created_time_utc8=convert_timestamp_to_utc8_string(1640995200000),
        )

        # 驗證基本欄位
        assert record.transaction_id == "txn-123"
        assert record.platform == "IOS"
        assert record.status == "SENT"
        assert record.ap_id == "mobile-app-001"
        assert record.sns_id == "sns-12345"

        # 驗證 UTC+8 時間轉換
        assert record.send_time_utc8 == "2022-01-01 08:00:00 UTC+8"
        assert record.delivered_time_utc8 is None
        assert record.failed_time_utc8 is None
        assert record.created_time_utc8 == "2022-01-01 08:00:00 UTC+8"


@pytest.mark.unit
class TestTransactionQuery:
    """交易查詢端點測試"""

    @patch("eks_handler.main.InternalAPIAdapter")
    def test_query_transaction_with_id_success(self, mock_internal_api_adapter_class: Any) -> None:
        """測試指定 transaction_id 的成功查詢"""
        # 設置 InternalAPIAdapter 的 mock
        mock_internal_api_adapter = mock_internal_api_adapter_class.return_value
        mock_internal_api_adapter.invoke_transaction_query = AsyncMock(
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
                        "send_ts": 1640995200000,
                        "ap_id": "mobile-app-001",
                        "created_at": 1640995200000,
                    }
                ],
                "message": "Successfully retrieved notifications for transaction ID: txn-123",
                "query_info": {"transaction_id": "txn-123", "limit": 30, "query_type": "specific"},
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

    @patch("eks_handler.main.InternalAPIAdapter")
    def test_query_recent_transactions_success(self, mock_internal_api_adapter_class: Any) -> None:
        """測試查詢最新記錄的成功場景"""
        # 設置 InternalAPIAdapter 的 mock
        mock_internal_api_adapter = mock_internal_api_adapter_class.return_value
        mock_internal_api_adapter.invoke_transaction_query = AsyncMock(
            return_value={
                "success": True,
                "items": [
                    {
                        "transaction_id": "txn-latest-1",
                        "token": "device-token-1",
                        "platform": "IOS",
                        "notification_title": "最新通知1",
                        "notification_body": "最新通知內容1",
                        "status": "SENT",
                        "send_ts": 1640995300000,
                        "ap_id": "mobile-app-001",
                        "created_at": 1640995300000,
                    },
                    {
                        "transaction_id": "txn-latest-2",
                        "token": "device-token-2",
                        "platform": "ANDROID",
                        "notification_title": "最新通知2",
                        "notification_body": "最新通知內容2",
                        "status": "DELIVERED",
                        "send_ts": 1640995200000,
                        "delivered_ts": 1640995250000,
                        "ap_id": "mobile-app-001",
                        "created_at": 1640995200000,
                    },
                ],
                "message": "Successfully retrieved 2 recent notifications (limit: 30)",
                "query_info": {"transaction_id": None, "limit": 30, "query_type": "recent"},
            }
        )

        # 發送請求（不指定 transaction_id）
        response = client.get("/tx")

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        assert data["data"][0]["transaction_id"] == "txn-latest-1"
        assert data["data"][1]["transaction_id"] == "txn-latest-2"
        assert data["query_info"]["query_type"] == "recent"
        assert data["query_info"]["limit"] == 30

    def test_query_transaction_invalid_input(self) -> None:
        """測試無效輸入"""
        # 空交易ID (對於 POST 端點仍然是必需的)
        response = client.post("/query/transaction", json={"transaction_id": ""})
        assert response.status_code == 422

        # 缺少交易ID (對於 POST 端點仍然是必需的)
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
        mock_internal_api_adapter.invoke_failed_query = AsyncMock(
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
        mock_internal_api_adapter.invoke_failed_query = AsyncMock(
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
class TestSnsQuery:
    """SNS 查詢端點測試"""

    @patch("eks_handler.main.InternalAPIAdapter")
    def test_query_sns_success(self, mock_internal_api_adapter_class: Any) -> None:
        """測試成功查詢 SNS 推播記錄"""
        # 設置 InternalAPIAdapter 的 mock
        mock_internal_api_adapter = mock_internal_api_adapter_class.return_value
        mock_internal_api_adapter.invoke_sns_query = AsyncMock(
            return_value={
                "success": True,
                "items": [
                    {
                        "transaction_id": "txn-sns-123",
                        "token": "device-token-sns",
                        "platform": "IOS",
                        "notification_title": "SNS 推播",
                        "notification_body": "這是 SNS 推播內容",
                        "status": "SENT",
                        "send_ts": 1640995200,
                        "ap_id": "mobile-app-001",
                        "created_at": 1640995200,
                        "sns_id": "sns-12345",
                    }
                ],
            }
        )

        # 發送請求
        response = client.post("/query/sns", json={"sns_id": "sns-12345"})

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["transaction_id"] == "txn-sns-123"
        assert data["data"][0]["sns_id"] == "sns-12345"

    def test_query_sns_invalid_input(self) -> None:
        """測試無效輸入"""
        # 空 SNS ID
        response = client.post("/query/sns", json={"sns_id": ""})
        assert response.status_code == 422

        # 缺少 SNS ID
        response = client.post("/query/sns", json={})
        assert response.status_code == 422

    def test_sns_query_request_valid(self) -> None:
        """測試有效的 SNS 查詢請求"""
        request = SnsQueryRequest(sns_id="sns-001")
        assert request.sns_id == "sns-001"

    @patch("eks_handler.main.InternalAPIAdapter")
    def test_get_sns_endpoint(self, mock_internal_api_adapter_class: Any) -> None:
        """測試 GET SNS 端點"""
        # 設置 InternalAPIAdapter 的 mock
        mock_internal_api_adapter = mock_internal_api_adapter_class.return_value
        mock_internal_api_adapter.invoke_sns_query = AsyncMock(
            return_value={
                "success": True,
                "items": [
                    {
                        "transaction_id": "txn-sns-456",
                        "token": "device-token-sns-get",
                        "platform": "ANDROID",
                        "notification_title": "GET SNS 推播",
                        "notification_body": "這是通過 GET 查詢的 SNS 推播",
                        "status": "DELIVERED",
                        "send_ts": 1640995200,
                        "delivered_ts": 1640995210,
                        "ap_id": "mobile-app-002",
                        "created_at": 1640995200,
                        "sns_id": "sns-get-456",
                    }
                ],
            }
        )

        # 發送 GET 請求
        response = client.get("/sns?sns_id=sns-get-456")

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["sns_id"] == "sns-get-456"

    @patch("eks_handler.main.InternalAPIAdapter")
    def test_query_sns_empty_result(self, mock_internal_api_adapter_class: Any) -> None:
        """測試 SNS 查詢無結果的情況"""
        # 設置 InternalAPIAdapter 的 mock 返回空結果
        mock_internal_api_adapter = mock_internal_api_adapter_class.return_value
        mock_internal_api_adapter.invoke_sns_query = AsyncMock(
            return_value={
                "success": False,
                "items": [],
                "message": "No notifications found for SNS ID: sns-empty",
            }
        )

        # 發送請求
        response = client.post("/query/sns", json={"sns_id": "sns-empty"})

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert len(data["data"]) == 0
        assert data["total_count"] == 0
        assert "No notifications found for SNS ID: sns-empty" in data["message"]

    @patch("eks_handler.main.InternalAPIAdapter")
    def test_get_sns_endpoint_empty_result(self, mock_internal_api_adapter_class: Any) -> None:
        """測試 GET SNS 端點無結果的情況"""
        # 設置 InternalAPIAdapter 的 mock 返回空結果
        mock_internal_api_adapter = mock_internal_api_adapter_class.return_value
        mock_internal_api_adapter.invoke_sns_query = AsyncMock(
            return_value={
                "success": False,
                "items": [],
                "message": "No notifications found for SNS ID: sns-404",
            }
        )

        # 發送請求
        response = client.get("/sns?sns_id=sns-404")

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert len(data["data"]) == 0
        assert data["total_count"] == 0
        assert "No notifications found for SNS ID: sns-404" in data["message"]


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
    """QueryService 測試"""

    @pytest.fixture
    def mock_internal_api_adapter(self) -> Mock:
        """創建 mock Internal API Adapter"""
        adapter = Mock(spec=InternalAPIAdapter)
        # 設置所有異步方法為 AsyncMock
        adapter.invoke_transaction_query = AsyncMock()
        adapter.invoke_failed_query = AsyncMock()
        adapter.invoke_sns_query = AsyncMock()
        return adapter

    @pytest.fixture
    def query_service(self, mock_internal_api_adapter: Mock) -> QueryService:
        """創建 QueryService 實例"""
        return QueryService(mock_internal_api_adapter)

    async def test_query_transaction_notifications_success(
        self, query_service: QueryService, mock_internal_api_adapter: Mock
    ) -> None:
        """測試成功查詢交易通知"""
        # 設定模擬回傳值
        mock_internal_api_adapter.invoke_transaction_query.return_value = {
            "success": True,
            "items": [
                {
                    "transaction_id": "txn-001",
                    "token": "device-token-001",
                    "platform": "IOS",
                    "notification_title": "交易通知",
                    "notification_body": "您的交易已成功",
                    "status": "DELIVERED",
                    "send_ts": 1640995200,
                    "delivered_ts": 1640995210,
                    "ap_id": "payment-service",
                    "created_at": 1640995200,
                }
            ],
        }

        # 執行查詢
        result = await query_service.query_transaction_notifications("txn-001")

        # 驗證結果
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0].transaction_id == "txn-001"
        assert result.data[0].status == "DELIVERED"

        # 驗證調用
        mock_internal_api_adapter.invoke_transaction_query.assert_called_once_with(
            {"transaction_id": "txn-001", "limit": 30}
        )

    async def test_query_failed_notifications_success(
        self, query_service: QueryService, mock_internal_api_adapter: Mock
    ) -> None:
        """測試成功查詢失敗通知"""
        # 設定模擬回傳值
        mock_internal_api_adapter.invoke_failed_query.return_value = {
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
                    "retry_cnt": 3,
                }
            ],
        }

        # 執行查詢
        result = await query_service.query_failed_notifications("failed-txn")

        # 驗證結果
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0].transaction_id == "failed-txn"
        assert result.data[0].status == "FAILED"

        # 驗證調用
        mock_internal_api_adapter.invoke_failed_query.assert_called_once_with(
            {"transaction_id": "failed-txn"}
        )

    async def test_query_notifications_failure(
        self, query_service: QueryService, mock_internal_api_adapter: Mock
    ) -> None:
        """測試通知查詢失敗"""
        # 設定模擬回傳失敗結果
        mock_internal_api_adapter.invoke_transaction_query.return_value = {
            "success": False,
            "message": "Query failed",
        }

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
        mock_internal_api_adapter.invoke_transaction_query.side_effect = HTTPException(
            status_code=404, detail="Not found"
        )

        # 驗證異常被正確傳播
        with pytest.raises(HTTPException) as exc_info:
            await query_service.query_transaction_notifications("test-txn")

        assert exc_info.value.status_code == 500
        assert "查詢服務錯誤:" in exc_info.value.detail

    async def test_general_exception_handling(
        self, query_service: QueryService, mock_internal_api_adapter: Mock
    ) -> None:
        """測試一般異常處理"""
        # 設定模擬拋出一般異常
        mock_internal_api_adapter.invoke_transaction_query.side_effect = Exception("Network error")

        # 驗證異常被包裝為 HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await query_service.query_transaction_notifications("test-txn")

        assert exc_info.value.status_code == 500
        assert "查詢服務錯誤:" in exc_info.value.detail


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
        with pytest.raises(ValueError) as exc_info:
            await adapter.invoke_query_api("invalid_type", {"test": "data"})

        assert "Unsupported query type: invalid_type" in str(exc_info.value)

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

    async def test_process_notification_records_failure_response(
        self, service: QueryService
    ) -> None:
        """測試處理推播記錄的失敗情況"""
        # 測試空項目列表
        items: List[Dict[str, Any]] = []
        processed = await service._process_notification_records(items)

        assert len(processed) == 0

    async def test_process_notification_records_invalid_item(self, service: QueryService) -> None:
        """測試處理包含無效項目的推播記錄"""
        items: List[Dict[str, Any]] = [
            {
                "transaction_id": "valid-1",
                "platform": "IOS",
                "notification_title": "Valid",
                "notification_body": "Valid body",
                "status": "DELIVERED",
                "created_at": 1640995200,
            },
            {
                # 缺少部分字段的項目，會使用默認值
                "transaction_id": "invalid-1",
                "created_at": 0,  # 添加必需的 created_at
            },
        ]

        processed = await service._process_notification_records(items)

        # 實際上兩個項目都會被處理，第二個會使用默認值
        assert len(processed) == 2
        assert processed[0].transaction_id == "valid-1"
        assert processed[1].transaction_id == "invalid-1"


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
        assert "查詢服務錯誤:" in response.json()["detail"]

    @patch("eks_handler.main.InternalAPIAdapter")
    def test_get_transaction_endpoint_unexpected_error(self, mock_adapter_class: Any) -> None:
        """測試 GET 交易端點意外錯誤"""
        mock_adapter = mock_adapter_class.return_value
        mock_adapter.invoke_query_api = AsyncMock(side_effect=RuntimeError("Unexpected error"))

        response = client.get("/tx?transaction_id=test-txn")

        assert response.status_code == 500
        # 檢查是否包含錯誤相關訊息
        detail = response.json()["detail"]
        assert "查詢服務錯誤:" in detail

    @patch("eks_handler.main.InternalAPIAdapter")
    def test_fail_endpoint_unexpected_error(self, mock_adapter_class: Any) -> None:
        """測試失敗端點意外錯誤"""
        mock_adapter = mock_adapter_class.return_value
        mock_adapter.invoke_query_api = AsyncMock(side_effect=RuntimeError("Unexpected error"))

        response = client.post("/query/fail", json={"transaction_id": "test-txn"})

        assert response.status_code == 500
        # 檢查是否包含錯誤相關訊息
        detail = response.json()["detail"]
        assert "查詢服務錯誤:" in detail

    @patch("eks_handler.main.InternalAPIAdapter")
    def test_get_fail_endpoint_unexpected_error(self, mock_adapter_class: Any) -> None:
        """測試 GET 失敗端點意外錯誤"""
        mock_adapter = mock_adapter_class.return_value
        mock_adapter.invoke_query_api = AsyncMock(side_effect=RuntimeError("Unexpected error"))

        response = client.get("/fail?transaction_id=test-txn")

        assert response.status_code == 500
        # 檢查是否包含錯誤相關訊息
        detail = response.json()["detail"]
        assert "查詢服務錯誤:" in detail

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
        adapter = Mock(spec=InternalAPIAdapter)
        adapter.invoke_failed_query = AsyncMock()
        return adapter

    @pytest.fixture
    def query_service(self, mock_internal_api_adapter: Mock) -> QueryService:
        """建立測試用的 QueryService 實例"""
        return QueryService(mock_internal_api_adapter)

    async def test_query_failed_notifications_empty_transaction_id(
        self, query_service: QueryService, mock_internal_api_adapter: Mock
    ) -> None:
        """測試查詢失敗通知時傳入空字符串的 transaction_id"""
        mock_internal_api_adapter.invoke_failed_query.return_value = {"success": True, "items": []}

        # 傳入空字符串
        result = await query_service.query_failed_notifications("   ")

        # 應該調用時不包含 transaction_id（因為被 strip() 後為空）
        mock_internal_api_adapter.invoke_failed_query.assert_called_once_with({})
        assert result.success is True

    async def test_query_failed_notifications_none_transaction_id(
        self, query_service: QueryService, mock_internal_api_adapter: Mock
    ) -> None:
        """測試查詢失敗通知時傳入 None 的 transaction_id"""
        mock_internal_api_adapter.invoke_failed_query.return_value = {"success": True, "items": []}

        # 傳入 None
        result = await query_service.query_failed_notifications(None)

        # 應該調用時不包含 transaction_id
        mock_internal_api_adapter.invoke_failed_query.assert_called_once_with({})
        assert result.success is True

    async def test_query_failed_notifications_exception_without_transaction_id(
        self, query_service: QueryService, mock_internal_api_adapter: Mock
    ) -> None:
        """測試查詢失敗通知時發生異常但沒有 transaction_id"""
        mock_internal_api_adapter.invoke_failed_query.side_effect = Exception("Service unavailable")

        with pytest.raises(HTTPException) as exc_info:
            await query_service.query_failed_notifications()

        assert exc_info.value.status_code == 500
        assert "查詢服務錯誤:" in exc_info.value.detail


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
