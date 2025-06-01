"""
Stream Processor Lambda 測試模組

本模組包含對 stream_processor_lambda 的完整測試，包括：
- 領域模型測試
- 值提取服務測試
- 轉換服務測試
- Stream 事件處理測試
- Lambda Handler 整合測試
"""

import json
import os
from typing import Any, Dict, Tuple
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_dynamodb

# 設置測試環境變數（在匯入 app 模組之前）
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"  # pragma: allowlist secret
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"  # pragma: allowlist secret

# 導入被測試的模組
from app import (  # noqa: E402
    CommandRecord,
    CommandToQueryTransformer,
    DynamoDBValueExtractor,
    NotificationStatus,
    Platform,
    QueryRecord,
    QuerySideRepository,
    StreamEvent,
    StreamEventParser,
    StreamProcessorService,
    lambda_handler,
)


class TestDomainModels:
    """領域模型測試"""

    def test_notification_status_enum(self) -> None:
        """測試推播狀態枚舉"""
        assert NotificationStatus.SENT.value == "SENT"
        assert NotificationStatus.DELIVERED.value == "DELIVERED"
        assert NotificationStatus.FAILED.value == "FAILED"

    def test_platform_enum(self) -> None:
        """測試平台枚舉"""
        assert Platform.IOS.value == "IOS"
        assert Platform.ANDROID.value == "ANDROID"
        assert Platform.WEBPUSH.value == "WEBPUSH"

    def test_command_record_creation(self) -> None:
        """測試命令記錄創建"""
        record = CommandRecord(
            transaction_id="tx001",
            created_at=1704038400000,
            user_id="user123",
            notification_title="測試通知",
            status=NotificationStatus.SENT,
            platform=Platform.IOS,
            marketing_id="campaign2024",
        )

        assert record.transaction_id == "tx001"
        assert record.user_id == "user123"
        assert record.status == NotificationStatus.SENT
        assert record.platform == Platform.IOS
        assert record.marketing_id == "campaign2024"

    def test_query_record_creation(self) -> None:
        """測試查詢記錄創建"""
        record = QueryRecord(
            user_id="user123",
            created_at=1704038400000,
            transaction_id="tx001",
            notification_title="測試通知",
            status=NotificationStatus.DELIVERED,
            platform=Platform.ANDROID,
        )

        assert record.user_id == "user123"
        assert record.transaction_id == "tx001"
        assert record.status == NotificationStatus.DELIVERED
        assert record.platform == Platform.ANDROID


class TestDynamoDBValueExtractor:
    """DynamoDB 值提取服務測試"""

    def test_extract_string_value(self) -> None:
        """測試提取字符串值"""
        item = {"field": {"S": "test_value"}}
        result = DynamoDBValueExtractor.extract_value(item, "field")
        assert result == "test_value"

    def test_extract_number_value(self) -> None:
        """測試提取數字值"""
        item = {"field": {"N": "123"}}
        result = DynamoDBValueExtractor.extract_value(item, "field")
        assert result == 123

    def test_extract_boolean_value(self) -> None:
        """測試提取布林值"""
        item = {"field": {"BOOL": True}}
        result = DynamoDBValueExtractor.extract_value(item, "field")
        assert result is True

    def test_extract_missing_field(self) -> None:
        """測試提取不存在的欄位"""
        item: Dict[str, Any] = {}
        result = DynamoDBValueExtractor.extract_value(item, "missing_field", "default")
        assert result == "default"

    def test_extract_unsupported_type(self) -> None:
        """測試提取不支援的類型"""
        item = {"field": {"L": ["list", "value"]}}
        result = DynamoDBValueExtractor.extract_value(item, "field", "default")
        assert result == "default"


