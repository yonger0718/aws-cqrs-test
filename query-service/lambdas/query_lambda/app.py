import json
import os
from typing import Any, Dict

import requests

# 從環境變數取得 EKS Handler URL
EKS_HANDLER_URL = os.environ.get("EKS_HANDLER_URL", "http://eks-handler:8000")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function to handle API Gateway requests and forward to EKS handler
    """
    try:
        # 解析請求路徑和參數
        path = event.get("path", "")
        query_params = event.get("queryStringParameters", {}) or {}

        # 根據路徑決定查詢類型
        if "/user" in path:
            user_id = query_params.get("user_id")
            if not user_id:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Missing required parameter: user_id"}),
                }

            # 呼叫 EKS handler
            response = requests.post(
                f"{EKS_HANDLER_URL}/query/user", json={"user_id": user_id}, timeout=10
            )

        elif "/marketing" in path:
            marketing_id = query_params.get("marketing_id")
            if not marketing_id:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Missing required parameter: marketing_id"}),
                }

            # 呼叫 EKS handler
            response = requests.post(
                f"{EKS_HANDLER_URL}/query/marketing",
                json={"marketing_id": marketing_id},
                timeout=10,
            )

        elif "/failures" in path:
            transaction_id = query_params.get("transaction_id")
            if not transaction_id:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Missing required parameter: transaction_id"}),
                }

            # 呼叫 EKS handler
            response = requests.post(
                f"{EKS_HANDLER_URL}/query/failures",
                json={"transaction_id": transaction_id},
                timeout=10,
            )

        else:
            return {"statusCode": 404, "body": json.dumps({"error": "Invalid query path"})}

        # 檢查 EKS handler 響應
        if response.status_code == 200:
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps(response.json()),
            }
        else:
            return {
                "statusCode": response.status_code,
                "body": json.dumps({"error": "EKS handler error", "details": response.text}),
            }

    except requests.exceptions.Timeout:
        return {"statusCode": 504, "body": json.dumps({"error": "Request timeout"})}
    except requests.exceptions.RequestException as e:
        return {
            "statusCode": 502,
            "body": json.dumps({"error": "Failed to connect to EKS handler", "details": str(e)}),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error", "details": str(e)}),
        }
