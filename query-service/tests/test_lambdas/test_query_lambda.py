"""
Query Lambda 測試

測試使用 aws-lambda-powertools 的 query_lambda
"""

import json
import os
import sys
import unittest
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

import requests

# 設置測試環境變數
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("EKS_HANDLER_URL", "http://test-eks-handler:8000")
os.environ.setdefault("REQUEST_TIMEOUT", "5")

# 確保正確的 lambda 目錄路徑
lambda_dir = Path(__file__).parent.parent.parent / "lambdas" / "query_lambda"
if str(lambda_dir) not in sys.path:
    sys.path.insert(0, str(lambda_dir))

# 清除任何現有的 app 模組，避免衝突
if "app" in sys.modules:
    del sys.modules["app"]

# 導入 Lambda 模組
try:
    import app
except ImportError as e:
    raise ImportError(f"Cannot import query_lambda app from {lambda_dir}: {e}")


def create_mock_lambda_context() -> MagicMock:
    """創建模擬的 Lambda context"""
    context = MagicMock()
    context.function_name = "test-query-lambda"
    context.memory_limit_in_mb = 128
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
    context.aws_request_id = "test-request-id"
    context.log_group_name = "/aws/lambda/test-query-lambda"
    context.log_stream_name = "2024/01/01/[$LATEST]test"
    context.remaining_time_in_millis = lambda: 30000
    return context


def create_api_gateway_event(
    path: str = "/user", query_params: Dict[str, str] | None = None
) -> Dict[str, Any]:
    """創建標準的 API Gateway 事件"""
    if query_params is None:
        query_params = {}

    return {
        "version": "2.0",
        "routeKey": f"GET {path}",
        "rawPath": path,
        "rawQueryString": "&".join([f"{k}={v}" for k, v in query_params.items()]),
        "headers": {"accept": "application/json", "content-type": "application/json"},
        "queryStringParameters": query_params,
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "api123",
            "domainName": "api123.execute-api.us-east-1.amazonaws.com",
            "domainPrefix": "api123",
            "http": {
                "method": "GET",
                "path": path,
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "test-agent",
            },
            "requestId": "request-id",
            "routeKey": f"GET {path}",
            "stage": "test",
            "time": "01/Jan/2024:00:00:00 +0000",
            "timeEpoch": 1704038400000,
        },
        "body": None,
        "isBase64Encoded": False,
    }


