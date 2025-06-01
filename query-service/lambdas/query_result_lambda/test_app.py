"""
Query Result Lambda 測試模組

本模組包含對 query_result_lambda 的完整測試，包括：
- DynamoDB 查詢操作測試
- 不同查詢類型測試
- 錯誤處理測試
- 響應格式測試
"""

import json
import os
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_dynamodb

# 設置測試環境變數
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"  # pragma: allowlist secret
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"  # pragma: allowlist secret

# 確保從當前目錄導入正確的 app 模組
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

# 確保當前目錄在 sys.path 的最前面
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path or sys.path.index(str(current_dir)) != 0:
    sys.path.insert(0, str(current_dir))

# 使用絕對導入確保導入正確的模組
import importlib.util  # noqa: E402

app_path = current_dir / "app.py"
spec = importlib.util.spec_from_file_location("query_result_app", app_path)
if spec is None:
    raise ImportError(f"Cannot load module from {app_path}")
app_module = importlib.util.module_from_spec(spec)
if spec.loader is None:
    raise ImportError(f"Cannot get loader for module from {app_path}")
spec.loader.exec_module(app_module)

# 提取需要的函數
decimal_to_int = app_module.decimal_to_int
lambda_handler = app_module.lambda_handler

# 設置全局變數供測試使用
import builtins  # noqa: E402

builtins.query_result_app_module = app_module  # type: ignore[attr-defined]


class TestDecimalToInt:  # noqa: E402
    """Decimal 轉換函數測試"""

    def test_decimal_to_int_conversion(self) -> None:
        """測試 Decimal 轉 int"""
        result = decimal_to_int(Decimal("123"))
        assert result == 123
        assert isinstance(result, int)

    def test_decimal_to_int_raises_type_error(self) -> None:
        """測試非 Decimal 類型拋出 TypeError"""
        with pytest.raises(TypeError):
            decimal_to_int("not_a_decimal")


