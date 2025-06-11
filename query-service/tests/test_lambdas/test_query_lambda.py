"""
Query Lambda 測試

測試使用 aws-lambda-powertools 的 query_lambda
"""

import os
import sys
import unittest
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

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
    path: str = "/tx", query_params: Dict[str, str] | None = None
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
        self.service = app.EKSHandlerService("http://test:8000", 5)

    def test_eks_handler_service_initialization(self) -> None:
        """測試 EKS Handler 服務初始化"""
        service = app.EKSHandlerService("http://test:8000", 10)
        self.assertEqual(service.base_url, "http://test:8000")
        self.assertEqual(service.timeout, 10)

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

        # 測試交易查詢
        self.service.query_transaction_notifications("user123")
        mock_post.assert_called_with(
            "http://test:8000/query/transaction", json={"transaction_id": "user123"}, timeout=5
        )

        # 重置 mock
        mock_post.reset_mock()

        # 測試失敗查詢
        self.service.query_failed_notifications("tx123")
        mock_post.assert_called_with(
            "http://test:8000/query/fail",
            json={"transaction_id": "tx123"},
            timeout=5,
        )


if __name__ == "__main__":
    unittest.main()
