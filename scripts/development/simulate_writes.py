#!/usr/bin/env python3

import json
import random
import time
from datetime import datetime
from typing import Optional

import boto3

# 設置 LocalStack DynamoDB 客戶端
dynamodb = boto3.resource(
    "dynamodb",
    endpoint_url="http://localhost:4566",
    region_name="us-east-1",
    aws_access_key_id="test",
    aws_secret_access_key="test",
)

COMMAND_TABLE_NAME = "command-records"


def generate_notification_record(
    transaction_id: str, user_id: str, marketing_id: Optional[str] = None
):
    """產生模擬的通知記錄"""
    current_time = int(datetime.now().timestamp() * 1000)

    platforms = ["IOS", "ANDROID", "WEBPUSH"]
    statuses = ["SENT", "DELIVERED", "FAILED"]

    platform = random.choice(platforms)
    status = random.choice(statuses)

    record = {
        "transaction_id": transaction_id,
        "created_at": current_time,
        "user_id": user_id,
        "platform": platform,
        "status": status,
        "notification_title": f"測試通知 - {transaction_id}",
        "device_token": f"{platform.lower()}_token_{random.randint(1000, 9999)}",
        "payload": json.dumps(
            {"title": f"測試通知 - {transaction_id}", "body": f"這是針對用戶 {user_id} 的測試推播"},
            ensure_ascii=False,
        ),
    }

    if marketing_id:
        record["marketing_id"] = marketing_id

    if status == "FAILED":
        error_messages = [
            "Device token invalid",
            "Network timeout",
            "Service unavailable",
            "Rate limit exceeded",
        ]
        record["error_msg"] = random.choice(error_messages)

    return record


def write_to_command_table(record):
    """寫入到命令表"""
    table = dynamodb.Table(COMMAND_TABLE_NAME)

    try:
        table.put_item(Item=record)
        print(f"✅ 成功寫入記錄: {record['transaction_id']}")
        return True
    except Exception as e:
        print(f"❌ 寫入失敗: {e}")
        return False


def simulate_batch_notifications():
    """模擬批次推播"""
    print("🚀 開始模擬批次推播...")

    # 模擬一個行銷活動的推播
    marketing_id = "campaign_2024_test"
    users = ["user_001", "user_002", "user_003", "user_004", "user_005"]

    for i, user in enumerate(users):
        transaction_id = f"tx_batch_{int(time.time())}_{i}"
        record = generate_notification_record(transaction_id, user, marketing_id)

        if write_to_command_table(record):
            print(f"   用戶 {user}: {record['status']}")

        # 稍微延遲以避免時間戳衝突
        time.sleep(0.1)

    print("✅ 批次推播模擬完成")


def simulate_individual_notification():
    """模擬單個推播"""
    print("📱 模擬單個推播...")

    transaction_id = f"tx_individual_{int(time.time())}"
    user_id = f"user_{random.randint(100, 999)}"

    record = generate_notification_record(transaction_id, user_id)

    if write_to_command_table(record):
        print(f"   推播給 {user_id}: {record['status']}")

    print("✅ 單個推播模擬完成")


def simulate_update_status():
    """模擬狀態更新（從 SENT 到 DELIVERED 或 FAILED）"""
    print("🔄 模擬狀態更新...")

    # 首先創建一個 SENT 狀態的記錄
    transaction_id = f"tx_update_{int(time.time())}"
    user_id = f"user_update_{random.randint(100, 999)}"

    # 初始記錄（SENT 狀態）
    initial_record = generate_notification_record(transaction_id, user_id)
    initial_record["status"] = "SENT"

    print(f"   創建初始記錄: {transaction_id} (SENT)")
    write_to_command_table(initial_record)

    time.sleep(2)  # 等待 2 秒

    # 更新狀態
    updated_record = initial_record.copy()
    updated_record["status"] = random.choice(["DELIVERED", "FAILED"])
    updated_record["created_at"] = int(datetime.now().timestamp() * 1000)

    if updated_record["status"] == "FAILED":
        updated_record["error_msg"] = "Delivery failed after retry"

    print(f"   更新記錄狀態: {transaction_id} ({updated_record['status']})")
    write_to_command_table(updated_record)

    print("✅ 狀態更新模擬完成")


def main():
    print("🎯 DynamoDB Stream 測試腳本")
    print("=" * 50)

    while True:
        print("\n請選擇測試類型:")
        print("1. 模擬批次推播")
        print("2. 模擬單個推播")
        print("3. 模擬狀態更新")
        print("4. 退出")

        choice = input("\n請輸入選項 (1-4): ").strip()

        if choice == "1":
            simulate_batch_notifications()
        elif choice == "2":
            simulate_individual_notification()
        elif choice == "3":
            simulate_update_status()
        elif choice == "4":
            print("👋 測試結束")
            break
        else:
            print("❌ 無效選項，請重新選擇")

        print("\n" + "=" * 50)


if __name__ == "__main__":
    main()