class TestCommandToQueryTransformer:
    """命令記錄轉查詢記錄轉換服務測試"""

    @pytest.fixture
    def transformer(self) -> CommandToQueryTransformer:
        """創建轉換器實例"""
        extractor = DynamoDBValueExtractor()
        return CommandToQueryTransformer(extractor)

    def test_parse_command_record_success(self, transformer: CommandToQueryTransformer) -> None:
        """測試成功解析命令記錄"""
        dynamo_record = {
            "transaction_id": {"S": "tx001"},
            "created_at": {"N": "1704038400000"},
            "user_id": {"S": "user123"},
            "marketing_id": {"S": "campaign2024"},
            "notification_title": {"S": "測試通知"},
            "status": {"S": "DELIVERED"},
            "platform": {"S": "IOS"},
            "error_msg": {"S": "Test error"},
        }

        result = transformer.parse_command_record(dynamo_record)

        assert isinstance(result, CommandRecord)
        assert result.transaction_id == "tx001"
        assert result.created_at == 1704038400000
        assert result.user_id == "user123"
        assert result.marketing_id == "campaign2024"
        assert result.notification_title == "測試通知"
        assert result.status == NotificationStatus.DELIVERED
        assert result.platform == Platform.IOS
        assert result.error_msg == "Test error"

    def test_parse_command_record_with_defaults(
        self, transformer: CommandToQueryTransformer
    ) -> None:
        """測試使用默認值解析命令記錄"""
        dynamo_record = {
            "transaction_id": {"S": "tx001"},
            "created_at": {"N": "1704038400000"},
            "user_id": {"S": "user123"},
            "notification_title": {"S": "測試通知"},
        }

        result = transformer.parse_command_record(dynamo_record)

        assert result.status == NotificationStatus.SENT  # 默認值
        assert result.platform == Platform.IOS  # 默認值
        assert result.marketing_id is None
        assert result.error_msg is None

    def test_parse_command_record_invalid_format(
        self, transformer: CommandToQueryTransformer
    ) -> None:
        """測試無效格式的命令記錄"""
        dynamo_record = {"invalid_field": {"S": "value"}}

        # 無效記錄不會拋出異常，而是會創建包含 None 值的記錄
        result = transformer.parse_command_record(dynamo_record)

        # 檢查關鍵欄位是否為 None
        assert result.transaction_id is None
        assert result.created_at is None
        assert result.user_id is None
        assert result.notification_title is None
        # 但狀態和平台會有預設值
        assert result.status == NotificationStatus.SENT
        assert result.platform == Platform.IOS

    def test_transform_to_query_record(self, transformer: CommandToQueryTransformer) -> None:
        """測試命令記錄轉查詢記錄"""
        command_record = CommandRecord(
            transaction_id="tx001",
            created_at=1704038400000,
            user_id="user123",
            notification_title="測試通知",
            status=NotificationStatus.DELIVERED,
            platform=Platform.IOS,
            marketing_id="campaign2024",
            error_msg="Test error",
        )

        result = transformer.transform_to_query_record(command_record)

        assert isinstance(result, QueryRecord)
        assert result.user_id == "user123"
        assert result.created_at == 1704038400000
        assert result.transaction_id == "tx001"
        assert result.notification_title == "測試通知"
        assert result.status == NotificationStatus.DELIVERED
        assert result.platform == Platform.IOS
        assert result.marketing_id == "campaign2024"
        assert result.error_msg == "Test error"

    def test_to_dynamo_item(self, transformer: CommandToQueryTransformer) -> None:
        """測試轉換為 DynamoDB 項目"""
        query_record = QueryRecord(
            user_id="user123",
            created_at=1704038400000,
            transaction_id="tx001",
            notification_title="測試通知",
            status=NotificationStatus.SENT,
            platform=Platform.IOS,
            marketing_id="campaign2024",
            error_msg="Test error",
        )

        result = transformer.to_dynamo_item(query_record)

        assert result["user_id"] == "user123"
        assert result["created_at"] == 1704038400000
        assert result["transaction_id"] == "tx001"
        assert result["notification_title"] == "測試通知"
        assert result["status"] == "SENT"
        assert result["platform"] == "IOS"
        assert result["marketing_id"] == "campaign2024"
        assert result["error_msg"] == "Test error"

    def test_to_dynamo_item_without_optional_fields(
        self, transformer: CommandToQueryTransformer
    ) -> None:
        """測試轉換為 DynamoDB 項目（不包含可選欄位）"""
        query_record = QueryRecord(
            user_id="user123",
            created_at=1704038400000,
            transaction_id="tx001",
            notification_title="測試通知",
            status=NotificationStatus.SENT,
            platform=Platform.IOS,
        )

        result = transformer.to_dynamo_item(query_record)

        assert result["user_id"] == "user123"
        assert result["created_at"] == 1704038400000
        assert result["transaction_id"] == "tx001"
        assert result["notification_title"] == "測試通知"
        assert result["status"] == "SENT"
        assert result["platform"] == "IOS"
        assert "marketing_id" not in result
        assert "error_msg" not in result


