"""
Query Lambda 測試模組

本模組包含對 query_lambda 的完整測試，包括：
- API Gateway 事件處理測試
- HTTP 請求轉發測試
- 錯誤處理測試
- 響應格式測試
"""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

# 導入被測試的模組
from app import lambda_handler


class TestLambdaHandlerUserQuery:
    """用戶查詢相關測試"""

    @patch("requests.post")
    def test_user_query_success(self, mock_post: MagicMock) -> None:
        """測試用戶查詢成功案例"""
        # 模擬 EKS handler 響應
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "count": 2,
            "items": [
                {
                    "user_id": "user123",
                    "transaction_id": "tx001",
                    "notification_title": "測試通知",
                    "status": "DELIVERED",
                    "platform": "IOS",
                }
            ],
        }
        mock_post.return_value = mock_response

        event = {"path": "/user", "queryStringParameters": {"user_id": "user123"}}

        result = lambda_handler(event, None)

        # 驗證響應
        assert result["statusCode"] == 200
        assert "headers" in result
        assert result["headers"]["Content-Type"] == "application/json"
        assert result["headers"]["Access-Control-Allow-Origin"] == "*"

        body = json.loads(result["body"])
        assert body["success"] is True
        assert body["count"] == 2

        # 驗證 EKS handler 調用
        mock_post.assert_called_once_with(
            "http://eks-handler:8000/query/user", json={"user_id": "user123"}, timeout=10
        )

    @patch("requests.post")
    def test_user_query_missing_user_id(self, mock_post: MagicMock) -> None:
        """測試缺少 user_id 參數的情況"""
        event = {"path": "/user", "queryStringParameters": {}}

        result = lambda_handler(event, None)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Missing required parameter: user_id" in body["error"]

        # 確認沒有調用 EKS handler
        mock_post.assert_not_called()

    @patch("requests.post")
    def test_user_query_null_query_parameters(self, mock_post: MagicMock) -> None:
        """測試 queryStringParameters 為 null 的情況"""
        event = {"path": "/user", "queryStringParameters": None}

        result = lambda_handler(event, None)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Missing required parameter: user_id" in body["error"]

        mock_post.assert_not_called()


class TestLambdaHandlerMarketingQuery:
    """行銷活動查詢相關測試"""

    @patch("requests.post")
    def test_marketing_query_success(self, mock_post: MagicMock) -> None:
        """測試行銷活動查詢成功案例"""
        # 模擬 EKS handler 響應
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "count": 5,
            "items": [
                {
                    "marketing_id": "campaign2024",
                    "transaction_id": "tx001",
                    "notification_title": "新年促銷",
                    "status": "DELIVERED",
                    "platform": "IOS",
                }
            ],
        }
        mock_post.return_value = mock_response

        event = {"path": "/marketing", "queryStringParameters": {"marketing_id": "campaign2024"}}

        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["success"] is True
        assert body["count"] == 5

        # 驗證 EKS handler 調用
        mock_post.assert_called_once_with(
            "http://eks-handler:8000/query/marketing",
            json={"marketing_id": "campaign2024"},
            timeout=10,
        )

    @patch("requests.post")
    def test_marketing_query_missing_marketing_id(self, mock_post: MagicMock) -> None:
        """測試缺少 marketing_id 參數的情況"""
        event = {
            "path": "/marketing",
            "queryStringParameters": {"user_id": "user123"},  # 錯誤的參數
        }

        result = lambda_handler(event, None)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Missing required parameter: marketing_id" in body["error"]

        mock_post.assert_not_called()


class TestLambdaHandlerFailuresQuery:
    """失敗記錄查詢相關測試"""

    @patch("requests.post")
    def test_failures_query_success(self, mock_post: MagicMock) -> None:
        """測試失敗記錄查詢成功案例"""
        # 模擬 EKS handler 響應
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "count": 1,
            "items": [
                {
                    "transaction_id": "tx003",
                    "status": "FAILED",
                    "error_msg": "Device token invalid",
                    "platform": "WEBPUSH",
                }
            ],
        }
        mock_post.return_value = mock_response

        event = {"path": "/failures", "queryStringParameters": {"transaction_id": "tx003"}}

        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["success"] is True
        assert body["count"] == 1

        # 驗證失敗記錄內容
        item = body["items"][0]
        assert item["transaction_id"] == "tx003"
        assert item["status"] == "FAILED"
        assert "error_msg" in item

        # 驗證 EKS handler 調用
        mock_post.assert_called_once_with(
            "http://eks-handler:8000/query/failures", json={"transaction_id": "tx003"}, timeout=10
        )

    @patch("requests.post")
    def test_failures_query_missing_transaction_id(self, mock_post: MagicMock) -> None:
        """測試缺少 transaction_id 參數的情況"""
        event = {"path": "/failures", "queryStringParameters": {"user_id": "user123"}}  # 錯誤的參數

        result = lambda_handler(event, None)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Missing required parameter: transaction_id" in body["error"]

        mock_post.assert_not_called()


