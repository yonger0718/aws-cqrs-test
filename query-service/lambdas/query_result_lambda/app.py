import json
import os
from datetime import datetime, timedelta, timezone
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

# UTC+8 timezone object
UTC_PLUS_8 = timezone(timedelta(hours=8))


def get_dynamodb_resource() -> Any:
    """Get DynamoDB resource with region configuration"""
    region = os.environ.get("AWS_REGION", "ap-southeast-1")
    endpoint_url = os.environ.get("DYNAMODB_ENDPOINT")

    if endpoint_url:
        # LocalStack development environment
        logger.info(f"Using LocalStack DynamoDB endpoint: {endpoint_url}")
        return boto3.resource("dynamodb", region_name=region, endpoint_url=endpoint_url)
    else:
        # Production environment
        logger.info(f"Using AWS DynamoDB in region: {region}")
        return boto3.resource("dynamodb", region_name=region)


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
    if hasattr(obj, "to_integral_value"):
        return int(obj.to_integral_value())
    return int(obj)


def convert_timestamp_to_utc8_string(timestamp: Optional[int]) -> Optional[str]:
    """Convert Unix timestamp to UTC+8 timezone string format"""
    if timestamp is None or timestamp == 0:
        return None

    try:
        # Convert timestamp to datetime in UTC+8
        dt = datetime.fromtimestamp(timestamp / 1000.0, tz=UTC_PLUS_8)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC+8")
    except (ValueError, TypeError, OSError) as e:
        logger.warning(f"Failed to convert timestamp {timestamp}: {e}")
        return None


class QueryService:
    """Query service for notification records with enhanced error handling"""

    def __init__(self, table_name: str):
        self.table_name = table_name
        self.table = dynamodb.Table(table_name)
        logger.info(f"QueryService initialized with table: {table_name}")

    @tracer.capture_method
    def query_transaction_notifications(
        self, transaction_id: Optional[str] = None, limit: int = 30
    ) -> Dict[str, Any]:
        """Query notification records by transaction_id or get recent records"""
        if transaction_id and transaction_id.strip():
            # 原有邏輯：查詢特定 transaction_id
            logger.info(
                "Starting transaction notifications query", extra={"transaction_id": transaction_id}
            )

            try:
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
        else:
            # 新增邏輯：查詢最新的 N 筆記錄
            logger.info(f"Starting recent transaction notifications query (limit: {limit})")

            try:
                # 使用 scan 並按 created_at 排序取得最新記錄
                response = self.table.scan(
                    ProjectionExpression=(
                        "transaction_id, #token, platform, notification_title, "
                        "notification_body, #status, send_ts, delivered_ts, "
                        "failed_ts, ap_id, created_at, sns_id"
                    ),
                    ExpressionAttributeNames={"#token": "token", "#status": "status"},
                    Limit=limit * 2,  # 多掃描一些以確保有足夠記錄排序
                )

                items = response.get("Items", [])
                consumed_capacity = response.get("ConsumedCapacity", {})

                # 按 created_at 降序排序，取最新的 limit 筆
                # 確保 created_at 是數字類型，處理 None 和字符串類型
                def safe_sort_key(item: Dict[str, Any]) -> int:
                    created_at = item.get("created_at", 0)
                    if created_at is None:
                        return 0
                    try:
                        return int(created_at) if created_at else 0
                    except (ValueError, TypeError):
                        return 0

                items.sort(key=safe_sort_key, reverse=True)
                items = items[:limit]

                logger.info(
                    "Recent transaction notifications query completed successfully",
                    extra={
                        "items_found": len(items),
                        "limit": limit,
                        "consumed_capacity": consumed_capacity,
                    },
                )

                return {"success": True, "items": items, "count": len(items)}

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "UnknownError")
                error_message = e.response.get("Error", {}).get("Message", str(e))

                logger.error(
                    "DynamoDB ClientError in recent transaction notifications query",
                    extra={
                        "error_code": error_code,
                        "error_message": error_message,
                        "limit": limit,
                    },
                )
                raise
            except Exception as e:
                logger.error(
                    "Unexpected error in recent transaction notifications query",
                    extra={"error": str(e), "limit": limit},
                )
                raise

    @tracer.capture_method
    def query_failed_notifications(self, transaction_id: Optional[str] = None) -> Dict[str, Any]:
        """Query failed notification records (status='FAILED') by optional transaction_id"""
        logger.info(f"Querying failed notifications for transaction_id: {transaction_id or 'all'}")

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

            # Log consumption details
            logger.info(
                "Query completed for failed notifications",
                extra={
                    "transaction_id": transaction_id or "all",
                    "items_count": len(items),
                    "consumed_capacity": consumed_capacity,
                },
            )

            return {
                "success": True,
                "items": items,
                "count": len(items),
                "query_info": {
                    "transaction_id": transaction_id or "all",
                    "query_type": "failed_notifications",
                },
            }

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "UnknownError")
            logger.error(
                f"DynamoDB error in query_failed_notifications: {error_code}",
                extra={"transaction_id": transaction_id or "all"},
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in query_failed_notifications: {str(e)}",
                extra={"transaction_id": transaction_id or "all"},
            )
            raise

    @tracer.capture_method
    def query_sns_notifications(self, sns_id: str) -> Dict[str, Any]:
        """Query notification records by sns_id using scan with filter"""
        logger.info(f"Querying notifications for sns_id: {sns_id}")

        try:
            # Use scan with filter since sns_id is not part of the key schema
            response = self.table.scan(
                FilterExpression=Attr("sns_id").eq(sns_id),
                ProjectionExpression=(
                    "transaction_id, #token, platform, notification_title, "
                    "notification_body, #status, send_ts, delivered_ts, "
                    "failed_ts, ap_id, created_at, sns_id"
                ),
                ExpressionAttributeNames={"#token": "token", "#status": "status"},
            )

            items = response.get("Items", [])
            consumed_capacity = response.get("ConsumedCapacity", {})

            logger.info(f"Found {len(items)} notifications for sns_id: {sns_id}")

            # Log consumption details
            logger.info(
                f"Query completed for sns_id: {sns_id}",
                extra={
                    "sns_id": sns_id,
                    "items_count": len(items),
                    "consumed_capacity": consumed_capacity,
                },
            )

            return {
                "success": True,
                "items": items,
                "count": len(items),
                "query_info": {
                    "sns_id": sns_id,
                    "query_type": "sns_notifications",
                },
            }

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "UnknownError")
            logger.error(
                f"DynamoDB error in query_sns_notifications: {error_code}",
                extra={"sns_id": sns_id},
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in query_sns_notifications: {str(e)}",
                extra={"sns_id": sns_id},
            )
            raise


