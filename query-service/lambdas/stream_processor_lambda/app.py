import json
import logging
import os
from typing import Any, Dict

import boto3

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

READ_TABLE_NAME = "notification-records"


def transform_record(command_record: Dict[str, Any]) -> Dict[str, Any]:
    """
    將命令側的記錄轉換為查詢側的記錄格式
    """

    # 提取 DynamoDB 格式的數據
    def extract_value(item, key, default=None):
        if key not in item:
            return default

        dynamo_value = item[key]
        if "S" in dynamo_value:
            return dynamo_value["S"]
        elif "N" in dynamo_value:
            return int(dynamo_value["N"])
        elif "BOOL" in dynamo_value:
            return dynamo_value["BOOL"]
        else:
            return default

    # 轉換為查詢側需要的格式
    query_record = {
        "user_id": extract_value(command_record, "user_id"),
        "created_at": extract_value(command_record, "created_at"),
        "transaction_id": extract_value(command_record, "transaction_id"),
        "marketing_id": extract_value(command_record, "marketing_id"),
        "notification_title": extract_value(command_record, "notification_title"),
        "status": extract_value(command_record, "status"),
        "platform": extract_value(command_record, "platform"),
    }

    # 只在有錯誤訊息時才加入
    error_msg = extract_value(command_record, "error_msg")
    if error_msg:
        query_record["error_msg"] = error_msg

    # 移除 None 值
    return {k: v for k, v in query_record.items() if v is not None}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    處理 DynamoDB Stream 事件並將數據同步到讀取表
    """
    try:
        table = dynamodb.Table(READ_TABLE_NAME)
        processed_records = 0

        logger.info(f"Processing {len(event.get('Records', []))} stream records")

        for record in event.get("Records", []):
            event_name = record.get("eventName")

            logger.info(f"Processing event: {event_name}")

            if event_name in ["INSERT", "MODIFY"]:
                # 處理新增或修改事件
                dynamodb_record = record.get("dynamodb", {})
                new_image = dynamodb_record.get("NewImage", {})

                if new_image:
                    # 轉換記錄格式
                    query_record = transform_record(new_image)

                    logger.info(f"Transformed record: {query_record}")

                    # 寫入到讀取表
                    try:
                        table.put_item(Item=query_record)
                        processed_records += 1
                        logger.info(
                            f"Successfully wrote record to query table: "
                            f"{query_record['transaction_id']}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to write record to query table: {e}")
                        logger.error(f"Record: {query_record}")
                        raise

            elif event_name == "REMOVE":
                # 處理刪除事件
                dynamodb_record = record.get("dynamodb", {})
                old_image = dynamodb_record.get("OldImage", {})

                if old_image:
                    # 從讀取表中刪除對應記錄
                    transaction_id = old_image.get("transaction_id", {}).get("S")
                    user_id = old_image.get("user_id", {}).get("S")
                    created_at = old_image.get("created_at", {}).get("N")

                    if transaction_id and user_id and created_at:
                        try:
                            table.delete_item(
                                Key={"user_id": user_id, "created_at": int(created_at)}
                            )
                            processed_records += 1
                            logger.info(
                                f"Successfully deleted record from query table: {transaction_id}"
                            )
                        except Exception as e:
                            logger.error(f"Failed to delete record from query table: {e}")
                            raise

        logger.info(f"Stream processing completed. Processed {processed_records} records.")

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Stream processing completed successfully",
                    "processed_records": processed_records,
                }
            ),
        }

    except Exception as e:
        logger.error(f"Stream processing failed: {e}")
        logger.error(f"Event: {json.dumps(event, indent=2)}")

        # 在 Lambda 中，拋出異常會導致重試
        raise Exception(f"Stream processing failed: {str(e)}")


# 用於本地測試的輔助函數
def test_transform():
    """測試記錄轉換功能"""
    test_record = {
        "transaction_id": {"S": "tx_001"},
        "created_at": {"N": "1704038400000"},
        "user_id": {"S": "test_user_001"},
        "marketing_id": {"S": "campaign_2024_new_year"},
        "notification_title": {"S": "新年快樂！"},
        "status": {"S": "DELIVERED"},
        "platform": {"S": "IOS"},
    }

    result = transform_record(test_record)
    print(f"Transformed record: {json.dumps(result, indent=2)}")


if __name__ == "__main__":
    test_transform()
