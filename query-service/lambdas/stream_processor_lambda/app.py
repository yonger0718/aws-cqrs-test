import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import boto3

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================================
# Domain Models and Value Objects
# ================================


class NotificationStatus(Enum):
    """推播狀態枚舉"""

    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class Platform(Enum):
    """平台枚舉"""

    IOS = "IOS"
    ANDROID = "ANDROID"
    WEBPUSH = "WEBPUSH"


@dataclass
class CommandRecord:
    """命令記錄領域模型"""

    transaction_id: str
    created_at: int
    user_id: str
    notification_title: str
    status: NotificationStatus
    platform: Platform
    marketing_id: Optional[str] = None
    device_token: Optional[str] = None
    payload: Optional[str] = None
    error_msg: Optional[str] = None


@dataclass
class QueryRecord:
    """查詢記錄領域模型"""

    user_id: str
    created_at: int
    transaction_id: str
    notification_title: str
    status: NotificationStatus
    platform: Platform
    marketing_id: Optional[str] = None
    error_msg: Optional[str] = None


@dataclass
class StreamEvent:
    """Stream 事件模型"""

    event_name: str
    command_record: Optional[CommandRecord] = None
    old_record: Optional[CommandRecord] = None
    new_image: Optional[Dict[str, Any]] = None
    old_image: Optional[Dict[str, Any]] = None


# ================================
# Infrastructure
# ================================


