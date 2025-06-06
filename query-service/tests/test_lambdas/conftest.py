"""
Lambda 測試的共享配置和 fixtures
"""

import uuid
from typing import Any, Generator

import boto3
import pytest
from moto import mock_dynamodb


@pytest.fixture(autouse=True)
def moto_dynamodb() -> Generator[None, None, None]:
    with mock_dynamodb():
        yield


@pytest.fixture(scope="function")
def dynamodb_resource() -> Generator[Any, None, None]:
    """提供 DynamoDB 資源的 fixture"""
    # 創建 DynamoDB 資源
    dynamodb = boto3.resource("dynamodb", region_name="ap-southeast-1")
    yield dynamodb


@pytest.fixture(scope="function")
def notification_records_table(dynamodb_resource: Any) -> Generator[Any, None, None]:
    """創建 notification-records 表的 fixture"""
    # 使用唯一的表名避免衝突
    table_name = f"notification-records-{uuid.uuid4().hex[:8]}"

    # 創建表
    table = dynamodb_resource.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "created_at", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "N"},
            {"AttributeName": "marketing_id", "AttributeType": "S"},
            {"AttributeName": "transaction_id", "AttributeType": "S"},
            {"AttributeName": "status", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "marketing_id-index",
                "KeySchema": [
                    {"AttributeName": "marketing_id", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            },
            {
                "IndexName": "transaction_id-status-index",
                "KeySchema": [
                    {"AttributeName": "transaction_id", "KeyType": "HASH"},
                    {"AttributeName": "status", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
            },
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )

    # 等待表創建完成
    table.wait_until_exists()

    yield table

    # 清理表（自動由 moto 處理）


@pytest.fixture(scope="function")
def notification_records_table_with_data(notification_records_table: Any) -> Any:
    """創建包含測試資料的 notification-records 表"""
    # 插入測試數據
    test_items = [
        {
            "user_id": "user123",
            "created_at": 1704038400000,
            "transaction_id": "tx001",
            "marketing_id": "campaign2024",
            "notification_title": "新年促銷",
            "status": "DELIVERED",
            "platform": "IOS",
        },
        {
            "user_id": "user123",
            "created_at": 1704038500000,
            "transaction_id": "tx002",
            "marketing_id": "campaign2024",
            "notification_title": "限時優惠",
            "status": "SENT",
            "platform": "ANDROID",
        },
        {
            "user_id": "user456",
            "created_at": 1704038600000,
            "transaction_id": "tx003",
            "marketing_id": "campaign2025",
            "notification_title": "春節活動",
            "status": "FAILED",
            "platform": "WEBPUSH",
            "error_msg": "Device token invalid",
        },
    ]

    for item in test_items:
        notification_records_table.put_item(Item=item)

    return notification_records_table


@pytest.fixture(autouse=True)
def cleanup_localstack_tables() -> Generator[None, None, None]:
    """在每個測試之前清理 LocalStack 中可能殘留的表"""
    # 在實際的 LocalStack 環境中運行時的清理邏輯
    try:
        import os

        if os.getenv("AWS_ENDPOINT_URL") or os.getenv("LOCALSTACK_ENDPOINT"):
            # 在 LocalStack 環境中
            dynamodb = boto3.resource(
                "dynamodb",
                region_name="us-east-1",
                endpoint_url=os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566"),
            )
            try:
                # 嘗試刪除可能存在的表
                table = dynamodb.Table("notification-records")
                table.delete()
                table.wait_until_not_exists()
            except Exception:
                # 表不存在，正常情況
                pass
    except Exception:
        # 導入錯誤或其他問題，忽略
        pass

    yield

    # 測試後的清理會由 moto 或 LocalStack 自動處理
