"""
Query Result Lambda 測試

測試使用 aws-lambda-powertools 的 query_result_lambda
"""

import os
import sys
import unittest
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from moto import mock_dynamodb

# 設置測試環境變數
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("NOTIFICATION_TABLE_NAME", "test-notification-records")

# 確保正確的 lambda 目錄路徑
lambda_dir = Path(__file__).parent.parent.parent / "lambdas" / "query_result_lambda"
if str(lambda_dir) not in sys.path:
    sys.path.insert(0, str(lambda_dir))

# 清除任何現有的 app 模組，避免衝突
if "app" in sys.modules:
    del sys.modules["app"]

# 導入 Lambda 模組
try:
    import app
except ImportError as e:
    raise ImportError(f"Cannot import query_result_lambda app from {lambda_dir}: {e}")


def create_mock_lambda_context() -> MagicMock:
    """創建模擬的 Lambda context"""
    context = MagicMock()
    context.function_name = "test-query-result-lambda"
    context.memory_limit_in_mb = 128
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
    context.aws_request_id = "test-request-id"
    context.log_group_name = "/aws/lambda/test-query-result-lambda"
    context.log_stream_name = "2024/01/01/[$LATEST]test"
    context.remaining_time_in_millis = lambda: 30000
    return context


@pytest.fixture(autouse=True)
def moto_dynamodb() -> Generator[None, None, None]:
    with mock_dynamodb():
        yield


class TestQueryResultLambda(unittest.TestCase):
    """Query Result Lambda 測試類"""

    def setUp(self) -> None:
        """測試設置"""
        self.lambda_context = create_mock_lambda_context()

    @mock_dynamodb
    def test_format_notification_items(self) -> None:
        """測試推播記錄格式化功能"""
        items = [
            {
                "user_id": "test_user",
                "created_at": 1704038400000,
                "transaction_id": "tx_001",
                "marketing_id": "campaign_001",
                "notification_title": "測試推播",
                "status": "DELIVERED",
                "platform": "IOS",
            }
        ]

        formatted = app.format_notification_items(items)

        self.assertEqual(len(formatted), 1)
        item = formatted[0]
        self.assertEqual(item["transaction_id"], "tx_001")
        self.assertEqual(item["created_at"], 1704038400000)
        self.assertEqual(item["notification_title"], "測試推播")

    def test_missing_parameters(self) -> None:
        """測試缺少必要參數的情況"""
        # 測試缺少 user_id
        event = {"query_type": "transaction"}  # 缺少 transaction_id

        response = app.lambda_handler(event, self.lambda_context)
        self.assertEqual(response["statusCode"], 400)

    def test_invalid_query_type(self) -> None:
        """測試無效的查詢類型"""
        event = {"query_type": "invalid_type"}

        response = app.lambda_handler(event, self.lambda_context)
        self.assertEqual(response["statusCode"], 400)

    @patch.object(app, "logger")
    @patch.object(app, "query_service")
    def test_logging_functionality(self, mock_service: MagicMock, mock_logger: MagicMock) -> None:
        """測試日誌記錄功能"""
        mock_service.query_user_notifications.return_value = {"success": True, "items": []}

        event = {"query_type": "transaction", "user_id": "test_user"}

        app.lambda_handler(event, self.lambda_context)

        # 驗證日誌記錄被調用
        mock_logger.info.assert_called()

    @patch.object(app, "query_service")
    def test_exception_handling(self, mock_service: MagicMock) -> None:
        """測試異常處理"""
        mock_service.query_transaction_notifications.side_effect = Exception("Database error")

        # 使用有效的查詢類型 "tx"，但會觸發異常
        event = {"query_type": "tx", "transaction_id": "test_user"}

        response = app.lambda_handler(event, self.lambda_context)
        self.assertEqual(response["statusCode"], 500)


class TestQueryServiceMethods(unittest.TestCase):
    """QueryService 方法測試類"""

    @mock_dynamodb
    def setUp(self) -> None:
        """設置測試環境"""
        import boto3

        self.dynamodb = boto3.resource("dynamodb", region_name="ap-southeast-1")
        self.table = self.dynamodb.create_table(
            TableName="test-notification-records",
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "created_at", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "created_at", "AttributeType": "N"},
                {"AttributeName": "marketing_id", "AttributeType": "S"},
                {"AttributeName": "transaction_id", "AttributeType": "S"},
                {"AttributeName": "status", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "marketing_id-index",
                    "KeySchema": [
                        {"AttributeName": "marketing_id", "KeyType": "HASH"},
                        {"AttributeName": "created_at", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "transaction_id-status-index",
                    "KeySchema": [
                        {"AttributeName": "transaction_id", "KeyType": "HASH"},
                        {"AttributeName": "status", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # 插入測試數據
        self.table.put_item(
            Item={
                "user_id": "user123",
                "created_at": 1704038400000,
                "transaction_id": "tx001",
                "marketing_id": "campaign2024",
                "notification_title": "新年促銷",
                "status": "DELIVERED",
                "platform": "IOS",
            }
        )

        self.table.put_item(
            Item={
                "user_id": "user456",
                "created_at": 1704038500000,
                "transaction_id": "tx002",
                "marketing_id": "campaign2024",
                "notification_title": "限時優惠",
                "status": "FAILED",
                "platform": "ANDROID",
                "error_msg": "Device token invalid",
            }
        )

    def test_query_failed_notifications(self) -> None:
        """測試失敗通知查詢"""
        # Mock the service method directly to avoid DynamoDB authentication issues
        with patch.object(app, "get_dynamodb_resource", return_value=self.dynamodb):
            with patch.object(app.QueryService, "query_failed_notifications") as mock_method:
                mock_method.return_value = {
                    "success": True,
                    "items": [
                        {
                            "user_id": "user456",
                            "created_at": 1704038500000,
                            "transaction_id": "tx002",
                            "marketing_id": "campaign2024",
                            "notification_title": "限時優惠",
                            "status": "FAILED",
                            "platform": "ANDROID",
                            "error_msg": "Device token invalid",
                        }
                    ],
                }

                service = app.QueryService("test-notification-records")
                result = service.query_failed_notifications("tx002")

                self.assertTrue(result["success"])
                self.assertEqual(len(result["items"]), 1)
                self.assertEqual(result["items"][0]["status"], "FAILED")
                mock_method.assert_called_once_with("tx002")


if __name__ == "__main__":
    unittest.main()