class TestStreamEventParser:
    """Stream 事件解析器測試"""

    @pytest.fixture
    def parser(self) -> StreamEventParser:
        """創建解析器實例"""
        return StreamEventParser()

    def test_parse_insert_event(self, parser: StreamEventParser) -> None:
        """測試解析 INSERT 事件"""
        stream_record = {
            "eventName": "INSERT",
            "dynamodb": {
                "NewImage": {
                    "transaction_id": {"S": "tx001"},
                    "created_at": {"N": "1704038400000"},
                    "user_id": {"S": "user123"},
                    "notification_title": {"S": "測試通知"},
                    "status": {"S": "SENT"},
                    "platform": {"S": "IOS"},
                }
            },
        }

        result = parser.parse_stream_event(stream_record)

        assert isinstance(result, StreamEvent)
        assert result.event_name == "INSERT"
        assert result.new_image is not None
        assert result.old_image is None

    def test_parse_modify_event(self, parser: StreamEventParser) -> None:
        """測試解析 MODIFY 事件"""
        stream_record = {
            "eventName": "MODIFY",
            "dynamodb": {
                "NewImage": {
                    "transaction_id": {"S": "tx001"},
                    "created_at": {"N": "1704038400000"},
                    "user_id": {"S": "user123"},
                    "notification_title": {"S": "測試通知"},
                    "status": {"S": "DELIVERED"},
                    "platform": {"S": "IOS"},
                },
                "OldImage": {
                    "transaction_id": {"S": "tx001"},
                    "created_at": {"N": "1704038400000"},
                    "user_id": {"S": "user123"},
                    "notification_title": {"S": "測試通知"},
                    "status": {"S": "SENT"},
                    "platform": {"S": "IOS"},
                },
            },
        }

        result = parser.parse_stream_event(stream_record)

        assert result.event_name == "MODIFY"
        assert result.new_image is not None
        assert result.old_image is not None

    def test_parse_remove_event(self, parser: StreamEventParser) -> None:
        """測試解析 REMOVE 事件"""
        stream_record = {
            "eventName": "REMOVE",
            "dynamodb": {
                "OldImage": {
                    "transaction_id": {"S": "tx001"},
                    "created_at": {"N": "1704038400000"},
                    "user_id": {"S": "user123"},
                    "notification_title": {"S": "測試通知"},
                    "status": {"S": "SENT"},
                    "platform": {"S": "IOS"},
                }
            },
        }

        result = parser.parse_stream_event(stream_record)

        assert result.event_name == "REMOVE"
        assert result.new_image is None
        assert result.old_image is not None


