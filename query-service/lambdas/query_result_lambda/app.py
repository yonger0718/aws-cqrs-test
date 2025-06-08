import json
import os
from decimal import Decimal
from typing import Any, Dict

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler.api_gateway import APIGatewayHttpResolver
from aws_lambda_powertools.event_handler.exceptions import (
    BadRequestError,
    InternalServerError,
    ServiceError,
)
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.conditions import Key
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
    def query_user_notifications(self, user_id: str, limit: int = 10) -> Dict[str, Any]:
        """Query recent notification records by user_id"""
        logger.info("Starting user notifications query", extra={"user_id": user_id, "limit": limit})

        try:
            response = self.table.query(
                KeyConditionExpression=Key("user_id").eq(user_id),
                ScanIndexForward=False,  # Descending order (newest first)
                Limit=limit,
            )

            items = response.get("Items", [])
            consumed_capacity = response.get("ConsumedCapacity", {})

            logger.info(
                "User notifications query completed successfully",
                extra={
                    "user_id": user_id,
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
                "DynamoDB ClientError in user notifications query",
                extra={
                    "user_id": user_id,
                    "error_code": error_code,
                    "error_message": error_message,
                },
            )
            raise
        except BotoCoreError as e:
            logger.error(
                "BotoCoreError in user notifications query",
                extra={"user_id": user_id, "error": str(e)},
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error in user notifications query",
                extra={"user_id": user_id, "error": str(e)},
            )
            raise

    @tracer.capture_method
    def query_marketing_notifications(self, marketing_id: str) -> Dict[str, Any]:
        """Query all notification records by marketing_id"""
        logger.info("Starting marketing notifications query", extra={"marketing_id": marketing_id})

        try:
            response = self.table.query(
                IndexName="marketing_id-index",
                KeyConditionExpression=Key("marketing_id").eq(marketing_id),
                ScanIndexForward=False,  # Descending order
            )

            items = response.get("Items", [])
            consumed_capacity = response.get("ConsumedCapacity", {})

            logger.info(
                "Marketing notifications query completed successfully",
                extra={
                    "marketing_id": marketing_id,
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
                "DynamoDB ClientError in marketing notifications query",
                extra={
                    "marketing_id": marketing_id,
                    "error_code": error_code,
                    "error_message": error_message,
                },
            )
            raise
        except BotoCoreError as e:
            logger.error(
                "BotoCoreError in marketing notifications query",
                extra={"marketing_id": marketing_id, "error": str(e)},
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error in marketing notifications query",
                extra={"marketing_id": marketing_id, "error": str(e)},
            )
            raise

    @tracer.capture_method
    def query_failed_notifications(self, transaction_id: str) -> Dict[str, Any]:
        """Query failed notification records by transaction_id"""
        logger.info("Starting failed notifications query", extra={"transaction_id": transaction_id})

        try:
            response = self.table.query(
                IndexName="transaction_id-status-index",
                KeyConditionExpression=(
                    Key("transaction_id").eq(transaction_id) & Key("status").eq("FAILED")
                ),
            )

            items = response.get("Items", [])
            consumed_capacity = response.get("ConsumedCapacity", {})

            logger.info(
                "Failed notifications query completed successfully",
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
                "DynamoDB ClientError in failed notifications query",
                extra={
                    "transaction_id": transaction_id,
                    "error_code": error_code,
                    "error_message": error_message,
                },
            )
            raise
        except BotoCoreError as e:
            logger.error(
                "BotoCoreError in failed notifications query",
                extra={"transaction_id": transaction_id, "error": str(e)},
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error in failed notifications query",
                extra={"transaction_id": transaction_id, "error": str(e)},
            )
            raise


def format_notification_items(items: list) -> list:
    """Format notification record items with enhanced data handling"""
    formatted_items = []

    for item in items:
        try:
            formatted_item = {
                "user_id": item.get("user_id"),
                "created_at": int(item.get("created_at", 0)),
                "transaction_id": item.get("transaction_id"),
                "marketing_id": item.get("marketing_id"),
                "notification_title": item.get("notification_title"),
                "status": item.get("status"),
                "platform": item.get("platform"),
            }

            # Only include error_msg if it exists and is not empty
            error_msg = item.get("error_msg")
            if error_msg and error_msg.strip():
                formatted_item["error_msg"] = error_msg

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


@app.get("/user")
@tracer.capture_method
def get_user_notifications() -> Dict[str, Any]:
    """Query user notification records"""
    try:
        user_id = app.current_event.get_query_string_value("user_id")
        if not user_id or not user_id.strip():
            logger.warning("Missing or empty user_id parameter")
            raise BadRequestError("Missing or empty user_id parameter")

        # Optional limit parameter
        limit_str = app.current_event.get_query_string_value("limit")
        limit = 10  # default
        if limit_str:
            try:
                limit = int(limit_str)
                if limit <= 0 or limit > 100:
                    logger.warning(f"Invalid limit value: {limit_str}")
                    raise BadRequestError("Limit must be between 1 and 100")
            except ValueError:
                logger.warning(f"Invalid limit format: {limit_str}")
                raise BadRequestError("Limit must be a valid integer")

        result = query_service.query_user_notifications(user_id, limit)
        formatted_items = format_notification_items(result["items"])

        return {
            "success": True,
            "count": len(formatted_items),
            "items": formatted_items,
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "UnknownError")
        logger.error(f"DynamoDB error in query_user: {error_code}")
        raise ServiceError(f"Database error: {error_code}")
    except Exception as e:
        logger.error(f"Error in query_user: {str(e)}")
        raise InternalServerError("Internal server error")


@app.get("/marketing")
@tracer.capture_method
def get_marketing_notifications() -> Dict[str, Any]:
    """Query marketing campaign notification records"""
    try:
        marketing_id = app.current_event.get_query_string_value("marketing_id")
        if not marketing_id or not marketing_id.strip():
            logger.warning("Missing or empty marketing_id parameter")
            raise BadRequestError("Missing or empty marketing_id parameter")

        result = query_service.query_marketing_notifications(marketing_id)
        formatted_items = format_notification_items(result["items"])

        return {
            "success": True,
            "count": len(formatted_items),
            "items": formatted_items,
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "UnknownError")
        logger.error(f"DynamoDB error in query_marketing: {error_code}")
        raise ServiceError(f"Database error: {error_code}")
    except Exception as e:
        logger.error(f"Error in query_marketing: {str(e)}")
        raise InternalServerError("Internal server error")


@app.get("/fail")
@tracer.capture_method
def get_failed_notifications() -> Dict[str, Any]:
    """Query failed notification records"""
    try:
        transaction_id = app.current_event.get_query_string_value("transaction_id")
        if not transaction_id or not transaction_id.strip():
            logger.warning("Missing or empty transaction_id parameter")
            raise BadRequestError("Missing or empty transaction_id parameter")

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
        raise ServiceError(f"Database error: {error_code}")
    except Exception as e:
        logger.error(f"Error in query_fail: {str(e)}")
        raise InternalServerError("Internal server error")


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_HTTP)
@tracer.capture_lambda_handler
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda function to query DynamoDB based on different criteria
    Supports both direct Lambda invocation and API Gateway events
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

        if query_type == "user":
            user_id = body.get("user_id")
            if not user_id or not user_id.strip():
                logger.warning("Missing or empty user_id in direct invocation")
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Missing or empty user_id"}),
                }

            limit = body.get("limit", 10)
            if not isinstance(limit, int) or limit <= 0 or limit > 100:
                logger.warning(f"Invalid limit value in direct invocation: {limit}")
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Limit must be between 1 and 100"}),
                }

            result = query_service.query_user_notifications(user_id, limit)
            formatted_items = format_notification_items(result["items"])

        elif query_type == "marketing":
            marketing_id = body.get("marketing_id")
            if not marketing_id or not marketing_id.strip():
                logger.warning("Missing or empty marketing_id in direct invocation")
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Missing or empty marketing_id"}),
                }

            result = query_service.query_marketing_notifications(marketing_id)
            formatted_items = format_notification_items(result["items"])

        elif query_type == "fail":
            transaction_id = body.get("transaction_id")
            if not transaction_id or not transaction_id.strip():
                logger.warning("Missing or empty transaction_id in direct invocation")
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Missing or empty transaction_id"}),
                }

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
                        "supported_types": ["user", "marketing", "fail"],
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
        logger.error(f"DynamoDB ClientError in lambda_handler: {error_code}")
        return {
            "statusCode": 503,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"success": False, "error": f"Database error: {error_code}"}),
        }
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in lambda_handler: {str(e)}")
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {"success": False, "error": "Invalid JSON format", "details": str(e)}
            ),
        }
    except Exception as e:
        logger.error(f"Unhandled error in lambda_handler: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {"success": False, "error": "Internal server error", "details": str(e)}
            ),
        }
