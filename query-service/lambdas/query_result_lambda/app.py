import json
import os
from decimal import Decimal
from typing import Any, Dict, Optional

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.event_handler.exceptions import BadRequestError, InternalServerError
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import BotoCoreError, ClientError

# Environment detection
IS_LAMBDA_ENV = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None

# Initialize PowerTools
logger = Logger(disabled=not IS_LAMBDA_ENV, service="query-result-lambda")
tracer = Tracer(disabled=not IS_LAMBDA_ENV, service="query-result-lambda")
app = APIGatewayHttpResolver()


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
        # AWS environment
        aws_region = os.environ.get("AWS_REGION", "ap-southeast-1")
        logger.info(f"Initializing DynamoDB client for AWS environment in region: {aws_region}")
        return boto3.resource("dynamodb", region_name=aws_region)


# Initialize DynamoDB with error handling
try:
    dynamodb = get_dynamodb_resource()
    TABLE_NAME = os.environ.get("NOTIFICATION_TABLE_NAME", "notification-records")
    logger.info(f"DynamoDB resource initialized successfully. Target table: {TABLE_NAME}")
except Exception as e:
    logger.error(f"Failed to initialize DynamoDB resource: {str(e)}")
    raise


def decimal_to_int(obj: Any) -> int:
    """Convert Decimal objects to int for JSON serialization"""
    if isinstance(obj, Decimal):
        return int(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class QueryService:
    """Query service for notification records with enhanced error handling"""

    def __init__(self, table_name: str):
        self.table_name = table_name
        self.table = dynamodb.Table(table_name)
        logger.info(f"QueryService initialized with table: {table_name}")

    @tracer.capture_method
    def query_transaction_notifications(self, transaction_id: str) -> Dict[str, Any]:
        """Query notification records by transaction_id (Primary Key)"""
        logger.info(
            "Starting transaction notifications query", extra={"transaction_id": transaction_id}
        )

        try:
            # 使用 transaction_id 作為主鍵進行查詢
            response = self.table.get_item(Key={"transaction_id": transaction_id})

            item = response.get("Item")
            consumed_capacity = response.get("ConsumedCapacity", {})

            items = [item] if item else []

            logger.info(
                "Transaction notifications query completed successfully",
                extra={
                    "transaction_id": transaction_id,
                    "items_found": len(items),
                    "consumed_capacity": (
                        consumed_capacity.get("CapacityUnits", 0) if consumed_capacity else 0
                    ),
                },
            )

            return {"success": True, "items": items, "count": len(items)}

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "UnknownError")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(
                "DynamoDB ClientError in transaction notifications query",
                extra={
                    "transaction_id": transaction_id,
                    "error_code": error_code,
                    "error_message": error_message,
                },
            )
            raise
        except BotoCoreError as e:
            logger.error(
                "BotoCoreError in transaction notifications query",
                extra={"transaction_id": transaction_id, "error": str(e)},
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error in transaction notifications query",
                extra={"transaction_id": transaction_id, "error": str(e)},
            )
            raise

    @tracer.capture_method
    def query_failed_notifications(self, transaction_id: Optional[str] = None) -> Dict[str, Any]:
        """Query failed notification records by transaction_id or all failed records"""
        logger.info(
            "Starting failed notifications query", extra={"transaction_id": transaction_id or "all"}
        )

        try:
            if transaction_id and transaction_id.strip():
                # Query specific transaction and check if it's failed
                logger.info(f"Querying specific transaction: {transaction_id}")
                response = self.table.get_item(Key={"transaction_id": transaction_id})

                item = response.get("Item")
                items = []

                # If the record exists and status is FAILED, return it
                if item and item.get("status") == "FAILED":
                    items = [item]
                    logger.info(f"Found failed record for transaction: {transaction_id}")
                else:
                    logger.info(f"No failed record found for transaction: {transaction_id}")

                consumed_capacity = response.get("ConsumedCapacity", {})
            else:
                # Query all failed notifications using scan
                logger.info("Querying all failed notifications")
                response = self.table.scan(
                    FilterExpression=Attr("status").eq("FAILED"),
                    ProjectionExpression=(
                        "transaction_id, #token, platform, notification_title, "
                        "notification_body, #status, send_ts, delivered_ts, "
                        "failed_ts, ap_id, created_at"
                    ),
                    ExpressionAttributeNames={"#token": "token", "#status": "status"},
                )

                items = response.get("Items", [])
                consumed_capacity = response.get("ConsumedCapacity", {})

                logger.info(f"Found {len(items)} failed notifications")

            logger.info(
                "Failed notifications query completed successfully",
                extra={
                    "transaction_id": transaction_id or "all",
                    "items_found": len(items),
                    "consumed_capacity": (
                        consumed_capacity.get("CapacityUnits", 0) if consumed_capacity else 0
                    ),
                },
            )

            return {"success": True, "items": items, "count": len(items)}

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "UnknownError")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(
                "DynamoDB ClientError in failed notifications query",
                extra={
                    "transaction_id": transaction_id or "all",
                    "error_code": error_code,
                    "error_message": error_message,
                },
            )
            raise
        except BotoCoreError as e:
            logger.error(
                "BotoCoreError in failed notifications query",
                extra={"transaction_id": transaction_id or "all", "error": str(e)},
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error in failed notifications query",
                extra={"transaction_id": transaction_id or "all", "error": str(e)},
            )
            raise