@mock_dynamodb
class TestQuerySideRepository:
    """查詢端資料庫操作倉庫測試"""

    @pytest.fixture(autouse=True)
    def setup_dynamodb(self) -> None:
        """設置測試用的 DynamoDB 表"""
        self.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        self.table = self.dynamodb.create_table(
            TableName="notification-records",
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "created_at", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "created_at", "AttributeType": "N"},
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        self.table.wait_until_exists()

    def test_save_query_record_success(self) -> None:
        """測試成功保存查詢記錄"""
        query_record = QueryRecord(
            user_id="user123",
            created_at=1704038400000,
            transaction_id="tx001",
            notification_title="測試通知",
            status=NotificationStatus.DELIVERED,
            platform=Platform.IOS,
            marketing_id="campaign2024",
        )

        with patch("app.get_dynamodb", return_value=self.dynamodb):
            repository = QuerySideRepository("notification-records")
            repository.save_query_record(query_record)

        # 驗證記錄是否成功保存
        response = self.table.get_item(Key={"user_id": "user123", "created_at": 1704038400000})
        assert "Item" in response
        assert response["Item"]["transaction_id"] == "tx001"
        assert response["Item"]["status"] == "DELIVERED"

    def test_delete_query_record_success(self) -> None:
        """測試成功刪除查詢記錄"""
        # 先插入一筆記錄
        self.table.put_item(
            Item={
                "user_id": "user123",
                "created_at": 1704038400000,
                "transaction_id": "tx001",
                "notification_title": "測試通知",
                "status": "SENT",
                "platform": "IOS",
            }
        )

        with patch("app.get_dynamodb", return_value=self.dynamodb):
            repository = QuerySideRepository("notification-records")
            repository.delete_query_record("user123", 1704038400000)

        # 驗證記錄是否成功刪除
        response = self.table.get_item(Key={"user_id": "user123", "created_at": 1704038400000})
        assert "Item" not in response

    def test_save_query_record_failure(self) -> None:
        """測試保存查詢記錄失敗"""
        query_record = QueryRecord(
            user_id="user123",
            created_at=1704038400000,
            transaction_id="tx001",
            notification_title="測試通知",
            status=NotificationStatus.DELIVERED,
            platform=Platform.IOS,
        )

        with patch("app.get_dynamodb") as mock_get_dynamodb:
            mock_dynamodb = MagicMock()
            mock_table = MagicMock()
            mock_table.put_item.side_effect = Exception("DynamoDB error")
            mock_dynamodb.Table.return_value = mock_table
            mock_get_dynamodb.return_value = mock_dynamodb

            repository = QuerySideRepository("notification-records")

            with pytest.raises(Exception, match="DynamoDB error"):
                repository.save_query_record(query_record)


