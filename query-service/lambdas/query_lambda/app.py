import json
import os
from typing import Any, Dict, Optional

import requests
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler.api_gateway import APIGatewayHttpResolver
from aws_lambda_powertools.event_handler.exceptions import BadRequestError, ServiceError
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext

# Environment detection
IS_LAMBDA_ENV = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None

# Initialize PowerTools
logger = Logger(disabled=not IS_LAMBDA_ENV, service="query-lambda-adapter")
tracer = Tracer(disabled=not IS_LAMBDA_ENV, service="query-lambda-adapter")
app = APIGatewayHttpResolver()

# Environment configuration
EKS_HANDLER_URL = os.environ.get("EKS_HANDLER_URL", "http://eks-handler:8000")
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "10"))


class EKSHandlerService:
    """EKS Handler service for managing external API requests"""

    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        logger.info(
            f"Initialized EKS Handler Service with URL: {self.base_url}, timeout: {self.timeout}s"
        )

    @tracer.capture_method
    def query_transaction_notifications(self, transaction_id: str) -> requests.Response:
        """Query transaction notification records"""
        logger.info(
            "Starting transaction notifications query", extra={"transaction_id": transaction_id}
        )
        url = f"{self.base_url}/query/transaction"
        payload = {"transaction_id": transaction_id}

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            logger.info(
                "Transaction notifications query completed",
                extra={
                    "transaction_id": transaction_id,
                    "status_code": response.status_code,
                    "response_size": len(response.content),
                },
            )
            return response
        except requests.exceptions.RequestException as e:
            logger.error(
                "Failed to query transaction notifications",
                extra={"transaction_id": transaction_id, "error": str(e)},
            )
            raise

    @tracer.capture_method
    def query_failed_notifications(self, transaction_id: Optional[str] = None) -> requests.Response:
        """Query failed notification records"""
        logger.info(
            "Starting failed notifications query", extra={"transaction_id": transaction_id or "all"}
        )
        url = f"{self.base_url}/query/fail"
        payload = {}
        if transaction_id and transaction_id.strip():
            payload["transaction_id"] = transaction_id

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            logger.info(
                "Failed notifications query completed",
                extra={
                    "transaction_id": transaction_id or "all",
                    "status_code": response.status_code,
                    "response_size": len(response.content),
                },
            )
            return response
        except requests.exceptions.RequestException as e:
            logger.error(
                "Failed to query failed notifications",
                extra={"transaction_id": transaction_id or "all", "error": str(e)},
            )
            raise


def handle_eks_response(response: requests.Response) -> tuple[Dict[str, Any], int]:
    """Handle EKS service response with proper error handling"""
    try:
        if response.status_code == 200:
            return response.json(), 200
        else:
            logger.warning(f"EKS handler returned error status: {response.status_code}")
            return {
                "error": "EKS handler error",
                "status_code": response.status_code,
                "details": response.text,
            }, response.status_code
    except json.JSONDecodeError:
        logger.error("Failed to parse EKS handler response as JSON")
        return {"error": "Invalid response format", "details": response.text}, 502


# Initialize EKS Handler service
eks_service = EKSHandlerService(EKS_HANDLER_URL, REQUEST_TIMEOUT)


@app.post("/tx")
@tracer.capture_method
def post_transaction_notifications() -> Dict[str, Any]:
    """Get transaction notifications via API Gateway"""
    try:
        # 從 POST 請求體中獲取參數
        body = app.current_event.json_body or {}
        transaction_id = body.get("transaction_id")
    except Exception:
        # 如果解析 JSON 失敗，嘗試從 query string 獲取（向後兼容）
        transaction_id = (
            app.current_event.query_string_parameters.get("transaction_id")
            if app.current_event.query_string_parameters
            else None
        )

    if not transaction_id or not transaction_id.strip():
        logger.warning("Missing or empty transaction_id parameter")
        raise BadRequestError("Missing or empty transaction_id parameter")

    logger.info(f"Processing transaction query for transaction_id: {transaction_id}")

    try:
        response = eks_service.query_transaction_notifications(transaction_id)
        result, status_code = handle_eks_response(response)

        if status_code != 200:
            logger.warning(f"EKS service returned error: {status_code}")
            return {"error": "EKS service error", "details": result}

        logger.info("Transaction query completed successfully")
        return result

    except requests.exceptions.Timeout:
        logger.error("Request to EKS handler timed out")
        raise ServiceError("Request timeout")
    except requests.exceptions.ConnectionError:
        logger.error("Failed to connect to EKS handler")
        raise ServiceError("Service unavailable")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request to EKS handler failed: {str(e)}")
        raise ServiceError("Request failed")