# 初始化 DynamoDB 客戶端
def get_dynamodb_resource() -> Any:
    """獲取 DynamoDB 資源，延遲初始化"""
    if os.environ.get("LOCALSTACK_HOSTNAME"):
        # LocalStack 環境
        return boto3.resource(
            "dynamodb",
            endpoint_url="http://localstack:4566",
            region_name="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
    else:
        # AWS 環境或測試環境
        return boto3.resource("dynamodb")


# 全局變數，延遲初始化
_dynamodb = None


def get_dynamodb() -> Any:
    """獲取 DynamoDB 資源的單例"""
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = get_dynamodb_resource()
    return _dynamodb


READ_TABLE_NAME = "notification-records"

# ================================
# Domain Services
# ================================


class DynamoDBValueExtractor:
    """DynamoDB 值提取服務"""

    @staticmethod
    def extract_value(item: Dict[str, Any], key: str, default: Any = None) -> Any:
        """從 DynamoDB 格式中提取值"""
        if key not in item:
            return default

        dynamo_value = item[key]
        if "S" in dynamo_value:
            return dynamo_value["S"]
        elif "N" in dynamo_value:
            return int(dynamo_value["N"])
        elif "BOOL" in dynamo_value:
            return dynamo_value["BOOL"]
        else:
            return default


class CommandToQueryTransformer:
    """命令記錄轉查詢記錄轉換服務"""

    def __init__(self, extractor: DynamoDBValueExtractor):
        self.extractor = extractor

    def parse_command_record(self, dynamo_record: Dict[str, Any]) -> CommandRecord:
        """解析 DynamoDB 格式的命令記錄"""
        try:
            status_str = self.extractor.extract_value(dynamo_record, "status")
            platform_str = self.extractor.extract_value(dynamo_record, "platform")

            return CommandRecord(
                transaction_id=self.extractor.extract_value(dynamo_record, "transaction_id"),
                created_at=self.extractor.extract_value(dynamo_record, "created_at"),
                user_id=self.extractor.extract_value(dynamo_record, "user_id"),
                marketing_id=self.extractor.extract_value(dynamo_record, "marketing_id"),
                notification_title=self.extractor.extract_value(
                    dynamo_record, "notification_title"
                ),
                status=NotificationStatus(status_str) if status_str else NotificationStatus.SENT,
                platform=Platform(platform_str) if platform_str else Platform.IOS,
                device_token=self.extractor.extract_value(dynamo_record, "device_token"),
                payload=self.extractor.extract_value(dynamo_record, "payload"),
                error_msg=self.extractor.extract_value(dynamo_record, "error_msg"),
            )
        except Exception as e:
            logger.error(f"Failed to parse command record: {e}, record: {dynamo_record}")
            raise ValueError(f"Invalid command record format: {e}")

    def transform_to_query_record(self, command_record: CommandRecord) -> QueryRecord:
        """將命令記錄轉換為查詢記錄"""
        return QueryRecord(
            user_id=command_record.user_id,
            created_at=command_record.created_at,
            transaction_id=command_record.transaction_id,
            marketing_id=command_record.marketing_id,
            notification_title=command_record.notification_title,
            status=command_record.status,
            platform=command_record.platform,
            error_msg=command_record.error_msg,
        )

    def to_dynamo_item(self, query_record: QueryRecord) -> Dict[str, Any]:
        """將查詢記錄轉換為 DynamoDB 項目格式"""
        item = {
            "user_id": query_record.user_id,
            "created_at": query_record.created_at,
            "transaction_id": query_record.transaction_id,
            "notification_title": query_record.notification_title,
            "status": query_record.status.value,
            "platform": query_record.platform.value,
        }

        # 可選欄位
        if query_record.marketing_id:
            item["marketing_id"] = query_record.marketing_id
        if query_record.error_msg:
            item["error_msg"] = query_record.error_msg

        return item


class StreamEventParser:
    """Stream 事件解析服務"""

    def parse_stream_event(self, stream_record: Dict[str, Any]) -> StreamEvent:
        """解析 DynamoDB Stream 記錄"""
        event_name = stream_record.get("eventName")
        dynamodb_record = stream_record.get("dynamodb", {})

        new_image = dynamodb_record.get("NewImage")
        old_image = dynamodb_record.get("OldImage")

        return StreamEvent(
            event_name=event_name or "UNKNOWN", new_image=new_image, old_image=old_image
        )


class QuerySideRepository:
    """查詢端資料庫操作倉庫"""

    def __init__(self, table_name: str):
        self.table = get_dynamodb().Table(table_name)

    def save_query_record(self, query_record: QueryRecord) -> None:
        """保存查詢記錄"""
        transformer = CommandToQueryTransformer(DynamoDBValueExtractor())
        item = transformer.to_dynamo_item(query_record)

        try:
            self.table.put_item(Item=item)
            logger.info(f"Successfully saved query record: {query_record.transaction_id}")
        except Exception as e:
            logger.error(f"Failed to save query record: {e}, record: {item}")
            raise

    def delete_query_record(self, user_id: str, created_at: int) -> None:
        """刪除查詢記錄"""
        try:
            self.table.delete_item(Key={"user_id": user_id, "created_at": created_at})
            logger.info(f"Successfully deleted query record: {user_id}@{created_at}")
        except Exception as e:
            logger.error(f"Failed to delete query record: {e}")
            raise


# ================================
# Application Services
# ================================


class StreamProcessorService:
    """Stream 處理應用服務"""

    def __init__(
        self,
        transformer: CommandToQueryTransformer,
        parser: StreamEventParser,
        repository: QuerySideRepository,
    ):
        self.transformer = transformer
        self.parser = parser
        self.repository = repository

    def process_stream_events(self, records: List[Dict[str, Any]]) -> int:
        """處理 Stream 事件列表"""
        processed_count = 0

        for record in records:
            try:
                stream_event = self.parser.parse_stream_event(record)
                self._process_single_event(stream_event)
                processed_count += 1

            except Exception as e:
                logger.error(f"Failed to process stream record: {e}")
                # 在生產環境中，可能需要將失敗的記錄送到 DLQ
                # 這裡我們繼續處理其他記錄
                continue

        return processed_count

    def _process_single_event(self, event: StreamEvent) -> None:
        """處理單一事件"""
        if event.event_name in ["INSERT", "MODIFY"]:
            if event.new_image:
                command_record = self.transformer.parse_command_record(event.new_image)
                query_record = self.transformer.transform_to_query_record(command_record)
                self.repository.save_query_record(query_record)
                logger.info(
                    f"Processed {event.event_name} event for transaction: "
                    f"{command_record.transaction_id}"
                )

        elif event.event_name == "REMOVE":
            if event.old_image:
                old_command_record = self.transformer.parse_command_record(event.old_image)
                self.repository.delete_query_record(
                    old_command_record.user_id, old_command_record.created_at
                )
                logger.info(
                    f"Processed {event.event_name} event for transaction: "
                    f"{old_command_record.transaction_id}"
                )


# ================================
# Lambda Handler
# ================================


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    處理 DynamoDB Stream 事件並將數據同步到讀取表
    """
    try:
        # 初始化服務
        repository = QuerySideRepository(READ_TABLE_NAME)
        extractor = DynamoDBValueExtractor()
        transformer = CommandToQueryTransformer(extractor)
        parser = StreamEventParser()
        processor = StreamProcessorService(transformer, parser, repository)

        # 處理事件
        records = event.get("Records", [])
        logger.info(f"Processing {len(records)} stream records")

        processed_count = processor.process_stream_events(records)

        logger.info(
            f"Stream processing completed. Processed {processed_count}/"
            f"{len(records)} records successfully."
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Stream processing completed successfully",
                    "total_records": len(records),
                    "processed_records": processed_count,
                    "success_rate": (
                        f"{(processed_count/len(records)*100):.1f}%" if records else "100%"
                    ),
                }
            ),
        }

    except Exception as e:
        logger.error(f"Stream processing failed: {e}")
        logger.error(f"Event: {json.dumps(event, indent=2)}")

        # 在 Lambda 中，拋出異常會導致重試
        raise Exception(f"Stream processing failed: {str(e)}")


# ================================
# Testing Utilities
# ================================


def test_transform() -> None:
    """測試記錄轉換功能"""
    test_record = {
        "transaction_id": {"S": "tx_001"},
        "created_at": {"N": "1704038400000"},
        "user_id": {"S": "test_user_001"},
        "marketing_id": {"S": "campaign_2024_new_year"},
        "notification_title": {"S": "新年快樂！"},
        "status": {"S": "DELIVERED"},
        "platform": {"S": "IOS"},
    }

    extractor = DynamoDBValueExtractor()
    transformer = CommandToQueryTransformer(extractor)

    try:
        command_record = transformer.parse_command_record(test_record)
        query_record = transformer.transform_to_query_record(command_record)
        dynamo_item = transformer.to_dynamo_item(query_record)

        print("Original DynamoDB record:")
        print(json.dumps(test_record, indent=2))
        print("\nCommand record:")
        print(command_record)
        print("\nQuery record:")
        print(query_record)
        print("\nTransformed DynamoDB item:")
        print(json.dumps(dynamo_item, indent=2))

    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == "__main__":
    test_transform()