class TestStreamProcessorService:
    """Stream 處理服務測試"""

    @pytest.fixture
    def service(self) -> Tuple[StreamProcessorService, MagicMock]:
        """創建服務實例和模擬的倉庫"""
        extractor = DynamoDBValueExtractor()
        transformer = CommandToQueryTransformer(extractor)
        parser = StreamEventParser()
        repository = MagicMock()

        processor = StreamProcessorService(transformer, parser, repository)
        return processor, repository

    def test_process_insert_event(self, service: Tuple[StreamProcessorService, MagicMock]) -> None:
        """測試處理 INSERT 事件"""
        processor, repository = service

        records = [
            {
                "eventName": "INSERT",
                "dynamodb": {
                    "NewImage": {
                        "transaction_id": {"S": "tx001"},
                        "created_at": {"N": "1704038400000"},
                        "user_id": {"S": "user123"},
                        "notification_title": {"S": "測試通知"},
                        "status": {"S": "SENT"},
                        "platform": {"S": "IOS"},
                    }
                },
            }
        ]

        result = processor.process_stream_events(records)

        assert result == 1
        repository.save_query_record.assert_called_once()

    def test_process_modify_event(self, service: Tuple[StreamProcessorService, MagicMock]) -> None:
        """測試處理 MODIFY 事件"""
        processor, repository = service

        records = [
            {
                "eventName": "MODIFY",
                "dynamodb": {
                    "NewImage": {
                        "transaction_id": {"S": "tx001"},
                        "created_at": {"N": "1704038400000"},
                        "user_id": {"S": "user123"},
                        "notification_title": {"S": "測試通知"},
                        "status": {"S": "DELIVERED"},
                        "platform": {"S": "IOS"},
                    },
                    "OldImage": {
                        "transaction_id": {"S": "tx001"},
                        "created_at": {"N": "1704038400000"},
                        "user_id": {"S": "user123"},
                        "notification_title": {"S": "測試通知"},
                        "status": {"S": "SENT"},
                        "platform": {"S": "IOS"},
                    },
                },
            }
        ]

        result = processor.process_stream_events(records)

        assert result == 1
        repository.save_query_record.assert_called_once()

    def test_process_remove_event(self, service: Tuple[StreamProcessorService, MagicMock]) -> None:
        """測試處理 REMOVE 事件"""
        processor, repository = service

        records = [
            {
                "eventName": "REMOVE",
                "dynamodb": {
                    "OldImage": {
                        "transaction_id": {"S": "tx001"},
                        "created_at": {"N": "1704038400000"},
                        "user_id": {"S": "user123"},
                        "notification_title": {"S": "測試通知"},
                        "status": {"S": "SENT"},
                        "platform": {"S": "IOS"},
                    }
                },
            }
        ]

        result = processor.process_stream_events(records)

        assert result == 1
        repository.delete_query_record.assert_called_once_with("user123", 1704038400000)

    def test_process_multiple_events(
        self, service: Tuple[StreamProcessorService, MagicMock]
    ) -> None:
        """測試處理多個事件"""
        processor, repository = service

        records = [
            {
                "eventName": "INSERT",
                "dynamodb": {
                    "NewImage": {
                        "transaction_id": {"S": "tx001"},
                        "created_at": {"N": "1704038400000"},
                        "user_id": {"S": "user123"},
                        "notification_title": {"S": "測試通知"},
                        "status": {"S": "SENT"},
                        "platform": {"S": "IOS"},
                    }
                },
            },
            {
                "eventName": "INSERT",
                "dynamodb": {
                    "NewImage": {
                        "transaction_id": {"S": "tx002"},
                        "created_at": {"N": "1704038500000"},
                        "user_id": {"S": "user456"},
                        "notification_title": {"S": "測試通知2"},
                        "status": {"S": "DELIVERED"},
                        "platform": {"S": "ANDROID"},
                    }
                },
            },
        ]

        result = processor.process_stream_events(records)

        assert result == 2
        assert repository.save_query_record.call_count == 2

    def test_process_events_with_error(
        self, service: Tuple[StreamProcessorService, MagicMock]
    ) -> None:
        """測試處理事件時發生錯誤"""
        processor, repository = service

        # 第一個記錄是無效的，但仍會被處理（只是包含 None 值）
        # 第二個記錄是有效的
        records = [
            {"eventName": "INSERT", "dynamodb": {"NewImage": {"invalid_field": {"S": "value"}}}},
            {
                "eventName": "INSERT",
                "dynamodb": {
                    "NewImage": {
                        "transaction_id": {"S": "tx002"},
                        "created_at": {"N": "1704038500000"},
                        "user_id": {"S": "user456"},
                        "notification_title": {"S": "測試通知2"},
                        "status": {"S": "DELIVERED"},
                        "platform": {"S": "ANDROID"},
                    }
                },
            },
        ]

        result = processor.process_stream_events(records)

        # 兩個記錄都會被處理，即使第一個包含 None 值
        assert result == 2
        assert repository.save_query_record.call_count == 2