def format_notification_items(items: list) -> list:
    """Format notification record items with enhanced data handling and UTC+8 timezone conversion"""
    formatted_items = []

    for item in items:
        try:
            # 安全的時間戳轉換函數
            def safe_timestamp_convert(value: Any) -> Optional[int]:
                if value is None or value == "":
                    return None
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return None

            formatted_item = {
                "transaction_id": item.get("transaction_id"),
                "token": item.get("token"),
                "platform": item.get("platform"),
                "notification_title": item.get("notification_title"),
                "notification_body": item.get("notification_body"),
                "status": item.get("status"),
                "send_ts": safe_timestamp_convert(item.get("send_ts")),
                "delivered_ts": safe_timestamp_convert(item.get("delivered_ts")),
                "failed_ts": safe_timestamp_convert(item.get("failed_ts")),
                "ap_id": item.get("ap_id"),
                "created_at": safe_timestamp_convert(item.get("created_at")) or 0,
                "sns_id": item.get("sns_id"),
            }

            # 添加 UTC+8 時間戳轉換
            formatted_item["send_time_utc8"] = convert_timestamp_to_utc8_string(
                formatted_item["send_ts"]
            )
            formatted_item["delivered_time_utc8"] = convert_timestamp_to_utc8_string(
                formatted_item["delivered_ts"]
            )
            formatted_item["failed_time_utc8"] = convert_timestamp_to_utc8_string(
                formatted_item["failed_ts"]
            )
            formatted_item["created_time_utc8"] = convert_timestamp_to_utc8_string(
                formatted_item["created_at"]
            )

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
    """Query notification records by transaction_id or get recent records"""
    try:
        transaction_id = app.current_event.get_query_string_value("transaction_id")
        limit_str = app.current_event.get_query_string_value("limit")

        # 處理 limit 參數
        limit = 30  # 預設值
        if limit_str:
            try:
                limit = int(limit_str)
                limit = max(1, min(limit, 100))  # 限制在 1-100 之間
            except ValueError:
                logger.warning(f"Invalid limit parameter: {limit_str}, using default: {limit}")

        # transaction_id 現在是可選的
        if transaction_id and not transaction_id.strip():
            transaction_id = None

        result = query_service.query_transaction_notifications(transaction_id, limit)
        formatted_items = format_notification_items(result["items"])

        # 基礎檢驗：根據查詢類型提供不同的回應
        if len(formatted_items) == 0:
            if transaction_id:
                logger.info(f"No notifications found for transaction_id: {transaction_id}")
                return {
                    "success": False,
                    "count": 0,
                    "items": [],
                    "message": f"No notifications found for transaction ID: {transaction_id}",
                }
            else:
                logger.info("No recent notifications found in the system")
                return {
                    "success": True,
                    "count": 0,
                    "items": [],
                    "message": "No recent notifications found in the system",
                }

        # 成功找到記錄
        if transaction_id:
            message = (
                f"Successfully retrieved {len(formatted_items)} "
                f"notifications for transaction ID: {transaction_id}"
            )
        else:
            message = (
                f"Successfully retrieved {len(formatted_items)} "
                f"recent notifications (limit: {limit})"
            )

        logger.info(message)
        return {
            "success": True,
            "count": len(formatted_items),
            "items": formatted_items,
            "message": message,
            "query_info": {
                "transaction_id": transaction_id,
                "limit": limit,
                "query_type": "specific" if transaction_id else "recent",
            },
        }

    except BadRequestError:
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
    """Query failed notification records by optional transaction_id"""
    try:
        transaction_id = app.current_event.get_query_string_value("transaction_id")
        # transaction_id is optional for failed notifications query
        if transaction_id and not transaction_id.strip():
            transaction_id = None

        result = query_service.query_failed_notifications(transaction_id)
        formatted_items = format_notification_items(result["items"])

        # 基礎檢驗：區分特定 transaction_id 查詢和全部失敗記錄查詢
        if len(formatted_items) == 0:
            if transaction_id:
                # 查詢特定 transaction_id 但無結果
                logger.info(f"No failed notifications found for transaction_id: {transaction_id}")
                return {
                    "statusCode": 404,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(
                        {
                            "success": False,
                            "count": 0,
                            "items": [],
                            "message": (
                                f"No failed notifications found for "
                                f"transaction ID: {transaction_id}"
                            ),
                        }
                    ),
                }
            else:
                # 查詢所有失敗記錄但無結果（這是正常情況）
                logger.info("No failed notifications found in the system")
                return {
                    "success": True,
                    "count": 0,
                    "items": [],
                    "message": "No failed notifications found in the system",
                }

        # 有找到結果或查詢所有失敗記錄
        query_target = f"transaction ID: {transaction_id}" if transaction_id else "system"
        if len(formatted_items) == 0:
            success_msg = "No failed notifications found in the system"
        else:
            success_msg = (
                f"Successfully retrieved {len(formatted_items)} "
                f"failed notifications for {query_target}"
            )
        logger.info(success_msg)

        return {
            "success": True,
            "count": len(formatted_items),
            "items": formatted_items,
            "message": success_msg,
        }

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "UnknownError")
        logger.error(f"DynamoDB error in query_failed: {error_code}")
        raise InternalServerError("Database connection error")
    except Exception as e:
        logger.error(f"Error in query_failed: {str(e)}")
        raise InternalServerError("Internal server error")


