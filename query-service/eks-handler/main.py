import json
import logging
import os

import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化 FastAPI
app = FastAPI(title="Query Service EKS Handler")

# 初始化 Lambda 客戶端
LOCALSTACK_ENDPOINT = os.environ.get("LOCALSTACK_ENDPOINT", "http://localstack:4566")

lambda_client = boto3.client(
    "lambda",
    endpoint_url=LOCALSTACK_ENDPOINT,
    region_name="us-east-1",
    aws_access_key_id="test",
    aws_secret_access_key="test",
)


# Pydantic 模型
class UserQueryRequest(BaseModel):
    user_id: str


class MarketingQueryRequest(BaseModel):
    marketing_id: str


class FailuresQueryRequest(BaseModel):
    transaction_id: str


# 健康檢查
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "query-service-eks-handler"}


# 查詢用戶推播紀錄
@app.post("/query/user")
async def query_user_notifications(request: UserQueryRequest):
    """
    根據 user_id 查詢該用戶最近的推播紀錄
    """
    try:
        logger.info(f"Querying notifications for user: {request.user_id}")

        # 呼叫 query_result_lambda
        payload = {"query_type": "user", "user_id": request.user_id}

        response = lambda_client.invoke(
            FunctionName="query_result_lambda",
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )

        # 解析響應
        result = json.loads(response["Payload"].read())

        if "body" in result:
            body = json.loads(result["body"])
            return body
        else:
            return result

    except ClientError as e:
        logger.error(f"Lambda invocation error: {e}")
        raise HTTPException(status_code=502, detail="Failed to invoke Lambda function")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 查詢活動推播紀錄
@app.post("/query/marketing")
async def query_marketing_notifications(request: MarketingQueryRequest):
    """
    根據 marketing_id 查詢某活動所觸發的所有推播紀錄
    """
    try:
        logger.info(f"Querying notifications for marketing campaign: {request.marketing_id}")

        # 呼叫 query_result_lambda
        payload = {"query_type": "marketing", "marketing_id": request.marketing_id}

        response = lambda_client.invoke(
            FunctionName="query_result_lambda",
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )

        # 解析響應
        result = json.loads(response["Payload"].read())

        if "body" in result:
            body = json.loads(result["body"])
            return body
        else:
            return result

    except ClientError as e:
        logger.error(f"Lambda invocation error: {e}")
        raise HTTPException(status_code=502, detail="Failed to invoke Lambda function")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 查詢失敗的推播紀錄
@app.post("/query/failures")
async def query_failed_notifications(request: FailuresQueryRequest):
    """
    根據 transaction_id 查詢失敗的推播紀錄
    """
    try:
        logger.info(f"Querying failed notifications for transaction: {request.transaction_id}")

        # 呼叫 query_result_lambda
        payload = {"query_type": "failures", "transaction_id": request.transaction_id}

        response = lambda_client.invoke(
            FunctionName="query_result_lambda",
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )

        # 解析響應
        result = json.loads(response["Payload"].read())

        if "body" in result:
            body = json.loads(result["body"])
            return body
        else:
            return result

    except ClientError as e:
        logger.error(f"Lambda invocation error: {e}")
        raise HTTPException(status_code=502, detail="Failed to invoke Lambda function")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 根目錄
@app.get("/")
async def root():
    return {
        "service": "Query Service EKS Handler",
        "version": "1.0.0",
        "endpoints": ["/query/user", "/query/marketing", "/query/failures"],
    }


if __name__ == "__main__":
    import uvicorn

    # 使用環境變數設置主機以避免安全警告
    host = os.environ.get("HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=8000)
