import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

# Environment detection
IS_LAMBDA_ENV = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None

# Initialize PowerTools (without decorators in lambda_handler)
logger = Logger(service="stream-processor-lambda")
tracer = Tracer(service="stream-processor-lambda")

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
    ap_id: Optional[str] = None


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
    ap_id: Optional[str] = None


def get_dynamodb_resource() -> Any:
    """Get DynamoDB resource with environment-specific configuration"""
    if os.environ.get("LOCALSTACK_HOSTNAME"):
        # LocalStack environment
        logger.info("Initializing DynamoDB client for LocalStack environment")
        return boto3.resource(
            "dynamodb",
            endpoint_url="http://localstack:4566",
            region_name="ap-southeast-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
    else:
        # AWS environment or test environment
        aws_region = os.environ.get("AWS_REGION", "ap-southeast-1")
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


def parse_command_record(dynamo_record: Dict[str, Any]) -> CommandRecord:
    """Parse DynamoDB format command record with enhanced error handling"""
    try:
        status_str = extract_value(dynamo_record, "status")
        platform_str = extract_value(dynamo_record, "platform")

        # Validate required fields
        transaction_id = extract_value(dynamo_record, "transaction_id")
        created_at = extract_value(dynamo_record, "created_at")
        user_id = extract_value(dynamo_record, "user_id")
        notification_title = extract_value(dynamo_record, "notification_title")

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
            marketing_id=extract_value(dynamo_record, "marketing_id"),
            notification_title=notification_title,
            status=NotificationStatus(status_str) if status_str else NotificationStatus.SENT,
            platform=Platform(platform_str) if platform_str else Platform.IOS,
            device_token=extract_value(dynamo_record, "device_token"),
            payload=extract_value(dynamo_record, "payload"),
            error_msg=extract_value(dynamo_record, "error_msg"),
            ap_id=extract_value(dynamo_record, "ap_id"),
        )
    except (ValueError, KeyError) as e:
        logger.error(
            f"Failed to parse command record: {e}, record_keys: {list(dynamo_record.keys())}"
        )
        raise ValueError(f"Invalid command record format: {e}")
    except Exception as e:
        logger.error(f"Unexpected error parsing command record: {e}")
        raise


def transform_to_query_record(command_record: CommandRecord) -> QueryRecord:
    """Transform command record to query record"""
    return QueryRecord(
        user_id=command_record.user_id,
        created_at=command_record.created_at,
        transaction_id=command_record.transaction_id,
        notification_title=command_record.notification_title,
        status=command_record.status,
        platform=command_record.platform,
        marketing_id=command_record.marketing_id,
        error_msg=command_record.error_msg,
        ap_id=command_record.ap_id,
    )


def save_query_record(query_record: QueryRecord) -> None:
    """Save query record to DynamoDB"""
    try:
        dynamodb = get_dynamodb()
        table = dynamodb.Table(READ_TABLE_NAME)

        item = {
            "user_id": query_record.user_id,
            "created_at": query_record.created_at,
            "transaction_id": query_record.transaction_id,
            "notification_title": query_record.notification_title,
            "status": query_record.status.value,
            "platform": query_record.platform.value,
        }

        if query_record.marketing_id:
            item["marketing_id"] = query_record.marketing_id
        if query_record.error_msg:
            item["error_msg"] = query_record.error_msg
        if query_record.ap_id:
            item["ap_id"] = query_record.ap_id

        table.put_item(Item=item)
        logger.info(f"Successfully saved query record: {query_record.transaction_id}")

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "UnknownError")
        logger.error(f"DynamoDB ClientError saving record: {error_code} - {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error saving query record: {str(e)}")
        raise


def process_stream_record(record: Dict[str, Any]) -> None:
    """Process a single stream record"""
    try:
        event_name = record.get("eventName")
        if event_name != "INSERT":
            logger.info(f"Skipping event: {event_name}")
            return

        new_image = record.get("dynamodb", {}).get("NewImage", {})
        if not new_image:
            logger.warning("No NewImage in record")
            return

        # Parse and transform
        command_record = parse_command_record(new_image)
        query_record = transform_to_query_record(command_record)
        save_query_record(query_record)

        logger.info(f"Successfully processed record: {command_record.transaction_id}")

    except Exception as e:
        logger.error(f"Error processing record: {e}")
        raise


@tracer.capture_lambda_handler
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Process DynamoDB Stream events and synchronize data to read table
    """
    try:
        records = event.get("Records", [])
        logger.info(f"Processing {len(records)} stream records")

        processed = 0
        for record in records:
            try:
                process_stream_record(record)
                processed += 1
            except Exception as e:
                logger.error(f"Failed to process record: {e}")

        logger.info(f"Successfully processed {processed}/{len(records)} records")
        return {"statusCode": 200, "processedRecords": processed}

    except Exception as e:
        logger.error(f"Stream processing failed: {e}")
        raise