@app.get("/sns")
@tracer.capture_method
def get_sns_notifications() -> Dict[str, Any]:
    """Query notification records by sns_id"""
    try:
        sns_id = app.current_event.get_query_string_value("sns_id")
        if not sns_id or not sns_id.strip():
            logger.warning("Missing or empty sns_id parameter")
            raise BadRequestError("Missing or empty sns_id parameter")

        result = query_service.query_sns_notifications(sns_id)
        formatted_items = format_notification_items(result["items"])

        # 基礎檢驗：如果沒有找到任何結果，返回適當的訊息
        if len(formatted_items) == 0:
            logger.info(f"No notifications found for sns_id: {sns_id}")
            return {
                "success": False,
                "count": 0,
                "items": [],
                "message": f"No notifications found for SNS ID: {sns_id}",
            }

        logger.info(f"Successfully found {len(formatted_items)} notifications for sns_id: {sns_id}")
        return {
            "success": True,
            "count": len(formatted_items),
            "items": formatted_items,
            "message": (
                f"Successfully retrieved {len(formatted_items)} "
                f"notifications for SNS ID: {sns_id}"
            ),
        }

    except BadRequestError:
        # Re-raise BadRequestError to let PowerTools handle it
        raise
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "UnknownError")
        logger.error(f"DynamoDB error in query_sns: {error_code}")
        raise InternalServerError("Database connection error")
    except Exception as e:
        logger.error(f"Error in query_sns: {str(e)}")
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
            limit = body.get("limit", 30)

            # 處理 limit 參數
            try:
                limit = int(limit)
                limit = max(1, min(limit, 100))  # 限制在 1-100 之間
            except (ValueError, TypeError):
                logger.warning(f"Invalid limit parameter: {limit}, using default: 30")
                limit = 30

            # transaction_id 現在是可選的
            if transaction_id and not transaction_id.strip():
                transaction_id = None

            result = query_service.query_transaction_notifications(transaction_id, limit)
            formatted_items = format_notification_items(result["items"])

            # 基礎檢驗：根據查詢類型提供不同的回應
            if len(formatted_items) == 0:
                if transaction_id:
                    logger.info(f"No notifications found for transaction_id: {transaction_id}")
                    return {
                        "statusCode": 404,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps(
                            {
                                "success": False,
                                "count": 0,
                                "items": [],
                                "message": (
                                    f"No notifications found for "
                                    f"transaction ID: {transaction_id}"
                                ),
                            }
                        ),
                    }
                else:
                    logger.info("No recent notifications found in the system")
                    return {
                        "statusCode": 200,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps(
                            {
                                "success": True,
                                "count": 0,
                                "items": [],
                                "message": "No recent notifications found in the system",
                            }
                        ),
                    }

            # 成功找到記錄
            if transaction_id:
                message = (
                    f"Successfully retrieved {len(formatted_items)} "
                    f"notifications for transaction ID: {transaction_id}"
                )
                logger.info(message)
            else:
                message = (
                    f"Successfully retrieved {len(formatted_items)} "
                    f"recent notifications (limit: {limit})"
                )
                logger.info(message)
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
                        "message": message,
                        "query_info": {
                            "transaction_id": transaction_id,
                            "limit": limit,
                            "query_type": "specific" if transaction_id else "recent",
                        },
                    },
                    default=decimal_to_int,
                ),
            }

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

            # 基礎檢驗：區分特定 transaction_id 查詢和全部失敗記錄查詢
            if len(formatted_items) == 0:
                if transaction_id:
                    # 查詢特定 transaction_id 但無結果
                    logger.info(
                        f"No failed notifications found for transaction_id: {transaction_id}"
                    )
                    return {
                        "statusCode": 404,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps(
                            {
                                "success": False,
                                "count": 0,
                                "items": [],
                                "message": (
                                    f"No failed notifications found for "
                                    f"transaction ID: {transaction_id}"
                                ),
                            }
                        ),
                    }
                else:
                    # 查詢所有失敗記錄但無結果（這是正常情況）
                    logger.info("No failed notifications found in the system")

            # 有找到結果或查詢所有失敗記錄
            query_target = f"transaction ID: {transaction_id}" if transaction_id else "system"
            if len(formatted_items) == 0:
                success_msg = "No failed notifications found in the system"
            else:
                success_msg = (
                    f"Successfully retrieved {len(formatted_items)} "
                    f"failed notifications for {query_target}"
                )
            logger.info(success_msg)

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
                        "message": success_msg,
                    },
                    default=decimal_to_int,
                ),
            }

        elif query_type == "sns":
            sns_id = body.get("sns_id")
            if not sns_id or not sns_id.strip():
                logger.warning("Missing or empty sns_id in direct invocation")
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Missing or empty sns_id"}),
                }

            result = query_service.query_sns_notifications(sns_id)
            formatted_items = format_notification_items(result["items"])

            # 基礎檢驗：如果沒有找到任何結果，返回適當的訊息
            if len(formatted_items) == 0:
                logger.info(f"No notifications found for sns_id: {sns_id}")
                return {
                    "statusCode": 404,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(
                        {
                            "success": False,
                            "count": 0,
                            "items": [],
                            "message": f"No notifications found for SNS ID: {sns_id}",
                        }
                    ),
                }

            logger.info(
                f"Successfully found {len(formatted_items)} notifications for sns_id: {sns_id}"
            )
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

        else:
            logger.warning(f"Invalid query_type in direct invocation: {query_type}")
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {
                        "error": "Invalid query_type",
                        "supported_types": ["tx", "fail", "sns"],
                    }
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