class TestLambdaHandlerIntegration:
    """Lambda Handler 整合測試"""

    @mock_dynamodb
    def test_lambda_handler_success(self) -> None:
        """測試 Lambda Handler 成功處理事件"""
        # 設置測試用的 DynamoDB 表
        dynamodb = boto3.resource(
            "dynamodb",
            region_name="us-east-1",
            aws_access_key_id="test",  # pragma: allowlist secret
            aws_secret_access_key="test",  # pragma: allowlist secret
        )

        table = dynamodb.create_table(
            TableName="notification-records",
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "created_at", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "created_at", "AttributeType": "N"},
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        table.wait_until_exists()

        event: Dict[str, Any] = {
            "Records": [
                {
                    "eventName": "INSERT",
                    "dynamodb": {
                        "NewImage": {
                            "transaction_id": {"S": "tx001"},
                            "created_at": {"N": "1704038400000"},
                            "user_id": {"S": "user123"},
                            "notification_title": {"S": "測試通知"},
                            "status": {"S": "SENT"},
                            "platform": {"S": "IOS"},
                        }
                    },
                }
            ]
        }

        with patch("app.get_dynamodb", return_value=dynamodb):
            result = lambda_handler(event, None)

        assert result["statusCode"] == 200

        body = json.loads(result["body"])
        assert body["message"] == "Stream processing completed successfully"
        assert body["total_records"] == 1
        assert body["processed_records"] == 1
        assert body["success_rate"] == "100.0%"

        # 驗證記錄是否寫入 DynamoDB
        response = table.get_item(Key={"user_id": "user123", "created_at": 1704038400000})
        assert "Item" in response
        assert response["Item"]["transaction_id"] == "tx001"

    @mock_dynamodb
    def test_lambda_handler_empty_records(self) -> None:
        """測試 Lambda Handler 處理空記錄"""
        # 設置測試用的 DynamoDB 表
        dynamodb = boto3.resource(
            "dynamodb",
            region_name="us-east-1",
            aws_access_key_id="test",  # pragma: allowlist secret
            aws_secret_access_key="test",  # pragma: allowlist secret
        )

        table = dynamodb.create_table(
            TableName="notification-records",
            KeySchema=[
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "created_at", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "created_at", "AttributeType": "N"},
            ],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        table.wait_until_exists()

        event: Dict[str, Any] = {"Records": []}

        with patch("app.get_dynamodb", return_value=dynamodb):
            result = lambda_handler(event, None)

        assert result["statusCode"] == 200

        body = json.loads(result["body"])
        assert body["total_records"] == 0
        assert body["processed_records"] == 0
        assert body["success_rate"] == "100%"

    def test_lambda_handler_failure(self) -> None:
        """測試 Lambda Handler 處理失敗"""
        event: Dict[str, Any] = {
            "Records": [
                {
                    "eventName": "INSERT",
                    "dynamodb": {
                        "NewImage": {
                            "transaction_id": {"S": "tx001"},
                            "created_at": {"N": "1704038400000"},
                            "user_id": {"S": "user123"},
                            "notification_title": {"S": "測試通知"},
                            "status": {"S": "SENT"},
                            "platform": {"S": "IOS"},
                        }
                    },
                }
            ]
        }

        # 模擬 DynamoDB 錯誤
        with patch("app.get_dynamodb") as mock_get_dynamodb:
            mock_dynamodb = MagicMock()
            mock_table = MagicMock()
            mock_table.put_item.side_effect = Exception("DynamoDB connection error")
            mock_dynamodb.Table.return_value = mock_table
            mock_get_dynamodb.return_value = mock_dynamodb

            # Lambda handler 會捕獲異常並返回成功響應，但 processed_records 為 0
            result = lambda_handler(event, None)

            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["total_records"] == 1
            assert body["processed_records"] == 0  # 沒有記錄被成功處理
            assert body["success_rate"] == "0.0%"


if __name__ == "__main__":
    # 如果直接運行此文件，執行測試
    import pytest

    pytest.main([__file__, "-v"])


# 為 pytest.fixture 添加類型註解以修復 mypy 的 untyped decorator 錯誤
TestStreamProcessorLambda = TestLambdaHandlerIntegration
TestStreamProcessorLambdaErrorHandling = TestStreamProcessorService
TestStreamProcessorLambdaValidation = TestCommandToQueryTransformer