@app.post("/fail")
@tracer.capture_method
def post_failed_notifications() -> Dict[str, Any]:
    """Get failed notifications via API Gateway"""
    try:
        # 從 POST 請求體中獲取參數
        body = app.current_event.json_body or {}
        transaction_id = body.get("transaction_id")
    except Exception:
        # 如果解析 JSON 失敗，嘗試從 query string 獲取（向後兼容）
        transaction_id = (
            app.current_event.query_string_parameters.get("transaction_id")
            if app.current_event.query_string_parameters
            else None
        )

    if not transaction_id or not transaction_id.strip():
        logger.warning("Missing or empty transaction_id parameter")
        raise BadRequestError("Missing or empty transaction_id parameter")

    logger.info(f"Processing failed query for transaction_id: {transaction_id}")

    try:
        response = eks_service.query_failed_notifications(transaction_id)
        result, status_code = handle_eks_response(response)

        if status_code != 200:
            logger.warning(f"EKS service returned error: {status_code}")
            return {"error": "EKS service error", "details": result}

        logger.info("Failed query completed successfully")
        return result

    except requests.exceptions.Timeout:
        logger.error("Request to EKS handler timed out")
        raise ServiceError("Request timeout")
    except requests.exceptions.ConnectionError:
        logger.error("Failed to connect to EKS handler")
        raise ServiceError("Service unavailable")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request to EKS handler failed: {str(e)}")
        raise ServiceError("Request failed")


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_HTTP)
@tracer.capture_lambda_handler
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda function to handle API Gateway requests and forward to EKS handler

    Version: v4 - Optimized for transaction_id based queries only
    Supports both API Gateway HTTP events and direct Lambda invocation for backward compatibility
    """
    try:
        request_id = getattr(context, "aws_request_id", "unknown") if context else "no_context"
        logger.info(
            "Lambda invocation started",
            extra={
                "event_type": type(event).__name__,
                "has_http_method": "httpMethod" in event,
                "has_version": "version" in event,
                "aws_request_id": request_id,
                "event_keys": list(event.keys()),
            },
        )

        # Log the complete event structure for debugging
        logger.debug(f"Complete event structure: {json.dumps(event, indent=2, default=str)}")

        # Check if this is an API Gateway event
        if "httpMethod" in event or "version" in event:
            logger.info("Processing API Gateway event")
            http_method = event.get(
                "httpMethod", event.get("requestContext", {}).get("http", {}).get("method", "")
            )

            # Extract path and query parameters from API Gateway event
            # Support both REST API and HTTP API v2.0 formats
            path = event.get("path") or event.get("rawPath", "")

            # Also try to get path from requestContext for HTTP API v2.0
            if not path and "requestContext" in event:
                request_context = event["requestContext"]
                if "http" in request_context:
                    path = request_context["http"].get("path", "")

            query_params = event.get("queryStringParameters") or {}
            body_str = event.get("body", "")

            logger.info(
                "API Gateway request details",
                extra={
                    "method": http_method,
                    "path": path,
                    "query_params": query_params,
                    "has_body": bool(body_str),
                    "content_type": event.get("headers", {}).get("content-type", ""),
                },
            )

            # Route based on path - support /tx, /query/transaction, and /query/tx patterns
            if path in ["/tx", "/query/transaction", "/query/tx"]:
                logger.info("Processing transaction query request")

                # Get transaction_id from query parameters or body
                transaction_id = None
                if query_params:
                    transaction_id = query_params.get("transaction_id")
                    logger.info(f"Transaction ID from query params: {transaction_id}")

                # If no transaction_id in query params, try body (for POST requests)
                if not transaction_id and body_str:
                    try:
                        body_data = json.loads(body_str)
                        transaction_id = body_data.get("transaction_id")
                        logger.info(f"Transaction ID from body: {transaction_id}")
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse request body: {e}")

                if not transaction_id:
                    logger.error("Missing transaction_id parameter")
                    return {
                        "statusCode": 400,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "Missing required parameter: transaction_id"}),
                    }

                logger.info(
                    f"Forwarding transaction query to EKS handler for "
                    f"transaction_id: {transaction_id}"
                )
                response = eks_service.query_transaction_notifications(transaction_id)

            elif path in ["/fail", "/query/fail"]:
                logger.info("Processing failed notifications query request")

                # Get transaction_id from query parameters or body (optional for failed queries)
                transaction_id = None
                if query_params:
                    transaction_id = query_params.get("transaction_id")
                    logger.info(f"Transaction ID from query params: {transaction_id}")

                # If no transaction_id in query params, try body
                if not transaction_id and body_str:
                    try:
                        body_data = json.loads(body_str)
                        transaction_id = body_data.get("transaction_id")
                        logger.info(f"Transaction ID from body: {transaction_id}")
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse request body: {e}")

                # For failed queries, transaction_id is optional
                # (can query all failed notifications)
                logger.info(
                    f"Forwarding failed query to EKS handler for "
                    f"transaction_id: {transaction_id or 'all'}"
                )
                response = eks_service.query_failed_notifications(transaction_id)

            else:
                logger.warning(f"Unmatched path: {path}")
                return {
                    "statusCode": 404,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(
                        {
                            "error": "Path not found",
                            "path": path,
                            "available_paths": ["/tx", "/fail"],
                        }
                    ),
                }

            # Handle EKS handler response for API Gateway
            logger.info(f"EKS handler response status: {response.status_code}")

            if response.status_code == 200:
                logger.info("Request processed successfully")
                response_data = response.json()
                logger.info(f"Response contains {response_data.get('count', 0)} items")

                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": (
                            "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token"
                        ),
                        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
                    },
                    "body": json.dumps(response_data),
                }
            else:
                logger.error(f"EKS handler returned error: {response.status_code}, {response.text}")
                return {
                    "statusCode": response.status_code,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "EKS handler error", "details": response.text}),
                }

        # Direct Lambda invocation format - maintain backward compatibility
        path = event.get("path", "")
        query_params = event.get("queryStringParameters", {}) or {}

        logger.info(
            "Processing direct Lambda invocation",
            extra={"path": path, "query_params": list(query_params.keys())},
        )

        # Route based on path
        if "/tx" in path:
            transaction_id = query_params.get("transaction_id")
            if not transaction_id:
                logger.warning("Missing transaction_id parameter in direct invocation")
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Missing required parameter: transaction_id"}),
                    "headers": {"Content-Type": "application/json"},
                }

            logger.info(f"Direct invocation: transaction query for {transaction_id}")
            response = eks_service.query_transaction_notifications(transaction_id)

        elif "/fail" in path:
            transaction_id = query_params.get("transaction_id", "")  # Optional for failed queries
            logger.info(f"Direct invocation: failed query for {transaction_id or 'all'}")
            response = eks_service.query_failed_notifications(transaction_id)

        else:
            logger.warning(f"Unmatched path for direct invocation: {path}")
            return {
                "statusCode": 404,
                "body": json.dumps(
                    {"error": "Path not found", "supported_paths": ["/tx", "/fail"]}
                ),
                "headers": {"Content-Type": "application/json"},
            }

        # Handle response for direct invocation
        logger.info(f"Direct invocation response status: {response.status_code}")
        if response.status_code == 200:
            response_data = response.json()
            logger.info(
                f"Direct invocation successful, " f"{response_data.get('count', 0)} items returned"
            )
            return {"statusCode": 200, "body": json.dumps(response_data)}
        else:
            logger.error(f"Direct invocation failed: {response.status_code}, {response.text}")
            return {"statusCode": response.status_code, "body": response.text}

    except requests.exceptions.Timeout:
        logger.error("Request timeout")
        return {
            "statusCode": 504,
            "body": json.dumps({"error": "Request timeout"}),
            "headers": {"Content-Type": "application/json"},
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        return {
            "statusCode": 502,
            "body": json.dumps({"error": "Service unavailable", "details": str(e)}),
            "headers": {"Content-Type": "application/json"},
        }
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error", "details": str(e)}),
            "headers": {"Content-Type": "application/json"},
        }