@mock_dynamodb  # noqa: E402
class TestUserQueryIntegration:
    """用戶查詢整合測試"""

    def setup_method(self, method: Any) -> None:
        """設置測試方法"""
        # 創建 DynamoDB 資源
        self.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        # 創建 notification-records 表
        self.table = self.dynamodb.create_table(
            TableName="notification-records",
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
                    "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
                },
                {
                    "IndexName": "transaction_id-status-index",
                    "KeySchema": [
                        {"AttributeName": "transaction_id", "KeyType": "HASH"},
                        {"AttributeName": "status", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
                },
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )

        # 插入測試數據
        self._insert_test_data()

    def _insert_test_data(self) -> None:
        """插入測試數據"""
        test_items = [
            {
                "user_id": "user123",
                "created_at": 1704038400000,
                "transaction_id": "tx001",
                "marketing_id": "campaign2024",
                "notification_title": "新年促銷",
                "status": "DELIVERED",
                "platform": "IOS",
            },
            {
                "user_id": "user123",
                "created_at": 1704038500000,
                "transaction_id": "tx002",
                "marketing_id": "campaign2024",
                "notification_title": "限時優惠",
                "status": "SENT",
                "platform": "ANDROID",
            },
            {
                "user_id": "user456",
                "created_at": 1704038600000,
                "transaction_id": "tx003",
                "marketing_id": "campaign2025",
                "notification_title": "春節活動",
                "status": "FAILED",
                "platform": "WEBPUSH",
                "error_msg": "Device token invalid",
            },
        ]

        for item in test_items:
            self.table.put_item(Item=item)

    def test_user_query_success(self) -> None:
        """測試用戶查詢成功案例"""
        event = {"query_type": "user", "user_id": "user123"}

        # 嘗試獲取正確的模組引用
        import builtins

        if hasattr(builtins, "query_result_app_module"):
            app_module = builtins.query_result_app_module
            with patch.object(app_module, "dynamodb") as mock_dynamodb:
                mock_dynamodb.Table.return_value = self.table
                result = lambda_handler(event, None)
        else:
            with patch("app.dynamodb.Table", return_value=self.table):
                result = lambda_handler(event, None)

        assert result["statusCode"] == 200

        body = json.loads(result["body"])
        assert body["success"] is True
        assert body["count"] == 2
        assert len(body["items"]) == 2

        # 檢查第一筆記錄（應該是最新的）
        first_item = body["items"][0]
        assert first_item["user_id"] == "user123"
        assert first_item["transaction_id"] == "tx002"
        assert first_item["created_at"] == 1704038500000

    def test_marketing_query_success(self) -> None:
        """測試行銷活動查詢成功案例"""
        event = {"query_type": "marketing", "marketing_id": "campaign2024"}

        # 嘗試獲取正確的模組引用
        import builtins

        if hasattr(builtins, "query_result_app_module"):
            app_module = builtins.query_result_app_module
            with patch.object(app_module, "dynamodb") as mock_dynamodb:
                mock_dynamodb.Table.return_value = self.table
                result = lambda_handler(event, None)
        else:
            with patch("app.dynamodb.Table", return_value=self.table):
                result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["success"] is True
        assert body["count"] == 2

    def test_failures_query_success(self) -> None:
        """測試失敗記錄查詢成功案例"""
        event = {"query_type": "failures", "transaction_id": "tx003"}

        # 嘗試獲取正確的模組引用
        import builtins

        if hasattr(builtins, "query_result_app_module"):
            app_module = builtins.query_result_app_module
            with patch.object(app_module, "dynamodb") as mock_dynamodb:
                mock_dynamodb.Table.return_value = self.table
                result = lambda_handler(event, None)
        else:
            with patch("app.dynamodb.Table", return_value=self.table):
                result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["success"] is True
        assert body["count"] == 1

        # 檢查失敗記錄
        item = body["items"][0]
        assert item["transaction_id"] == "tx003"
        assert item["status"] == "FAILED"
        assert "error_msg" in item
        assert item["error_msg"] == "Device token invalid"


class TestErrorHandling:  # noqa: E402
    """錯誤處理相關測試"""

    def test_missing_user_id(self) -> None:
        """測試缺少 user_id 參數的情況"""
        event = {"query_type": "user"}

        result = lambda_handler(event, None)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Missing user_id" in body["error"]

    def test_invalid_query_type(self) -> None:
        """測試無效的查詢類型"""
        event = {"query_type": "invalid_type"}

        result = lambda_handler(event, None)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Invalid query_type" in body["error"]

    def test_invalid_api_gateway_path(self) -> None:
        """測試無效的 API Gateway 路徑"""
        event = {"path": "/invalid/path", "queryStringParameters": {}}

        result = lambda_handler(event, None)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Invalid path" in body["error"]


class TestResponseFormat:  # noqa: E402
    """響應格式測試"""

    def test_response_headers(self) -> None:
        """測試響應頭格式"""
        event = {"query_type": "user", "user_id": "user123"}

        # 嘗試獲取正確的模組引用
        import builtins

        if hasattr(builtins, "query_result_app_module"):
            app_module = builtins.query_result_app_module
            with patch.object(app_module, "dynamodb") as mock_dynamodb:
                mock_table_instance = MagicMock()
                mock_table_instance.query.return_value = {"Items": []}
                mock_dynamodb.Table.return_value = mock_table_instance
                result = lambda_handler(event, None)
        else:
            with patch("app.dynamodb.Table") as mock_table:
                mock_table_instance = MagicMock()
                mock_table_instance.query.return_value = {"Items": []}
                mock_table.return_value = mock_table_instance
                result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        assert "headers" in result
        assert result["headers"]["Content-Type"] == "application/json"

    def test_decimal_serialization(self) -> None:
        """測試 Decimal 類型的序列化"""
        # 嘗試獲取正確的模組引用
        import builtins

        if hasattr(builtins, "query_result_app_module"):
            app_module = builtins.query_result_app_module
            with patch.object(app_module, "dynamodb") as mock_dynamodb:
                mock_table_instance = MagicMock()
                mock_table_instance.query.return_value = {
                    "Items": [
                        {
                            "user_id": "user123",
                            "created_at": Decimal("1704038400000"),
                            "transaction_id": "tx001",
                            "marketing_id": "campaign2024",
                            "notification_title": "測試通知",
                            "status": "DELIVERED",
                            "platform": "IOS",
                        }
                    ]
                }
                mock_dynamodb.Table.return_value = mock_table_instance
                event = {"query_type": "user", "user_id": "user123"}
                result = lambda_handler(event, None)
        else:
            with patch("app.dynamodb.Table") as mock_table:
                mock_table_instance = MagicMock()
                mock_table_instance.query.return_value = {
                    "Items": [
                        {
                            "user_id": "user123",
                            "created_at": Decimal("1704038400000"),
                            "transaction_id": "tx001",
                            "marketing_id": "campaign2024",
                            "notification_title": "測試通知",
                            "status": "DELIVERED",
                            "platform": "IOS",
                        }
                    ]
                }
                mock_table.return_value = mock_table_instance
                event = {"query_type": "user", "user_id": "user123"}
                result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])

        # 檢查 Decimal 是否正確轉換為 int
        assert isinstance(body["items"][0]["created_at"], int)
        assert body["items"][0]["created_at"] == 1704038400000


# 為了與其他測試模組保持一致，提供測試類別別名
TestQueryResultLambda = TestUserQueryIntegration
TestQueryResultLambdaErrorHandling = TestErrorHandling
TestQueryResultLambdaValidation = TestResponseFormat


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v"])
