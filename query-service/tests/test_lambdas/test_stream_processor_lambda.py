"""
Stream Processor Lambda 測試

測試使用 aws-lambda-powertools 的 stream_processor_lambda
"""

import json
import os
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

from moto import mock_dynamodb

# 設置測試環境變數
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("NOTIFICATION_TABLE_NAME", "test-notification-records")

# 確保正確的 lambda 目錄路徑
lambda_dir = Path(__file__).parent.parent.parent / "lambdas" / "stream_processor_lambda"
if str(lambda_dir) not in sys.path:
    sys.path.insert(0, str(lambda_dir))

# 清除任何現有的 app 模組，避免衝突
if "app" in sys.modules:
    del sys.modules["app"]

# 導入 Lambda 模組
try:
    import app
except ImportError as e:
    raise ImportError(f"Cannot import stream_processor_lambda app from {lambda_dir}: {e}")


def create_mock_lambda_context() -> MagicMock:
    """創建模擬的 Lambda context"""
    context = MagicMock()
    context.function_name = "test-stream-processor-lambda"
    context.memory_limit_in_mb = 128
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
    context.aws_request_id = "test-request-id"
    context.log_group_name = "/aws/lambda/test-stream-processor-lambda"
    context.log_stream_name = "2024/01/01/[$LATEST]test"
    context.remaining_time_in_millis = lambda: 30000
    return context