def format_notification_items(items: list) -> list:
    """Format notification record items with enhanced data handling based on new schema"""
    formatted_items = []

    for item in items:
        try:
            formatted_item = {
                "transaction_id": item.get("transaction_id"),
                "token": item.get("token"),
                "platform": item.get("platform"),
                "notification_title": item.get("notification_title"),
                "notification_body": item.get("notification_body"),
                "status": item.get("status"),
                "send_ts": int(item.get("send_ts", 0)) if item.get("send_ts") else None,
                "delivered_ts": (
                    int(item.get("delivered_ts", 0)) if item.get("delivered_ts") else None
                ),
                "failed_ts": int(item.get("failed_ts", 0)) if item.get("failed_ts") else None,
                "ap_id": item.get("ap_id"),
                "created_at": int(item.get("created_at", 0)),
            }

            # Remove None values to keep response clean
            formatted_item = {k: v for k, v in formatted_item.items() if v is not None}

            formatted_items.append(formatted_item)

        except Exception as e:
            logger.error(
                "Error formatting notification item",
                extra={"item_id": item.get("transaction_id", "unknown"), "error": str(e)},
            )
            # Continue processing other items
            continue

    logger.info(f"Formatted {len(formatted_items)} notification items")
    return formatted_items


# Initialize query service
query_service = QueryService(TABLE_NAME)


@app.get("/tx")
@tracer.capture_method
def get_transaction_notifications() -> Dict[str, Any]:
    """Query notification records by transaction_id"""
    try:
        transaction_id = app.current_event.get_query_string_value("transaction_id")
        if not transaction_id or not transaction_id.strip():
            logger.warning("Missing or empty transaction_id parameter")
            raise BadRequestError("Missing or empty transaction_id parameter")

        result = query_service.query_transaction_notifications(transaction_id)
        formatted_items = format_notification_items(result["items"])

        return {
            "success": True,
            "count": len(formatted_items),
            "items": formatted_items,
        }

    except BadRequestError:
        # Re-raise BadRequestError to let PowerTools handle it
        raise
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "UnknownError")
        logger.error(f"DynamoDB error in query_transaction: {error_code}")
        raise InternalServerError("Database connection error")
    except Exception as e:
        logger.error(f"Error in query_transaction: {str(e)}")
        raise InternalServerError("Internal server error")


@app.get("/fail")
@tracer.capture_method
def get_failed_notifications() -> Dict[str, Any]:
    """Query failed notification records - transaction_id is optional"""
    try:
        transaction_id = app.current_event.get_query_string_value("transaction_id")
        # transaction_id is optional for failed notifications query
        if transaction_id and not transaction_id.strip():
            transaction_id = None  # Treat empty string as None

        logger.info(
            f"Querying failed notifications for " f"transaction_id: {transaction_id or 'all'}"
        )

        result = query_service.query_failed_notifications(transaction_id)
        formatted_items = format_notification_items(result["items"])

        return {
            "success": True,
            "count": len(formatted_items),
            "items": formatted_items,
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "UnknownError")
        logger.error(f"DynamoDB error in query_fail: {error_code}")
        raise InternalServerError("Database connection error")
    except Exception as e:
        logger.error(f"Error in query_fail: {str(e)}")
        raise InternalServerError("Internal server error")


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_HTTP)
@tracer.capture_lambda_handler
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda function to query DynamoDB based on different criteria
    Supports both direct Lambda invocation and API Gateway events

    Version: v4 - Optimized for transaction_id based queries only
    """
    try:
        logger.info(
            "Lambda invocation started",
            extra={
                "event_type": type(event).__name__,
                "has_http_method": "httpMethod" in event,
                "has_version": "version" in event,
                "aws_request_id": (
                    getattr(context, "aws_request_id", "unknown") if context else "no_context"
                ),
            },
        )

        # Check if this is an API Gateway event
        if "httpMethod" in event or "version" in event:
            logger.info("Processing API Gateway event")
            # API Gateway format, use PowerTools resolver
            return app.resolve(event, context)  # type: ignore[no-any-return]

        # Direct Lambda invocation format - maintain backward compatibility
        body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event

        query_type = body.get("query_type")
        logger.info("Processing direct Lambda invocation", extra={"query_type": query_type})

        if query_type == "tx":
            transaction_id = body.get("transaction_id")
            if not transaction_id or not transaction_id.strip():
                logger.warning("Missing or empty transaction_id in direct invocation")
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Missing or empty transaction_id"}),
                }

            result = query_service.query_transaction_notifications(transaction_id)
            formatted_items = format_notification_items(result["items"])

        elif query_type == "fail":
            transaction_id = body.get("transaction_id")
            # transaction_id is optional for failed notifications query
            if transaction_id and not transaction_id.strip():
                transaction_id = None  # Treat empty string as None

            logger.info(
                f"Direct invocation: failed query for " f"transaction_id: {transaction_id or 'all'}"
            )

            result = query_service.query_failed_notifications(transaction_id)
            formatted_items = format_notification_items(result["items"])

        else:
            logger.warning(f"Invalid query_type in direct invocation: {query_type}")
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {
                        "error": "Invalid query_type",
                        "supported_types": ["tx", "fail"],
                    }
                ),
            }

        logger.info("Direct invocation completed successfully")
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": (
                    "Content-Type,X-Amz-Date,Authorization," "X-Api-Key,X-Amz-Security-Token"
                ),
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            },
            "body": json.dumps(
                {
                    "success": True,
                    "count": len(formatted_items),
                    "items": formatted_items,
                },
                default=decimal_to_int,
            ),
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "UnknownError")
        logger.error(f"DynamoDB error: {error_code}")
        return {
            "statusCode": 502,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Database connection error", "code": error_code}),
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Internal server error", "details": str(e)}),
        }
