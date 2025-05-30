#!/usr/bin/env python3

import boto3

# 建立 DynamoDB 客戶端
dynamodb_client = boto3.client(
    "dynamodb",
    endpoint_url="http://localhost:4566",
    region_name="us-east-1",
    aws_access_key_id="test",
    aws_secret_access_key="test",
)


def check_tables():
    """檢查所有 DynamoDB 表及其結構"""
    try:
        # 列出所有表
        tables_response = dynamodb_client.list_tables()
        tables = tables_response.get("TableNames", [])

        print("🔍 LocalStack DynamoDB 表列表:")
        print("=" * 50)

        if not tables:
            print("❌ 沒有找到任何表")
            return

        for table_name in tables:
            print(f"\n📋 表名: {table_name}")
            print("-" * 30)

            # 獲取表詳細信息
            table_desc = dynamodb_client.describe_table(TableName=table_name)
            table_info = table_desc["Table"]

            # 顯示關鍵信息
            print(f"狀態: {table_info.get('TableStatus', 'Unknown')}")

            # 主鍵結構
            key_schema = table_info.get("KeySchema", [])
            print("主鍵結構:")
            for key in key_schema:
                print(f"  - {key['AttributeName']} ({key['KeyType']})")

            # 屬性定義
            attributes = table_info.get("AttributeDefinitions", [])
            print("屬性定義:")
            for attr in attributes:
                print(f"  - {attr['AttributeName']}: {attr['AttributeType']}")

            # 查看一些樣本數據
            try:
                scan_response = dynamodb_client.scan(TableName=table_name, Limit=3)
                items = scan_response.get("Items", [])
                print("樣本數據 (前3筆):")
                if items:
                    for i, item in enumerate(items, 1):
                        print(f"  記錄 {i}:")
                        for key, value in item.items():
                            # 簡化顯示
                            if "S" in value:
                                print(f"    {key}: '{value['S']}'")
                            elif "N" in value:
                                print(f"    {key}: {value['N']}")
                            else:
                                print(f"    {key}: {value}")
                else:
                    print("  (沒有數據)")
            except Exception as e:
                print(f"  ❌ 無法讀取數據: {e}")

    except Exception as e:
        print(f"❌ 錯誤: {e}")


if __name__ == "__main__":
    check_tables()
