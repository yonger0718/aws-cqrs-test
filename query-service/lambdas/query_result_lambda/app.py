import json
import os
from decimal import Decimal
from typing import Any, Dict

import boto3
from boto3.dynamodb.conditions import Key

# 初始化 DynamoDB 客戶端
if os.environ.get("LOCALSTACK_HOSTNAME"):
    # LocalStack 環境
    dynamodb = boto3.resource(
        "dynamodb",
        endpoint_url="http://localstack:4566",
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
else:
    # AWS 環境
    dynamodb = boto3.resource("dynamodb")

TABLE_NAME = "notification-records"


def decimal_to_int(obj: Any) -> int:
    """Convert Decimal objects to int for JSON serialization"""
    if isinstance(obj, Decimal):
        return int(obj)
    raise TypeError


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function to query DynamoDB based on different criteria
    Supports both direct Lambda invocation and API Gateway events
    """
    try:
        # 解析請求 - 支持 API Gateway 和直接調用
        if "queryStringParameters" in event:
            # API Gateway 事件格式
            query_params = event.get("queryStringParameters") or {}
            path = event.get("path", "")

            # 根據路徑和參數構建查詢
            if "/query/user" in path:
                body = {"query_type": "user", "user_id": query_params.get("user_id")}
            elif "/query/marketing" in path:
                body = {"query_type": "marketing", "marketing_id": query_params.get("marketing_id")}
            elif "/query/failures" in path:
                body = {
                    "query_type": "failures",
                    "transaction_id": query_params.get("transaction_id"),
                }
            else:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Invalid path"}),
                }
        else:
            # 直接 Lambda 調用格式
            body = (
                json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event
            )

        query_type = body.get("query_type")

        table = dynamodb.Table(TABLE_NAME)

        if query_type == "user":
            # 根據 user_id 查詢最近的推播紀錄
            user_id = body.get("user_id")
            if not user_id:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Missing user_id"}),
                }

            response = table.query(
                KeyConditionExpression=Key("user_id").eq(user_id),
                ScanIndexForward=False,  # 倒序排列（最新的在前）
                Limit=10,  # 最多返回 10 筆
            )

            items = response.get("Items", [])

        elif query_type == "marketing":
            # 根據 marketing_id 查詢所有推播紀錄
            marketing_id = body.get("marketing_id")
            if not marketing_id:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Missing marketing_id"}),
                }

            response = table.query(
                IndexName="marketing_id-index",
                KeyConditionExpression=Key("marketing_id").eq(marketing_id),
                ScanIndexForward=False,  # 倒序排列
            )

            items = response.get("Items", [])

        elif query_type == "failures":
            # 根據 transaction_id 查詢失敗的推播紀錄
            transaction_id = body.get("transaction_id")
            if not transaction_id:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Missing transaction_id"}),
                }

            response = table.query(
                IndexName="transaction_id-status-index",
                KeyConditionExpression=(
                    Key("transaction_id").eq(transaction_id) & Key("status").eq("FAILED")
                ),
            )

            items = response.get("Items", [])

        else:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid query_type"}),
            }

        # 格式化結果
        formatted_items = []
        for item in items:
            formatted_item = {
                "user_id": item.get("user_id"),
                "created_at": int(item.get("created_at", 0)),
                "transaction_id": item.get("transaction_id"),
                "marketing_id": item.get("marketing_id"),
                "notification_title": item.get("notification_title"),
                "status": item.get("status"),
                "platform": item.get("platform"),
            }

            # 只在有 error_msg 時才加入
            if item.get("error_msg"):
                formatted_item["error_msg"] = item.get("error_msg")

            formatted_items.append(formatted_item)

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "success": True,
                    "count": len(formatted_items),
                    "items": formatted_items,
                },
                default=decimal_to_int,
            ),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"success": False, "error": "Internal server error", "details": str(e)}
            ),
        }
