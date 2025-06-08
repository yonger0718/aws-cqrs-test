import json
import os
from typing import Any, Dict

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
    def query_user_notifications(self, user_id: str) -> requests.Response:
        """Query user notification records"""
        logger.info("Starting user notifications query", extra={"user_id": user_id})
        url = f"{self.base_url}/query/user"
        payload = {"user_id": user_id}

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            logger.info(
                "User notifications query completed",
                extra={
                    "user_id": user_id,
                    "status_code": response.status_code,
                    "response_size": len(response.content),
                },
            )
            return response
        except requests.exceptions.RequestException as e:
            logger.error(
                "Failed to query user notifications", extra={"user_id": user_id, "error": str(e)}
            )
            raise

    @tracer.capture_method
    def query_marketing_notifications(self, marketing_id: str) -> requests.Response:
        """Query marketing campaign notification records"""
        logger.info("Starting marketing notifications query", extra={"marketing_id": marketing_id})
        url = f"{self.base_url}/query/marketing"
        payload = {"marketing_id": marketing_id}

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            logger.info(
                "Marketing notifications query completed",
                extra={
                    "marketing_id": marketing_id,
                    "status_code": response.status_code,
                    "response_size": len(response.content),
                },
            )
            return response
        except requests.exceptions.RequestException as e:
            logger.error(
                "Failed to query marketing notifications",
                extra={"marketing_id": marketing_id, "error": str(e)},
            )
            raise

    @tracer.capture_method
    def query_failed_notifications(self, transaction_id: str) -> requests.Response:
        """Query failed notification records"""
        logger.info("Starting failed notifications query", extra={"transaction_id": transaction_id})
        url = f"{self.base_url}/query/fail"
        payload = {"transaction_id": transaction_id}

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            logger.info(
                "Failed notifications query completed",
                extra={
                    "transaction_id": transaction_id,
                    "status_code": response.status_code,
                    "response_size": len(response.content),
                },
            )
            return response
        except requests.exceptions.RequestException as e:
            logger.error(
                "Failed to query failed notifications",
                extra={"transaction_id": transaction_id, "error": str(e)},
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


@app.get("/user")
@tracer.capture_method
def get_user_notifications() -> Dict[str, Any]:
    """Get user notifications via API Gateway"""
    user_id = app.current_event.query_string_parameters.get("user_id")

    if not user_id or not user_id.strip():
        logger.warning("Missing or empty user_id parameter")
        raise BadRequestError("Missing or empty user_id parameter")

    logger.info(f"Processing user query for user_id: {user_id}")

    try:
        response = eks_service.query_user_notifications(user_id)
        result, status_code = handle_eks_response(response)

        if status_code != 200:
            logger.warning(f"EKS service returned error: {status_code}")
            return {"error": "EKS service error", "details": result}

        logger.info("User query completed successfully")
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


@app.get("/marketing")
@tracer.capture_method
def get_marketing_notifications() -> Dict[str, Any]:
    """Get marketing notifications via API Gateway"""
    marketing_id = app.current_event.query_string_parameters.get("marketing_id")

    if not marketing_id or not marketing_id.strip():
        logger.warning("Missing or empty marketing_id parameter")
        raise BadRequestError("Missing or empty marketing_id parameter")

    logger.info(f"Processing marketing query for marketing_id: {marketing_id}")

    try:
        response = eks_service.query_marketing_notifications(marketing_id)
        result, status_code = handle_eks_response(response)

        if status_code != 200:
            logger.warning(f"EKS service returned error: {status_code}")
            return {"error": "EKS service error", "details": result}

        logger.info("Marketing query completed successfully")
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


@app.get("/fail")
@tracer.capture_method
def get_failed_notifications() -> Dict[str, Any]:
    """Get failed notifications via API Gateway"""
    transaction_id = app.current_event.query_string_parameters.get("transaction_id")

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

    Supports both API Gateway HTTP events and direct Lambda invocation for backward compatibility
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

            # Extract path and query parameters from API Gateway event
            path = event.get("path", "")
            query_params = event.get("queryStringParameters") or {}

            logger.info(f"API Gateway path: {path}, query_params: {query_params}")

            # Route based on path
            if path == "/user":
                user_id = query_params.get("user_id")
                if not user_id:
                    return {
                        "statusCode": 400,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "Missing required parameter: user_id"}),
                    }
                response = eks_service.query_user_notifications(user_id)

            elif path == "/marketing":
                marketing_id = query_params.get("marketing_id")
                if not marketing_id:
                    return {
                        "statusCode": 400,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "Missing required parameter: marketing_id"}),
                    }
                response = eks_service.query_marketing_notifications(marketing_id)

            elif path == "/fail":
                transaction_id = query_params.get("transaction_id")
                if not transaction_id:
                    return {
                        "statusCode": 400,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "Missing required parameter: transaction_id"}),
                    }
                response = eks_service.query_failed_notifications(transaction_id)

            else:
                return {
                    "statusCode": 404,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Path not found", "path": path}),
                }

            # Handle EKS handler response for API Gateway
            if response.status_code == 200:
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
                    "body": json.dumps(response.json()),
                }
            else:
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
        if "/user" in path:
            user_id = query_params.get("user_id")
            if not user_id:
                logger.warning("Missing user_id parameter in direct invocation")
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Missing required parameter: user_id"}),
                    "headers": {"Content-Type": "application/json"},
                }

            response = eks_service.query_user_notifications(user_id)

        elif "/marketing" in path:
            marketing_id = query_params.get("marketing_id")
            if not marketing_id:
                logger.warning("Missing marketing_id parameter in direct invocation")
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Missing required parameter: marketing_id"}),
                    "headers": {"Content-Type": "application/json"},
                }

            response = eks_service.query_marketing_notifications(marketing_id)

        elif "/fail" in path:
            transaction_id = query_params.get("transaction_id")
            if not transaction_id:
                logger.warning("Missing transaction_id parameter in direct invocation")
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Missing required parameter: transaction_id"}),
                    "headers": {"Content-Type": "application/json"},
                }

            response = eks_service.query_failed_notifications(transaction_id)

        else:
            logger.warning(f"Invalid query path: {path}")
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Invalid query path", "provided_path": path}),
                "headers": {"Content-Type": "application/json"},
            }

        # Handle EKS handler response
        if response.status_code == 200:
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
                "body": json.dumps(response.json()),
            }
        else:
            logger.error(
                "EKS handler returned error in direct invocation",
                extra={"status_code": response.status_code, "response_text": response.text},
            )
            return {
                "statusCode": response.status_code,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {
                        "error": "EKS handler error",
                        "details": response.text,
                        "status_code": response.status_code,
                    }
                ),
            }

    except requests.exceptions.Timeout:
        logger.error("Request timeout in direct invocation", extra={"timeout": REQUEST_TIMEOUT})
        return {
            "statusCode": 504,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Request timeout", "timeout_seconds": REQUEST_TIMEOUT}),
        }
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error in direct invocation: {str(e)}")
        return {
            "statusCode": 502,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Failed to connect to EKS handler", "details": str(e)}),
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error in direct invocation: {str(e)}")
        return {
            "statusCode": 502,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "EKS handler request failed", "details": str(e)}),
        }
    except Exception as e:
        logger.error(f"Unhandled error in lambda_handler: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Internal server error", "details": str(e)}),
        }
