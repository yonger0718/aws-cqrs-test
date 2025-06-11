"""
Query Service 測試的共享配置和 fixtures
"""

import asyncio
import os
import uuid
from typing import Any, Dict, Generator, List
from unittest.mock import AsyncMock, Mock

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_dynamodb

# 設置測試環境變數
os.environ["AWS_DEFAULT_REGION"] = "ap-southeast-1"
os.environ["ENVIRONMENT"] = "test"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def setup_test_environment() -> Generator[None, None, None]:
    """設置測試環境"""
    # 設置環境變數
    os.environ["ENVIRONMENT"] = "test"
    os.environ["AWS_DEFAULT_REGION"] = "ap-southeast-1"
    yield
    # 清理環境變數
    if "LOCALSTACK_URL" in os.environ:
        del os.environ["LOCALSTACK_URL"]


@pytest.fixture(autouse=True)
def moto_dynamodb() -> Generator[None, None, None]:
    """啟用 moto DynamoDB mock"""
    with mock_dynamodb():
        yield


@pytest.fixture(scope="function")
def dynamodb_resource() -> Generator[Any, None, None]:
    """提供 DynamoDB 資源的 fixture"""
    # 創建 DynamoDB 資源
    dynamodb = boto3.resource("dynamodb", region_name="ap-southeast-1")
    yield dynamodb


@pytest.fixture
def mock_internal_api_adapter() -> Mock:
    """提供 mock 的 Internal API Adapter"""
    adapter = Mock()
    adapter.invoke_query_api = AsyncMock()
    return adapter


@pytest.fixture
def integration_client(mock_internal_api_adapter: Mock) -> Any:
    """提供整合測試客戶端"""
    from eks_handler.main import QueryService

    # 確保 mock_internal_api_adapter 正確設置 AsyncMock
    mock_internal_api_adapter.invoke_query_api = AsyncMock(
        return_value={
            "success": True,
            "items": [
                {
                    "transaction_id": "test-txn-1",
                    "token": "device-token-1",
                    "platform": "IOS",
                    "notification_title": "Test Notification 1",
                    "notification_body": "Test body 1",
                    "status": "DELIVERED",
                    "send_ts": 1640995200,
                    "delivered_ts": 1640995205,
                    "ap_id": "app-1",
                    "created_at": 1640995200,
                }
            ],
        }
    )

    return QueryService(mock_internal_api_adapter)


@pytest.fixture
def query_service(mock_internal_api_adapter: Mock) -> Any:
    """提供 QueryService 實例用於測試"""
    from eks_handler.main import QueryService

    return QueryService(mock_internal_api_adapter)


@pytest.fixture
def test_client() -> TestClient:
    """提供 FastAPI 測試客戶端"""
    from eks_handler.main import app

    return TestClient(app)


@pytest.fixture
def sample_notification_records() -> List[Dict[str, Any]]:
    """提供測試用的推播記錄資料"""
    return [
        {
            "transaction_id": "test-txn-1",
            "token": "device-token-1",
            "platform": "IOS",
            "notification_title": "Test Notification 1",
            "notification_body": "Test body 1",
            "status": "DELIVERED",
            "send_ts": 1640995200,
            "delivered_ts": 1640995205,
            "ap_id": "app-1",
            "created_at": 1640995200,
        },
        {
            "transaction_id": "test-txn-failed",
            "token": "device-token-2",
            "platform": "ANDROID",
            "notification_title": "Test Notification 2",
            "notification_body": "Test body 2",
            "status": "FAILED",
            "send_ts": 1640995300,
            "failed_ts": 1640995305,
            "ap_id": "app-2",
            "created_at": 1640995300,
        },
    ]


@pytest.fixture(scope="function")
def ensure_dynamodb_tables(dynamodb_resource: Any) -> Generator[Dict[str, Any], None, None]:
    """確保測試所需的 DynamoDB 表存在"""
    # 創建 command-records 表
    command_table_name = f"command-records-{uuid.uuid4().hex[:8]}"
    command_table = dynamodb_resource.create_table(
        TableName=command_table_name,
        KeySchema=[{"AttributeName": "transaction_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "transaction_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    # 創建 notification-records 表
    notification_table_name = f"notification-records-{uuid.uuid4().hex[:8]}"
    notification_table = dynamodb_resource.create_table(
        TableName=notification_table_name,
        KeySchema=[
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "created_at", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "N"},
            {"AttributeName": "transaction_id", "AttributeType": "S"},
            {"AttributeName": "status", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "transaction_id-status-index",
                "KeySchema": [
                    {"AttributeName": "transaction_id", "KeyType": "HASH"},
                    {"AttributeName": "status", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # 等待表創建完成
    command_table.wait_until_exists()
    notification_table.wait_until_exists()

    yield {
        "command_table": command_table,
        "notification_table": notification_table,
        "command_table_name": command_table_name,
        "notification_table_name": notification_table_name,
    }


@pytest.fixture
def populated_tables(
    ensure_dynamodb_tables: Dict[str, Any], sample_notification_records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """創建包含測試資料的 DynamoDB 表"""
    notification_table = ensure_dynamodb_tables["notification_table"]

    # 插入測試資料到 notification-records 表
    for record in sample_notification_records:
        # 為 notification-records 表添加必要的鍵
        item = record.copy()
        item["user_id"] = f"user-{record['transaction_id']}"
        notification_table.put_item(Item=item)

    return ensure_dynamodb_tables