class TestStreamProcessorLambda(unittest.TestCase):
    """Stream Processor Lambda 測試類"""

    def setUp(self) -> None:
        """測試設置"""
        self.lambda_context = create_mock_lambda_context()

    def test_notification_status_enum(self) -> None:
        """測試通知狀態枚舉"""
        self.assertEqual(app.NotificationStatus.SENT.value, "SENT")
        self.assertEqual(app.NotificationStatus.DELIVERED.value, "DELIVERED")
        self.assertEqual(app.NotificationStatus.FAILED.value, "FAILED")

    def test_platform_enum(self) -> None:
        """測試平台枚舉"""
        self.assertEqual(app.Platform.IOS.value, "IOS")
        self.assertEqual(app.Platform.ANDROID.value, "ANDROID")
        self.assertEqual(app.Platform.WEBPUSH.value, "WEBPUSH")

    def test_command_record_dataclass(self) -> None:
        """測試命令記錄資料類"""
        record = app.CommandRecord(
            transaction_id="tx_001",
            created_at=1704038400000,
            user_id="test_user",
            notification_title="測試推播",
            status=app.NotificationStatus.DELIVERED,
            platform=app.Platform.IOS,
            marketing_id="campaign_001",
        )

        self.assertEqual(record.transaction_id, "tx_001")
        self.assertEqual(record.user_id, "test_user")
        self.assertEqual(record.status, app.NotificationStatus.DELIVERED)

    def test_query_record_dataclass(self) -> None:
        """測試查詢記錄資料類"""
        record = app.QueryRecord(
            user_id="test_user",
            created_at=1704038400000,
            transaction_id="tx_001",
            notification_title="測試推播",
            status=app.NotificationStatus.DELIVERED,
            platform=app.Platform.IOS,
        )

        self.assertEqual(record.user_id, "test_user")
        self.assertEqual(record.transaction_id, "tx_001")

    def test_dynamodb_value_extractor(self) -> None:
        """測試 DynamoDB 值提取器"""
        extractor = app.DynamoDBValueExtractor()

        # 測試字符串值提取
        string_item = {"field": {"S": "test_value"}}
        result = extractor.extract_value(string_item, "field")
        self.assertEqual(result, "test_value")

        # 測試數字值提取
        number_item = {"field": {"N": "12345"}}
        result = extractor.extract_value(number_item, "field")
        self.assertEqual(result, 12345)

        # 測試布爾值提取
        bool_item: Dict[str, Dict[str, Any]] = {"field": {"BOOL": True}}
        result = extractor.extract_value(bool_item, "field")
        self.assertTrue(result)

        # 測試預設值
        empty_item: Dict[str, Any] = {}
        result = extractor.extract_value(empty_item, "missing_field", "default")
        self.assertEqual(result, "default")

    def test_command_to_query_transformer_parse(self) -> None:
        """測試命令到查詢記錄轉換器的解析功能"""
        extractor = app.DynamoDBValueExtractor()
        transformer = app.CommandToQueryTransformer(extractor)

        dynamo_record = {
            "transaction_id": {"S": "tx_001"},
            "created_at": {"N": "1704038400000"},
            "user_id": {"S": "test_user"},
            "notification_title": {"S": "測試推播"},
            "status": {"S": "DELIVERED"},
            "platform": {"S": "IOS"},
            "marketing_id": {"S": "campaign_001"},
        }

        command_record = transformer.parse_command_record(dynamo_record)

        self.assertEqual(command_record.transaction_id, "tx_001")
        self.assertEqual(command_record.user_id, "test_user")
        self.assertEqual(command_record.status, app.NotificationStatus.DELIVERED)
        self.assertEqual(command_record.platform, app.Platform.IOS)

    def test_command_to_query_transformer_transform(self) -> None:
        """測試命令記錄轉查詢記錄"""
        command_record = app.CommandRecord(
            transaction_id="tx_001",
            created_at=1704038400000,
            user_id="test_user",
            notification_title="測試推播",
            status=app.NotificationStatus.DELIVERED,
            platform=app.Platform.IOS,
            marketing_id="campaign_001",
        )

        extractor = app.DynamoDBValueExtractor()
        transformer = app.CommandToQueryTransformer(extractor)
        query_record = transformer.transform_to_query_record(command_record)

        self.assertEqual(query_record.transaction_id, "tx_001")
        self.assertEqual(query_record.user_id, "test_user")
        self.assertEqual(query_record.marketing_id, "campaign_001")

    def test_to_dynamo_item(self) -> None:
        """測試轉換為 DynamoDB 項目"""
        query_record = app.QueryRecord(
            user_id="test_user",
            created_at=1704038400000,
            transaction_id="tx_001",
            notification_title="測試推播",
            status=app.NotificationStatus.DELIVERED,
            platform=app.Platform.IOS,
            marketing_id="campaign_001",
            error_msg="測試錯誤",
        )

        extractor = app.DynamoDBValueExtractor()
        transformer = app.CommandToQueryTransformer(extractor)
        item = transformer.to_dynamo_item(query_record)

        self.assertEqual(item["user_id"], "test_user")
        self.assertEqual(item["transaction_id"], "tx_001")
        self.assertEqual(item["status"], "DELIVERED")
        self.assertEqual(item["platform"], "IOS")
        self.assertEqual(item["marketing_id"], "campaign_001")
        self.assertEqual(item["error_msg"], "測試錯誤")

    def test_stream_event_parser(self) -> None:
        """測試 Stream 事件解析器"""
        parser = app.StreamEventParser()

        stream_record = {
            "eventName": "INSERT",
            "dynamodb": {
                "NewImage": {"transaction_id": {"S": "tx_001"}, "user_id": {"S": "test_user"}},
                "OldImage": None,
            },
        }

        stream_event = parser.parse_stream_event(stream_record)

        self.assertEqual(stream_event.event_name, "INSERT")
        self.assertIsNotNone(stream_event.new_image)
        self.assertIsNone(stream_event.old_image)

    @mock_dynamodb
    def test_query_side_repository_save(self) -> None:
        """測試查詢端倉庫保存功能"""
        import boto3

        # 創建測試表
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="test-notification-records",
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "created_at", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "created_at", "AttributeType": "N"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        with patch.object(app, "get_dynamodb_resource", return_value=dynamodb):
            repository = app.QuerySideRepository("test-notification-records")

            query_record = app.QueryRecord(
                user_id="test_user",
                created_at=1704038400000,
                transaction_id="tx_001",
                notification_title="測試推播",
                status=app.NotificationStatus.DELIVERED,
                platform=app.Platform.IOS,
            )

            # 測試保存
            repository.save_query_record(query_record)

            # 驗證保存結果
            table = dynamodb.Table("test-notification-records")
            response = table.get_item(Key={"user_id": "test_user", "created_at": 1704038400000})
            item = response.get("Item")
            self.assertIsNotNone(item)
            self.assertEqual(item["transaction_id"], "tx_001")

    @mock_dynamodb
    def test_query_side_repository_delete(self) -> None:
        """測試查詢端倉庫刪除功能"""
        import boto3

        # 創建測試表
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="test-notification-records",
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "created_at", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "created_at", "AttributeType": "N"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # 插入測試數據
        table.put_item(
            Item={"user_id": "test_user", "created_at": 1704038400000, "transaction_id": "tx_001"}
        )

        with patch.object(app, "get_dynamodb_resource", return_value=dynamodb):
            repository = app.QuerySideRepository("test-notification-records")

            # 測試刪除
            repository.delete_query_record("test_user", 1704038400000)

            # 驗證刪除結果
            response = table.get_item(Key={"user_id": "test_user", "created_at": 1704038400000})
            self.assertNotIn("Item", response)

    def test_stream_processor_service_process_events(self) -> None:
        """測試 Stream 處理器服務處理事件"""
        # 創建模擬組件
        extractor = app.DynamoDBValueExtractor()
        transformer = app.CommandToQueryTransformer(extractor)
        parser = app.StreamEventParser()

        # 模擬倉庫
        mock_repository = MagicMock()

        processor = app.StreamProcessorService(transformer, parser, mock_repository)

        # 準備測試記錄
        records = [
            {
                "eventName": "INSERT",
                "dynamodb": {
                    "NewImage": {
                        "transaction_id": {"S": "tx_001"},
                        "created_at": {"N": "1704038400000"},
                        "user_id": {"S": "test_user"},
                        "notification_title": {"S": "測試推播"},
                        "status": {"S": "DELIVERED"},
                        "platform": {"S": "IOS"},
                    }
                },
            }
        ]

        # 執行處理
        processed_count = processor.process_stream_events(records)

        # 驗證結果
        self.assertEqual(processed_count, 1)
        mock_repository.save_query_record.assert_called_once()

    def test_stream_processor_service_process_remove_event(self) -> None:
        """測試 Stream 處理器處理刪除事件"""
        # 創建模擬組件
        extractor = app.DynamoDBValueExtractor()
        transformer = app.CommandToQueryTransformer(extractor)
        parser = app.StreamEventParser()

        # 模擬倉庫
        mock_repository = MagicMock()

        processor = app.StreamProcessorService(transformer, parser, mock_repository)

        # 準備測試記錄
        records = [
            {
                "eventName": "REMOVE",
                "dynamodb": {
                    "OldImage": {
                        "transaction_id": {"S": "tx_001"},
                        "created_at": {"N": "1704038400000"},
                        "user_id": {"S": "test_user"},
                        "notification_title": {"S": "測試推播"},
                        "status": {"S": "DELIVERED"},
                        "platform": {"S": "IOS"},
                    }
                },
            }
        ]

        # 執行處理
        processed_count = processor.process_stream_events(records)

        # 驗證結果
        self.assertEqual(processed_count, 1)
        mock_repository.delete_query_record.assert_called_once_with("test_user", 1704038400000)

    @mock_dynamodb
    def test_lambda_handler_success(self) -> None:
        """測試 Lambda 處理器成功案例"""
        import boto3

        # 創建測試表
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="test-notification-records",
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "created_at", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "created_at", "AttributeType": "N"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # 準備測試事件
        event = {
            "Records": [
                {
                    "eventName": "INSERT",
                    "dynamodb": {
                        "NewImage": {
                            "transaction_id": {"S": "tx_001"},
                            "created_at": {"N": "1704038400000"},
                            "user_id": {"S": "test_user"},
                            "notification_title": {"S": "測試推播"},
                            "status": {"S": "DELIVERED"},
                            "platform": {"S": "IOS"},
                        }
                    },
                }
            ]
        }

        # 修正日誌記錄問題 - 使用 patch 來避免衝突
        with patch.object(app, "get_dynamodb_resource", return_value=dynamodb):
            with patch.object(app, "logger") as mock_logger:
                # 避免日誌記錄的 key 衝突
                mock_logger.info.return_value = None

                response = app.lambda_handler(event, self.lambda_context)

        # 驗證結果
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["total_records"], 1)
        self.assertEqual(body["processed_records"], 1)

    def test_lambda_handler_error_handling(self) -> None:
        """測試 Lambda 處理器錯誤處理"""
        # 準備無效事件
        event = {
            "Records": [
                {
                    "eventName": "INSERT",
                    "dynamodb": {
                        "NewImage": {
                            # 缺少必要欄位，會導致解析錯誤
                            "incomplete": {"S": "data"}
                        }
                    },
                }
            ]
        }

        # 使用 patch 來避免 PowerTools 的日誌衝突
        with patch.object(app, "logger") as mock_logger:
            # 模擬日誌記錄方法
            mock_logger.inject_lambda_context = lambda **kwargs: lambda func: func
            mock_logger.info.return_value = None
            mock_logger.error.return_value = None
            mock_logger.warning.return_value = None

            # 測試錯誤處理 - 現在檢查是否能夠優雅處理錯誤
            try:
                response = app.lambda_handler(event, self.lambda_context)
                # 如果沒有拋出異常，檢查處理結果
                self.assertEqual(response["statusCode"], 200)  # 可能處理成功但記錄為 0
                body = json.loads(response["body"])
                self.assertEqual(body["processed_records"], 0)  # 沒有成功處理的記錄
            except Exception as e:
                # 如果拋出異常，驗證異常訊息
                self.assertIn("Stream processing failed", str(e))

    @patch.object(app, "logger")
    def test_logging_functionality(self, mock_logger: MagicMock) -> None:
        """測試日誌記錄功能"""
        event: Dict[str, List[Any]] = {"Records": []}

        with patch.object(app, "QuerySideRepository"):
            app.lambda_handler(event, self.lambda_context)

        # 驗證日誌記錄被調用
        mock_logger.info.assert_called()

    def test_transform_test_function(self) -> None:
        """測試轉換測試功能"""
        # 這個測試驗證測試工具函數能正常工作
        try:
            app.test_transform()
            # 如果沒有拋出異常，則測試通過
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"test_transform function failed: {e}")


class TestDomainModels(unittest.TestCase):
    """領域模型單元測試"""

    def test_stream_event_creation(self) -> None:
        """測試 Stream 事件創建"""
        event = app.StreamEvent(event_name="INSERT", new_image={"test": "data"})

        self.assertEqual(event.event_name, "INSERT")
        self.assertEqual(event.new_image["test"], "data")
        self.assertIsNone(event.command_record)

    def test_command_record_with_optional_fields(self) -> None:
        """測試帶有可選欄位的命令記錄"""
        record = app.CommandRecord(
            transaction_id="tx_001",
            created_at=1704038400000,
            user_id="test_user",
            notification_title="測試推播",
            status=app.NotificationStatus.FAILED,
            platform=app.Platform.ANDROID,
            error_msg="推播失敗",
        )

        self.assertEqual(record.error_msg, "推播失敗")
        self.assertEqual(record.status, app.NotificationStatus.FAILED)


if __name__ == "__main__":
    unittest.main()