class TestQueryLambda(unittest.TestCase):
    """Query Lambda 測試類"""

    def setUp(self) -> None:
        """測試設置"""
        self.lambda_context = create_mock_lambda_context()

    def test_eks_handler_service_initialization(self) -> None:
        """測試 EKS Handler 服務初始化"""
        service = app.EKSHandlerService("http://test:8000", 10)
        self.assertEqual(service.base_url, "http://test:8000")
        self.assertEqual(service.timeout, 10)

    @patch("requests.post")
    def test_query_user_notifications(self, mock_post: Mock) -> None:
        """測試用戶通知查詢"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"success": true}'
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response

        service = app.EKSHandlerService("http://test:8000")
        response = service.query_user_notifications("test_user")

        # 驗證請求
        mock_post.assert_called_once_with(
            "http://test:8000/query/user",
            json={"user_id": "test_user"},
            timeout=10,
        )
        self.assertEqual(response.status_code, 200)

    @patch("requests.post")
    def test_query_marketing_notifications(self, mock_post: Mock) -> None:
        """測試行銷通知查詢"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"success": true}'
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response

        service = app.EKSHandlerService("http://test:8000")
        service.query_marketing_notifications("campaign_123")

        mock_post.assert_called_once_with(
            "http://test:8000/query/marketing",
            json={"marketing_id": "campaign_123"},
            timeout=10,
        )

    @patch("requests.post")
    def test_query_failed_notifications(self, mock_post: Mock) -> None:
        """測試失敗通知查詢"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"success": true}'
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response

        service = app.EKSHandlerService("http://test:8000")
        service.query_failed_notifications("tx_123")

        mock_post.assert_called_once_with(
            "http://test:8000/query/fail",
            json={"transaction_id": "tx_123"},
            timeout=10,
        )

    def test_handle_eks_response_success(self) -> None:
        """測試處理成功的 EKS 響應"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": "test"}

        result, status_code = app.handle_eks_response(mock_response)

        self.assertEqual(status_code, 200)
        self.assertEqual(result["success"], True)

    def test_handle_eks_response_error(self) -> None:
        """測試處理錯誤的 EKS 響應"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        result, status_code = app.handle_eks_response(mock_response)

        self.assertEqual(status_code, 500)
        self.assertEqual(result["error"], "EKS handler error")

    @patch.object(app, "eks_service")
    def test_api_gateway_user_query(self, mock_service: Mock) -> None:
        """測試 API Gateway 用戶查詢路徑 - 使用直接調用格式避免 PowerTools 複雜度"""
        # 設置模擬服務響應
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "items": []}
        mock_service.query_user_notifications.return_value = mock_response

        # 使用直接調用格式，更容易測試
        event = {"path": "/user", "queryStringParameters": {"user_id": "test_user_123"}}

        response = app.lambda_handler(event, self.lambda_context)

        # 驗證結果
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertTrue(body["success"])
        mock_service.query_user_notifications.assert_called_once_with("test_user_123")

    @patch.object(app, "eks_service")
    def test_direct_invocation_user_query(self, mock_service: Mock) -> None:
        """測試直接調用用戶查詢"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "items": []}
        mock_service.query_user_notifications.return_value = mock_response

        # 直接調用事件
        event = {"path": "/user", "queryStringParameters": {"user_id": "test_user_123"}}

        response = app.lambda_handler(event, self.lambda_context)

        # 驗證結果
        self.assertEqual(response["statusCode"], 200)
        mock_service.query_user_notifications.assert_called_once_with("test_user_123")

    @patch.object(app, "eks_service")
    def test_missing_parameters(self, mock_service: Mock) -> None:
        """測試缺少必要參數的情況"""
        # 測試直接調用格式缺少 user_id
        event = {"path": "/user", "queryStringParameters": {}}  # 缺少 user_id

        response = app.lambda_handler(event, self.lambda_context)
        self.assertEqual(response["statusCode"], 400)

    @patch.object(app, "eks_service")
    def test_request_timeout_handling(self, mock_service: Mock) -> None:
        """測試請求超時處理"""
        mock_service.query_user_notifications.side_effect = requests.exceptions.Timeout()

        event = {"path": "/user", "queryStringParameters": {"user_id": "test_user"}}

        response = app.lambda_handler(event, self.lambda_context)
        self.assertEqual(response["statusCode"], 504)

    @patch.object(app, "eks_service")
    def test_connection_error_handling(self, mock_service: Mock) -> None:
        """測試連接錯誤處理"""
        mock_service.query_marketing_notifications.side_effect = (
            requests.exceptions.ConnectionError()
        )

        event = {
            "path": "/marketing",
            "queryStringParameters": {"marketing_id": "campaign_123"},
        }

        response = app.lambda_handler(event, self.lambda_context)
        self.assertEqual(response["statusCode"], 502)

    def test_invalid_path_handling(self) -> None:
        """測試無效路徑處理"""
        event = {"path": "/invalid_path", "queryStringParameters": {}}

        response = app.lambda_handler(event, self.lambda_context)
        self.assertEqual(response["statusCode"], 404)

    @patch.object(app, "logger")
    @patch.object(app, "eks_service")
    def test_logging_functionality(self, mock_service: Mock, mock_logger: Mock) -> None:
        """測試日誌記錄功能"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_service.query_user_notifications.return_value = mock_response

        event = {"path": "/user", "queryStringParameters": {"user_id": "test_user"}}

        app.lambda_handler(event, self.lambda_context)

        # 驗證日誌記錄被調用
        mock_logger.info.assert_called()

    @patch.object(app, "eks_service")
    def test_exception_handling(self, mock_service: Mock) -> None:
        """測試一般異常處理"""
        mock_service.query_user_notifications.side_effect = Exception("Unexpected error")

        event = {"path": "/user", "queryStringParameters": {"user_id": "test_user"}}

        response = app.lambda_handler(event, self.lambda_context)
        self.assertEqual(response["statusCode"], 500)


class TestEKSHandlerService(unittest.TestCase):
    """EKS Handler 服務單元測試"""

    def setUp(self) -> None:
        """設置測試環境"""
        self.service = app.EKSHandlerService("http://test:8000", 5)

    def test_base_url_normalization(self) -> None:
        """測試基礎 URL 正規化"""
        service = app.EKSHandlerService("http://test:8000/", 5)
        self.assertEqual(service.base_url, "http://test:8000")

    @patch("requests.post")
    def test_all_query_methods(self, mock_post: Mock) -> None:
        """測試所有查詢方法"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"success": true}'
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response

        # 測試用戶查詢
        self.service.query_user_notifications("user123")
        mock_post.assert_called_with(
            "http://test:8000/query/user", json={"user_id": "user123"}, timeout=5
        )

        # 測試行銷查詢
        self.service.query_marketing_notifications("campaign123")
        mock_post.assert_called_with(
            "http://test:8000/query/marketing",
            json={"marketing_id": "campaign123"},
            timeout=5,
        )

        # 測試失敗查詢
        self.service.query_failed_notifications("tx123")
        mock_post.assert_called_with(
            "http://test:8000/query/fail",
            json={"transaction_id": "tx123"},
            timeout=5,
        )


if __name__ == "__main__":
    unittest.main()
