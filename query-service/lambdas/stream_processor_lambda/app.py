import json
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import BotoCoreError, ClientError

# Environment detection
IS_LAMBDA_ENV = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None

# Initialize PowerTools
logger = Logger(disabled=not IS_LAMBDA_ENV, service="stream-processor-lambda")
tracer = Tracer(disabled=not IS_LAMBDA_ENV, service="stream-processor-lambda")

# ================================
# Domain Models and Value Objects
# ================================


class NotificationStatus(Enum):
    """Notification status enumeration"""

    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class Platform(Enum):
    """Platform enumeration"""

    IOS = "IOS"
    ANDROID = "ANDROID"
    WEBPUSH = "WEBPUSH"


@dataclass
class CommandRecord:
    """Command record domain model"""

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
    """Query record domain model"""

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
    """Stream event model"""

    event_name: str
    command_record: Optional[CommandRecord] = None
    old_record: Optional[CommandRecord] = None
    new_image: Optional[Dict[str, Any]] = None
    old_image: Optional[Dict[str, Any]] = None


# ================================
# Infrastructure
# ================================


def get_dynamodb_resource() -> Any:
    """Get DynamoDB resource with environment-specific configuration"""
    if os.environ.get("LOCALSTACK_HOSTNAME"):
        # LocalStack environment
        logger.info("Initializing DynamoDB client for LocalStack environment")
        return boto3.resource(
            "dynamodb",
            endpoint_url="http://localstack:4566",
            region_name="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
    else:
        # AWS environment or test environment
        aws_region = os.environ.get("AWS_REGION", "us-east-1")
        logger.info(f"Initializing DynamoDB client for AWS environment in region: {aws_region}")
        return boto3.resource("dynamodb", region_name=aws_region)


# Global variable with lazy initialization
_dynamodb = None


def get_dynamodb() -> Any:
    """Get DynamoDB resource singleton with error handling"""
    global _dynamodb
    if _dynamodb is None:
        try:
            _dynamodb = get_dynamodb_resource()
            logger.info("DynamoDB resource singleton initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DynamoDB resource: {str(e)}")
            raise
    return _dynamodb


# Environment configuration
READ_TABLE_NAME = os.environ.get("NOTIFICATION_TABLE_NAME", "notification-records")
logger.info(f"Configured read table name: {READ_TABLE_NAME}")

# ================================
# Domain Services
# ================================


class DynamoDBValueExtractor:
    """DynamoDB value extraction service"""

    @staticmethod
    def extract_value(item: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Extract value from DynamoDB format with type safety"""
        if key not in item:
            return default

        dynamo_value = item[key]
        try:
            if "S" in dynamo_value:
                return dynamo_value["S"]
            elif "N" in dynamo_value:
                return int(dynamo_value["N"])
            elif "BOOL" in dynamo_value:
                return dynamo_value["BOOL"]
            else:
                logger.warning(f"Unknown DynamoDB type for key {key}: {dynamo_value}")
                return default
        except (ValueError, KeyError) as e:
            logger.error(f"Error extracting value for key {key}: {str(e)}")
            return default


class CommandToQueryTransformer:
    """Command record to query record transformation service"""

    def __init__(self, extractor: DynamoDBValueExtractor):
        self.extractor = extractor

    @tracer.capture_method
    def parse_command_record(self, dynamo_record: Dict[str, Any]) -> CommandRecord:
        """Parse DynamoDB format command record with enhanced error handling"""
        try:
            status_str = self.extractor.extract_value(dynamo_record, "status")
            platform_str = self.extractor.extract_value(dynamo_record, "platform")

            # Validate required fields
            transaction_id = self.extractor.extract_value(dynamo_record, "transaction_id")
            created_at = self.extractor.extract_value(dynamo_record, "created_at")
            user_id = self.extractor.extract_value(dynamo_record, "user_id")
            notification_title = self.extractor.extract_value(dynamo_record, "notification_title")

            if not all([transaction_id, created_at, user_id, notification_title]):
                missing_fields = [
                    field
                    for field, value in [
                        ("transaction_id", transaction_id),
                        ("created_at", created_at),
                        ("user_id", user_id),
                        ("notification_title", notification_title),
                    ]
                    if not value
                ]
                raise ValueError(f"Missing required fields: {missing_fields}")

            return CommandRecord(
                transaction_id=transaction_id,
                created_at=created_at,
                user_id=user_id,
                marketing_id=self.extractor.extract_value(dynamo_record, "marketing_id"),
                notification_title=notification_title,
                status=NotificationStatus(status_str) if status_str else NotificationStatus.SENT,
                platform=Platform(platform_str) if platform_str else Platform.IOS,
                device_token=self.extractor.extract_value(dynamo_record, "device_token"),
                payload=self.extractor.extract_value(dynamo_record, "payload"),
                error_msg=self.extractor.extract_value(dynamo_record, "error_msg"),
            )
        except (ValueError, KeyError) as e:
            logger.error(
                "Failed to parse command record",
                extra={"error": str(e), "record_keys": list(dynamo_record.keys())},
            )
            raise ValueError(f"Invalid command record format: {e}")
        except Exception as e:
            logger.error(
                "Unexpected error parsing command record",
                extra={"error": str(e), "record": str(dynamo_record)[:500]},
            )
            raise

    @tracer.capture_method
    def transform_to_query_record(self, command_record: CommandRecord) -> QueryRecord:
        """Transform command record to query record"""
        try:
            query_record = QueryRecord(
                user_id=command_record.user_id,
                created_at=command_record.created_at,
                transaction_id=command_record.transaction_id,
                marketing_id=command_record.marketing_id,
                notification_title=command_record.notification_title,
                status=command_record.status,
                platform=command_record.platform,
                error_msg=command_record.error_msg,
            )

            logger.debug(
                "Command record transformed to query record",
                extra={"transaction_id": command_record.transaction_id},
            )

            return query_record
        except Exception as e:
            logger.error(
                "Failed to transform command record to query record",
                extra={"transaction_id": command_record.transaction_id, "error": str(e)},
            )
            raise

    @tracer.capture_method
    def to_dynamo_item(self, query_record: QueryRecord) -> Dict[str, Any]:
        """Convert query record to DynamoDB item format with validation"""
        try:
            item = {
                "user_id": query_record.user_id,
                "created_at": query_record.created_at,
                "transaction_id": query_record.transaction_id,
                "notification_title": query_record.notification_title,
                "status": query_record.status.value,
                "platform": query_record.platform.value,
            }

            # Optional fields - only include if they have values
            if query_record.marketing_id and query_record.marketing_id.strip():
                item["marketing_id"] = query_record.marketing_id
            if query_record.error_msg and query_record.error_msg.strip():
                item["error_msg"] = query_record.error_msg

            logger.debug(
                "Query record converted to DynamoDB item",
                extra={"transaction_id": query_record.transaction_id, "item_size": len(str(item))},
            )

            return item
        except Exception as e:
            logger.error(
                "Failed to convert query record to DynamoDB item",
                extra={"transaction_id": query_record.transaction_id, "error": str(e)},
            )
            raise


class StreamEventParser:
    """Stream event parsing service with enhanced validation"""

    @tracer.capture_method
    def parse_stream_event(self, stream_record: Dict[str, Any]) -> StreamEvent:
        """Parse DynamoDB Stream record with validation"""
        try:
            event_name = stream_record.get("eventName")
            dynamodb_record = stream_record.get("dynamodb", {})

            new_image = dynamodb_record.get("NewImage")
            old_image = dynamodb_record.get("OldImage")

            logger.debug(
                "Parsing stream event",
                extra={
                    "event_name": event_name,
                    "has_new_image": new_image is not None,
                    "has_old_image": old_image is not None,
                },
            )

            return StreamEvent(
                event_name=event_name or "UNKNOWN", new_image=new_image, old_image=old_image
            )
        except Exception as e:
            logger.error(
                "Failed to parse stream event",
                extra={"error": str(e), "record_keys": list(stream_record.keys())},
            )
            raise


class QuerySideRepository:
    """Query side database operations repository with enhanced error handling"""

    def __init__(self, table_name: str):
        self.table_name = table_name
        try:
            self.table = get_dynamodb().Table(table_name)
            logger.info(f"QuerySideRepository initialized with table: {table_name}")
        except Exception as e:
            logger.error(f"Failed to initialize QuerySideRepository: {str(e)}")
            raise

    @tracer.capture_method
    def save_query_record(self, query_record: QueryRecord) -> None:
        """Save query record with comprehensive error handling"""
        transformer = CommandToQueryTransformer(DynamoDBValueExtractor())
        item = transformer.to_dynamo_item(query_record)

        try:
            self.table.put_item(Item=item)
            logger.info(
                "Successfully saved query record",
                extra={
                    "transaction_id": query_record.transaction_id,
                    "user_id": query_record.user_id,
                    "table_name": self.table_name,
                },
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "UnknownError")
            logger.error(
                "DynamoDB ClientError saving query record",
                extra={
                    "transaction_id": query_record.transaction_id,
                    "error_code": error_code,
                    "error_message": str(e),
                },
            )
            raise
        except BotoCoreError as e:
            logger.error(
                "BotoCoreError saving query record",
                extra={"transaction_id": query_record.transaction_id, "error": str(e)},
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error saving query record",
                extra={
                    "transaction_id": query_record.transaction_id,
                    "error": str(e),
                    "item": str(item)[:500],
                },
            )
            raise

    @tracer.capture_method
    def delete_query_record(self, user_id: str, created_at: int) -> None:
        """Delete query record with enhanced error handling"""
        try:
            self.table.delete_item(Key={"user_id": user_id, "created_at": created_at})
            logger.info(
                "Successfully deleted query record",
                extra={"user_id": user_id, "created_at": created_at, "table_name": self.table_name},
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "UnknownError")
            logger.error(
                "DynamoDB ClientError deleting query record",
                extra={
                    "user_id": user_id,
                    "created_at": created_at,
                    "error_code": error_code,
                    "error_message": str(e),
                },
            )
            raise
        except BotoCoreError as e:
            logger.error(
                "BotoCoreError deleting query record",
                extra={"user_id": user_id, "created_at": created_at, "error": str(e)},
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error deleting query record",
                extra={"user_id": user_id, "created_at": created_at, "error": str(e)},
            )
            raise


# ================================
# Application Services
# ================================


class StreamProcessorService:
    """Stream processing application service with enhanced monitoring"""

    def __init__(
        self,
        transformer: CommandToQueryTransformer,
        parser: StreamEventParser,
        repository: QuerySideRepository,
    ):
        self.transformer = transformer
        self.parser = parser
        self.repository = repository
        logger.info("StreamProcessorService initialized successfully")

    @tracer.capture_method
    def process_stream_events(self, records: List[Dict[str, Any]]) -> int:
        """Process stream events list with comprehensive error handling and monitoring"""
        processed_count = 0
        failed_count = 0

        logger.info("Starting stream events processing", extra={"total_records": len(records)})

        for index, record in enumerate(records):
            try:
                logger.debug(f"Processing record {index + 1}/{len(records)}")
                stream_event = self.parser.parse_stream_event(record)
                self._process_single_event(stream_event)
                processed_count += 1

            except Exception as e:
                failed_count += 1
                logger.error(
                    "Failed to process stream record",
                    extra={
                        "record_index": index,
                        "error": str(e),
                        "event_name": record.get("eventName", "unknown"),
                    },
                )
                # In production, failed records might need to be sent to DLQ
                # Here we continue processing other records
                continue

        success_rate = (processed_count / len(records) * 100) if records else 100

        logger.info(
            "Stream events processing completed",
            extra={
                "total_records": len(records),
                "processed_count": processed_count,
                "failed_count": failed_count,
                "success_rate": f"{success_rate:.1f}%",
            },
        )

        return processed_count

    @tracer.capture_method
    def _process_single_event(self, event: StreamEvent) -> None:
        """Process single event with detailed logging and validation"""
        logger.debug("Processing single event", extra={"event_name": event.event_name})

        try:
            if event.event_name in ["INSERT", "MODIFY"]:
                if event.new_image:
                    command_record = self.transformer.parse_command_record(event.new_image)
                    query_record = self.transformer.transform_to_query_record(command_record)
                    self.repository.save_query_record(query_record)
                    logger.info(
                        f"Processed {event.event_name} event successfully",
                        extra={
                            "transaction_id": command_record.transaction_id,
                            "user_id": command_record.user_id,
                            "status": command_record.status.value,
                        },
                    )
                else:
                    logger.warning(
                        f"Received {event.event_name} event without new_image",
                        extra={"event_name": event.event_name},
                    )

            elif event.event_name == "REMOVE":
                if event.old_image:
                    old_command_record = self.transformer.parse_command_record(event.old_image)
                    self.repository.delete_query_record(
                        old_command_record.user_id, old_command_record.created_at
                    )
                    logger.info(
                        f"Processed {event.event_name} event successfully",
                        extra={
                            "transaction_id": old_command_record.transaction_id,
                            "user_id": old_command_record.user_id,
                        },
                    )
                else:
                    logger.warning(
                        f"Received {event.event_name} event without old_image",
                        extra={"event_name": event.event_name},
                    )
            else:
                logger.warning(
                    "Received unsupported event type", extra={"event_name": event.event_name}
                )

        except Exception as e:
            logger.error(
                "Error processing single event",
                extra={"event_name": event.event_name, "error": str(e)},
            )
            raise


# ================================
# Lambda Handler
# ================================


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_HTTP)
@tracer.capture_lambda_handler
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Process DynamoDB Stream events and synchronize data to read table

    Enhanced with comprehensive error handling, monitoring, and logging
    """
    try:
        records = event.get("Records", [])

        logger.info(
            "Stream processing started",
            extra={
                "total_records": len(records),
                "aws_request_id": (
                    getattr(context, "aws_request_id", "unknown") if context else "no_context"
                ),
                "function_name": (
                    getattr(context, "function_name", "unknown") if context else "no_context"
                ),
            },
        )

        # Initialize services
        try:
            repository = QuerySideRepository(READ_TABLE_NAME)
            extractor = DynamoDBValueExtractor()
            transformer = CommandToQueryTransformer(extractor)
            parser = StreamEventParser()
            processor = StreamProcessorService(transformer, parser, repository)
        except Exception as e:
            logger.error(f"Failed to initialize services: {str(e)}")
            raise Exception(f"Service initialization failed: {str(e)}")

        # Process events
        processed_count = processor.process_stream_events(records)

        # Calculate success rate
        success_rate = (processed_count / len(records) * 100) if records else 100

        response_body = {
            "message": "Stream processing completed successfully",
            "total_records": len(records),
            "processed_records": processed_count,
            "failed_records": len(records) - processed_count,
            "success_rate": f"{success_rate:.1f}%",
        }

        response = {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "X-Processed-Records": str(processed_count),
                "X-Total-Records": str(len(records)),
            },
            "body": json.dumps(response_body),
        }

        logger.info("Stream processing completed successfully", extra=response_body)

        return response

    except Exception as e:
        error_message = f"Stream processing failed: {str(e)}"
        logger.error(
            "Stream processing failed",
            extra={
                "error": str(e),
                "event_records_count": len(event.get("Records", [])),
                "aws_request_id": (
                    getattr(context, "aws_request_id", "unknown") if context else "no_context"
                ),
            },
        )

        # In Lambda, raising an exception will cause retry
        # This is the expected behavior for stream processing
        raise Exception(error_message)


# ================================
# Testing Utilities
# ================================


def test_transform() -> None:
    """Test record transformation functionality for development and debugging"""
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

        print("\n✅ Test transformation completed successfully")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    test_transform()
