"""
stream_processor_lambda 測試模組

測試 DynamoDB Stream 處理器 Lambda 函數的核心功能：
- DynamoDB Stream 事件處理
- 資料轉換和同步
- 錯誤處理
- 環境配置
"""

import os
from unittest.mock import Mock, patch

import pytest

# 設置測試環境
os.environ["AWS_REGION"] = "ap-southeast-1"
os.environ["NOTIFICATION_TABLE_NAME"] = "notification-records"


@pytest.mark.unit
class TestStreamProcessorLambda:
    """stream_processor_lambda 單元測試"""

    @pytest.fixture(autouse=True)
    def setup_environment(self) -> None:
        """設置測試環境變數"""
        os.environ["AWS_REGION"] = "ap-southeast-1"
        os.environ["NOTIFICATION_TABLE_NAME"] = "notification-records"

    @pytest.fixture
    def sample_dynamodb_event(self) -> dict:
        """提供標準的 DynamoDB Stream 事件範例"""
        return {
            "Records": [
                {
                    "eventID": "1",
                    "eventName": "INSERT",
                    "eventVersion": "1.1",
                    "eventSource": "aws:dynamodb",
                    "awsRegion": "ap-southeast-1",
                    "dynamodb": {
                        "ApproximateCreationDateTime": 1732000000.0,
                        "Keys": {"transaction_id": {"S": "tx-test-001"}},
                        "NewImage": {
                            "transaction_id": {"S": "tx-test-001"},
                            "created_at": {"N": "1732000000"},
                            "user_id": {"S": "user-123"},
                            "notification_title": {"S": "Test Notification"},
                            "status": {"S": "SENT"},
                            "platform": {"S": "IOS"},
                            "marketing_id": {"S": "test-campaign"},
                            "device_token": {"S": "test-device-token"},
                            "ap_id": {"S": "ap-001"},
                        },
                        "SequenceNumber": "1",
                        "SizeBytes": 512,
                        "StreamViewType": "NEW_AND_OLD_IMAGES",
                    },
                }
            ]
        }

    @pytest.fixture
    def mock_context(self) -> Mock:
        """模擬 Lambda Context"""
        context = Mock()
        context.function_name = "stream-processor-lambda"
        context.memory_limit_in_mb = 128
        context.invoked_function_arn = (
            "arn:aws:lambda:ap-southeast-1:123456789012:function:stream-processor-lambda"
        )
        return context

    @patch("lambdas.stream_processor_lambda.app.get_dynamodb")
    def test_lambda_handler_success(
        self, mock_get_dynamodb: Mock, sample_dynamodb_event: dict, mock_context: Mock
    ) -> None:
        """測試 lambda_handler 成功處理事件"""
        # 導入測試目標
        from lambdas.stream_processor_lambda.app import lambda_handler

        # 設置 mock DynamoDB
        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_get_dynamodb.return_value = mock_dynamodb

        # 執行測試
        result = lambda_handler(sample_dynamodb_event, mock_context)

        # 驗證結果
        assert result["statusCode"] == 200
        assert result["processedRecords"] == 1
        mock_table.put_item.assert_called_once()

    @patch("lambdas.stream_processor_lambda.app.get_dynamodb")
    def test_lambda_handler_multiple_records(
        self, mock_get_dynamodb: Mock, mock_context: Mock
    ) -> None:
        """測試處理多個記錄"""
        from lambdas.stream_processor_lambda.app import lambda_handler

        # 準備多個記錄的事件
        multi_record_event = {
            "Records": [
                {
                    "eventName": "INSERT",
                    "dynamodb": {
                        "NewImage": {
                            "transaction_id": {"S": f"tx-test-{i:03d}"},
                            "created_at": {"N": str(1732000000 + i)},
                            "user_id": {"S": f"user-{i}"},
                            "notification_title": {"S": f"Test Notification {i}"},
                            "status": {"S": "SENT"},
                            "platform": {"S": "IOS"},
                        }
                    },
                }
                for i in range(3)
            ]
        }

        # 設置 mock
        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_get_dynamodb.return_value = mock_dynamodb

        # 執行測試
        result = lambda_handler(multi_record_event, mock_context)

        # 驗證結果
        assert result["statusCode"] == 200
        assert result["processedRecords"] == 3
        assert mock_table.put_item.call_count == 3

    def test_extract_value_function(self) -> None:
        """測試 extract_value 輔助函數"""
        from lambdas.stream_processor_lambda.app import extract_value

        # 測試字串值
        assert extract_value({"key": {"S": "value"}}, "key") == "value"

        # 測試數字值
        assert extract_value({"key": {"N": "123"}}, "key") == 123

        # 測試布林值
        assert extract_value({"key": {"BOOL": True}}, "key") is True

        # 測試預設值
        assert extract_value({}, "missing_key", "default") == "default"

        # 測試無效格式
        assert extract_value({"key": {"INVALID": "value"}}, "key", "default") == "default"

    def test_parse_command_record_success(self) -> None:
        """測試命令記錄解析成功案例"""
        from lambdas.stream_processor_lambda.app import parse_command_record

        dynamo_record = {
            "transaction_id": {"S": "tx-001"},
            "created_at": {"N": "1732000000"},
            "user_id": {"S": "user-123"},
            "notification_title": {"S": "Test Title"},
            "status": {"S": "SENT"},
            "platform": {"S": "IOS"},
            "marketing_id": {"S": "campaign-001"},
            "device_token": {"S": "token-123"},
            "ap_id": {"S": "ap-001"},
            "sns_id": {"S": "sns-001"},
        }

        result = parse_command_record(dynamo_record)

        assert result.transaction_id == "tx-001"
        assert result.created_at == 1732000000
        assert result.user_id == "user-123"
        assert result.notification_title == "Test Title"
        assert result.status.value == "SENT"
        assert result.platform.value == "IOS"

    def test_parse_command_record_missing_required_fields(self) -> None:
        """測試缺少必要欄位時的錯誤處理"""
        from lambdas.stream_processor_lambda.app import parse_command_record

        # 缺少 transaction_id
        incomplete_record = {
            "created_at": {"N": "1732000000"},
            "user_id": {"S": "user-123"},
            "notification_title": {"S": "Test Title"},
        }

        with pytest.raises(ValueError, match="Missing required fields"):
            parse_command_record(incomplete_record)

    def test_transform_to_query_record(self) -> None:
        """測試命令記錄轉查詢記錄"""
        from lambdas.stream_processor_lambda.app import (
            CommandRecord,
            NotificationStatus,
            Platform,
            transform_to_query_record,
        )

        command_record = CommandRecord(
            transaction_id="tx-001",
            created_at=1732000000,
            user_id="user-123",
            marketing_id="campaign-001",
            notification_title="Test Title",
            status=NotificationStatus.SENT,
            platform=Platform.IOS,
            device_token="token-123",
            payload="{}",
            error_msg=None,
            ap_id="ap-001",
            sns_id="sns-001",
        )

        result = transform_to_query_record(command_record)

        assert result.user_id == "user-123"
        assert result.created_at == 1732000000
        assert result.transaction_id == "tx-001"
        assert result.status == NotificationStatus.SENT
        assert result.platform == Platform.IOS

    @patch("lambdas.stream_processor_lambda.app.get_dynamodb")
    def test_save_query_record_success(self, mock_get_dynamodb: Mock) -> None:
        """測試保存查詢記錄成功"""
        from lambdas.stream_processor_lambda.app import (
            NotificationStatus,
            Platform,
            QueryRecord,
            save_query_record,
        )

        # 準備測試資料
        query_record = QueryRecord(
            user_id="user-123",
            created_at=1732000000,
            transaction_id="tx-001",
            marketing_id="campaign-001",
            notification_title="Test Title",
            status=NotificationStatus.SENT,
            platform=Platform.IOS,
            error_msg=None,
            ap_id="ap-001",
            sns_id="sns-001",
        )

        # 設置 mock
        mock_table = Mock()
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_get_dynamodb.return_value = mock_dynamodb

        # 執行測試
        save_query_record(query_record)

        # 驗證
        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args[1]["Item"]
        assert call_args["user_id"] == "user-123"
        assert call_args["transaction_id"] == "tx-001"

    @patch("lambdas.stream_processor_lambda.app.get_dynamodb")
    def test_save_query_record_client_error(self, mock_get_dynamodb: Mock) -> None:
        """測試保存查詢記錄時的 DynamoDB 錯誤"""
        from botocore.exceptions import ClientError

        from lambdas.stream_processor_lambda.app import (
            NotificationStatus,
            Platform,
            QueryRecord,
            save_query_record,
        )

        # 準備測試資料
        query_record = QueryRecord(
            user_id="user-123",
            created_at=1732000000,
            transaction_id="tx-001",
            marketing_id=None,
            notification_title="Test Title",
            status=NotificationStatus.SENT,
            platform=Platform.IOS,
            error_msg=None,
            ap_id=None,
            sns_id=None,
        )

        # 設置 mock 拋出 ClientError
        mock_table = Mock()
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Test error"}}, "PutItem"
        )
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_get_dynamodb.return_value = mock_dynamodb

        # 執行測試並驗證拋出異常
        with pytest.raises(ClientError):
            save_query_record(query_record)

    def test_process_stream_record_skip_non_insert(self) -> None:
        """測試跳過非 INSERT 事件"""
        from lambdas.stream_processor_lambda.app import process_stream_record

        modify_record = {
            "eventName": "MODIFY",
            "dynamodb": {"NewImage": {"transaction_id": {"S": "tx-001"}}},
        }

        # 這應該不會拋出異常，只是跳過處理
        process_stream_record(modify_record)

    def test_process_stream_record_no_new_image(self) -> None:
        """測試沒有 NewImage 的情況"""
        from lambdas.stream_processor_lambda.app import process_stream_record

        record_without_image = {"eventName": "INSERT", "dynamodb": {}}

        # 這應該不會拋出異常，只是記錄警告
        process_stream_record(record_without_image)

    @patch("lambdas.stream_processor_lambda.app.get_dynamodb")
    def test_process_stream_record_exception_handling(self, mock_get_dynamodb: Mock) -> None:
        """測試記錄處理中的異常處理"""
        from lambdas.stream_processor_lambda.app import process_stream_record

        # 設置 mock 拋出異常
        mock_get_dynamodb.side_effect = Exception("Database connection failed")

        record = {
            "eventName": "INSERT",
            "dynamodb": {
                "NewImage": {
                    "transaction_id": {"S": "tx-001"},
                    "created_at": {"N": "1732000000"},
                    "user_id": {"S": "user-123"},
                    "notification_title": {"S": "Test"},
                }
            },
        }

        # 應該拋出異常
        with pytest.raises(Exception, match="Database connection failed"):
            process_stream_record(record)

    def test_get_dynamodb_resource_localstack(self) -> None:
        """測試 LocalStack 環境的 DynamoDB 資源配置"""
        with patch.dict(os.environ, {"LOCALSTACK_HOSTNAME": "localstack"}):
            with patch("lambdas.stream_processor_lambda.app.boto3.resource") as mock_boto3:
                from lambdas.stream_processor_lambda.app import get_dynamodb_resource

                get_dynamodb_resource()

                mock_boto3.assert_called_once_with(
                    "dynamodb",
                    endpoint_url="http://localstack:4566",
                    region_name="ap-southeast-1",
                    aws_access_key_id="test",
                    aws_secret_access_key="test",  # pragma: allowlist secret
                )

    def test_get_dynamodb_resource_aws(self) -> None:
        """測試 AWS 環境的 DynamoDB 資源配置"""
        with patch.dict(os.environ, {"AWS_REGION": "us-west-2"}, clear=True):
            with patch("lambdas.stream_processor_lambda.app.boto3.resource") as mock_boto3:
                from lambdas.stream_processor_lambda.app import get_dynamodb_resource

                get_dynamodb_resource()

                mock_boto3.assert_called_once_with("dynamodb", region_name="us-west-2")

    @patch("lambdas.stream_processor_lambda.app.get_dynamodb_resource")
    def test_get_dynamodb_singleton(self, mock_get_resource: Mock) -> None:
        """測試 DynamoDB 單例模式"""
        from lambdas.stream_processor_lambda.app import get_dynamodb

        mock_resource = Mock()
        mock_get_resource.return_value = mock_resource

        # 第一次調用
        result1 = get_dynamodb()
        # 第二次調用
        result2 = get_dynamodb()

        # 應該返回同一個實例
        assert result1 is result2
        # 只應該調用一次資源創建
        mock_get_resource.assert_called_once()

    @patch("lambdas.stream_processor_lambda.app.get_dynamodb")
    def test_lambda_handler_partial_failure(
        self, mock_get_dynamodb: Mock, mock_context: Mock
    ) -> None:
        """測試部分記錄處理失敗的情況"""
        from lambdas.stream_processor_lambda.app import lambda_handler

        # 設置第二個記錄會失敗
        mock_table = Mock()
        mock_table.put_item.side_effect = [None, Exception("DB Error"), None]
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_get_dynamodb.return_value = mock_dynamodb

        event = {
            "Records": [
                {
                    "eventName": "INSERT",
                    "dynamodb": {
                        "NewImage": {
                            "transaction_id": {"S": f"tx-{i}"},
                            "created_at": {"N": str(1732000000 + i)},
                            "user_id": {"S": f"user-{i}"},
                            "notification_title": {"S": f"Title {i}"},
                            "status": {"S": "SENT"},
                            "platform": {"S": "IOS"},
                        }
                    },
                }
                for i in range(3)
            ]
        }

        result = lambda_handler(event, mock_context)

        # 應該處理成功 2 個記錄（第一個和第三個）
        assert result["statusCode"] == 200
        assert result["processedRecords"] == 2

    def test_enum_classes(self) -> None:
        """測試枚舉類別"""
        from lambdas.stream_processor_lambda.app import NotificationStatus, Platform

        # 測試 NotificationStatus
        assert NotificationStatus.SENT.value == "SENT"
        assert NotificationStatus.DELIVERED.value == "DELIVERED"
        assert NotificationStatus.FAILED.value == "FAILED"

        # 測試 Platform
        assert Platform.IOS.value == "IOS"
        assert Platform.ANDROID.value == "ANDROID"
        assert Platform.WEBPUSH.value == "WEBPUSH"