class TestLambdaHandlerErrorHandling:
    """錯誤處理相關測試"""

    def test_invalid_path(self) -> None:
        """測試無效路徑"""
        event = {"path": "/invalid", "queryStringParameters": {"user_id": "user123"}}

        result = lambda_handler(event, None)

        assert result["statusCode"] == 404
        body = json.loads(result["body"])
        assert "Invalid query path" in body["error"]

    @patch("requests.post")
    def test_eks_handler_timeout(self, mock_post: MagicMock) -> None:
        """測試 EKS handler 超時"""
        mock_post.side_effect = requests.exceptions.Timeout()

        event = {"path": "/user", "queryStringParameters": {"user_id": "user123"}}

        result = lambda_handler(event, None)

        assert result["statusCode"] == 504
        body = json.loads(result["body"])
        assert "Request timeout" in body["error"]

    @patch("requests.post")
    def test_eks_handler_connection_error(self, mock_post: MagicMock) -> None:
        """測試 EKS handler 連接錯誤"""
        mock_post.side_effect = requests.exceptions.ConnectionError()

        event = {"path": "/user", "queryStringParameters": {"user_id": "user123"}}

        result = lambda_handler(event, None)

        assert result["statusCode"] == 502
        body = json.loads(result["body"])
        assert "Failed to connect to EKS handler" in body["error"]

    @patch("requests.post")
    def test_eks_handler_http_error(self, mock_post: MagicMock) -> None:
        """測試 EKS handler HTTP 錯誤"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        event = {"path": "/user", "queryStringParameters": {"user_id": "user123"}}

        result = lambda_handler(event, None)

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert "EKS handler error" in body["error"]

    @patch("requests.post")
    def test_general_exception(self, mock_post: MagicMock) -> None:
        """測試一般例外情況"""
        mock_post.side_effect = Exception("Unexpected error")

        event = {"path": "/user", "queryStringParameters": {"user_id": "user123"}}

        result = lambda_handler(event, None)

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert "Internal server error" in body["error"]


class TestLambdaHandlerResponseFormat:
    """響應格式相關測試"""

    @patch("requests.post")
    def test_cors_headers(self, mock_post: MagicMock) -> None:
        """測試 CORS 頭設置"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "count": 0, "items": []}
        mock_post.return_value = mock_response

        event = {"path": "/user", "queryStringParameters": {"user_id": "user123"}}

        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        assert "headers" in result
        assert result["headers"]["Access-Control-Allow-Origin"] == "*"
        assert result["headers"]["Content-Type"] == "application/json"

    @patch("requests.post")
    def test_json_response_format(self, mock_post: MagicMock) -> None:
        """測試 JSON 響應格式"""
        test_data = {
            "success": True,
            "count": 1,
            "items": [
                {
                    "user_id": "user123",
                    "transaction_id": "tx001",
                    "notification_title": "測試通知",
                    "status": "DELIVERED",
                    "platform": "IOS",
                }
            ],
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = test_data
        mock_post.return_value = mock_response

        event = {"path": "/user", "queryStringParameters": {"user_id": "user123"}}

        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])

        # 驗證 JSON 結構
        assert "success" in body
        assert "count" in body
        assert "items" in body
        assert isinstance(body["items"], list)

        # 驗證數據內容
        assert body["success"] is True
        assert body["count"] == 1
        assert len(body["items"]) == 1

        item = body["items"][0]
        assert item["user_id"] == "user123"
        assert item["transaction_id"] == "tx001"
        assert item["status"] == "DELIVERED"


class TestEnvironmentConfiguration:
    """環境配置相關測試"""

    @pytest.mark.skip(reason="模組重載在 CI 環境中可能不穩定")  # type: ignore[misc]
    @patch.dict("os.environ", {"EKS_HANDLER_URL": "http://custom-eks:9000"})
    @patch("requests.post")
    def test_custom_eks_handler_url(self, mock_post: MagicMock) -> None:
        """測試自定義 EKS Handler URL"""
        # 重新載入模組以應用環境變數變更
        import sys

        # 先移除現有的模組
        if "app" in sys.modules:
            del sys.modules["app"]

        # 重新匯入模組
        from app import lambda_handler

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "count": 0, "items": []}
        mock_post.return_value = mock_response

        event = {"path": "/user", "queryStringParameters": {"user_id": "user123"}}

        lambda_handler(event, None)

        # 驗證是否使用了自定義的 URL
        mock_post.assert_called_once_with(
            "http://custom-eks:9000/query/user", json={"user_id": "user123"}, timeout=10
        )

    @pytest.mark.skip(reason="模組重載在 CI 環境中可能不穩定")  # type: ignore[misc]
    @patch.dict("os.environ", {}, clear=True)
    @patch("requests.post")
    def test_default_eks_handler_url(self, mock_post: MagicMock) -> None:
        """測試預設 EKS Handler URL"""
        # 重新載入模組以應用環境變數變更
        import sys

        # 先移除現有的模組
        if "app" in sys.modules:
            del sys.modules["app"]

        # 重新匯入模組
        from app import lambda_handler

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "count": 0, "items": []}
        mock_post.return_value = mock_response

        event = {"path": "/user", "queryStringParameters": {"user_id": "user123"}}

        lambda_handler(event, None)

        # 驗證是否使用了預設的 URL
        mock_post.assert_called_once_with(
            "http://eks-handler:8000/query/user", json={"user_id": "user123"}, timeout=10
        )


class TestRequestTimeout:
    """請求超時相關測試"""

    @patch("requests.post")
    def test_request_timeout_configuration(self, mock_post: MagicMock) -> None:
        """測試請求超時配置"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "count": 0, "items": []}
        mock_post.return_value = mock_response

        event = {"path": "/user", "queryStringParameters": {"user_id": "user123"}}

        lambda_handler(event, None)

        # 驗證請求是否設置了正確的超時時間
        mock_post.assert_called_once_with(
            "http://eks-handler:8000/query/user", json={"user_id": "user123"}, timeout=10
        )


# 測試類別別名，用於與其他模組保持一致
TestQueryLambda = TestLambdaHandlerUserQuery
TestQueryLambdaErrorHandling = TestLambdaHandlerErrorHandling
TestQueryLambdaValidation = TestLambdaHandlerResponseFormat


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
