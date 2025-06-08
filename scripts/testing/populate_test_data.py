#!/usr/bin/env python3
"""
測試數據填充工具
==============

為 DynamoDB 表填充測試數據，用於測試查詢功能
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List

import boto3
import click
from botocore.exceptions import ClientError
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class TestDataPopulator:
    def __init__(self, endpoint_url="http://localhost:4566", region="ap-southeast-1"):
        """初始化測試數據填充器"""
        self.endpoint_url = endpoint_url
        self.region = region

        # 設置 DynamoDB 資源
        self.dynamodb = boto3.resource(
            "dynamodb",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id="test",
            aws_secret_access_key="test",  # pragma: allowlist secret
        )

    def check_table_exists(self, table_name: str) -> bool:
        """檢查表是否存在"""
        try:
            table = self.dynamodb.Table(table_name)
            table.load()
            return True
        except ClientError:
            return False

    def populate_command_records(self, count: int = 10) -> bool:
        """填充 command-records 表"""
        table_name = "command-records"

        if not self.check_table_exists(table_name):
            console.print(f"[red]表 {table_name} 不存在[/red]")
            return False

        table = self.dynamodb.Table(table_name)

        console.print(f"[yellow]正在填充 {table_name} 表...[/yellow]")

        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            task = progress.add_task(f"插入 {count} 條記錄", total=count)

            for i in range(count):
                timestamp = datetime.now(timezone.utc).isoformat()
                transaction_id = f"tx_{uuid.uuid4().hex[:8]}"

                item = {
                    "transaction_id": transaction_id,
                    "user_id": f"test_user_{i:03d}",
                    "marketing_id": f'campaign_2024_{["new_year", "spring", "summer", "autumn"][i % 4]}',
                    "ap_id": f"ap_{uuid.uuid4().hex[:6]}",
                    "message": f"測試推播訊息 {i+1}",
                    "channel": ["email", "sms", "push"][i % 3],
                    "status": ["sent", "pending", "failed"][i % 3],
                    "timestamp": timestamp,
                    "metadata": {
                        "device_type": ["ios", "android", "web"][i % 3],
                        "locale": ["zh-TW", "en-US"][i % 2],
                        "test_data": True,
                    },
                }

                try:
                    table.put_item(Item=item)
                    progress.update(task, advance=1)
                except ClientError as e:
                    console.print(f"[red]插入失敗: {e}[/red]")
                    return False

        console.print(f"[green]✅ 成功填充 {count} 條記錄到 {table_name}[/green]")
        return True

    def populate_notification_records(self, count: int = 15) -> bool:
        """填充 notification-records 表"""
        table_name = "notification-records"

        if not self.check_table_exists(table_name):
            console.print(f"[red]表 {table_name} 不存在[/red]")
            return False

        table = self.dynamodb.Table(table_name)

        console.print(f"[yellow]正在填充 {table_name} 表...[/yellow]")

        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            task = progress.add_task(f"插入 {count} 條記錄", total=count)

            for i in range(count):
                timestamp = datetime.now(timezone.utc).isoformat()
                record_id = f"record_{uuid.uuid4().hex[:8]}"

                item = {
                    "record_id": record_id,
                    "user_id": f"test_user_{i:03d}",
                    "marketing_id": f'campaign_2024_{["new_year", "spring", "summer", "autumn"][i % 4]}',
                    "transaction_id": f"tx_{uuid.uuid4().hex[:8]}",
                    "message": f"查詢最佳化記錄 {i+1}",
                    "status": ["delivered", "read", "clicked", "failed"][i % 4],
                    "channel": ["email", "sms", "push", "app"][i % 4],
                    "timestamp": timestamp,
                    "delivered_at": timestamp if i % 4 != 3 else None,
                    "read_at": timestamp if i % 5 == 0 else None,
                    "clicked_at": timestamp if i % 7 == 0 else None,
                    "metadata": {
                        "campaign_type": ["promotional", "transactional", "reminder"][i % 3],
                        "priority": ["high", "medium", "low"][i % 3],
                        "test_data": True,
                    },
                }

                try:
                    table.put_item(Item=item)
                    progress.update(task, advance=1)
                except ClientError as e:
                    console.print(f"[red]插入失敗: {e}[/red]")
                    return False

        console.print(f"[green]✅ 成功填充 {count} 條記錄到 {table_name}[/green]")
        return True

    def clear_test_data(self, table_name: str) -> bool:
        """清除測試數據"""
        if not self.check_table_exists(table_name):
            console.print(f"[red]表 {table_name} 不存在[/red]")
            return False

        table = self.dynamodb.Table(table_name)

        console.print(f"[yellow]正在清除 {table_name} 的測試數據...[/yellow]")

        try:
            # 掃描並刪除包含 test_data: True 的項目
            response = table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr("metadata.test_data").eq(True)
            )

            items = response.get("Items", [])

            if not items:
                console.print(f"[yellow]表 {table_name} 中沒有測試數據[/yellow]")
                return True

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(f"刪除 {len(items)} 條測試記錄", total=len(items))

                for item in items:
                    # 獲取主鍵
                    if table_name == "command-records":
                        key = {"transaction_id": item["transaction_id"]}
                    else:  # notification-records
                        key = {"record_id": item["record_id"]}

                    table.delete_item(Key=key)
                    progress.update(task, advance=1)

            console.print(f"[green]✅ 成功清除 {len(items)} 條測試記錄[/green]")
            return True

        except ClientError as e:
            console.print(f"[red]清除失敗: {e}[/red]")
            return False

    def populate_all_tables(self, command_count: int = 10, notification_count: int = 15) -> bool:
        """填充所有表"""
        console.print(Panel.fit("[bold blue]填充測試數據[/bold blue]"))

        success = True
        success &= self.populate_command_records(command_count)
        success &= self.populate_notification_records(notification_count)

        if success:
            console.print("\n[green]✅ 所有表填充完成[/green]")
        else:
            console.print("\n[red]❌ 部分表填充失敗[/red]")

        return success


@click.command()
@click.option(
    "--action",
    "-a",
    type=click.Choice(["populate", "clear", "populate-command", "populate-notification"]),
    default="populate",
    help="執行的動作",
)
@click.option("--command-count", "-c", default=10, help="command-records 表的記錄數")
@click.option("--notification-count", "-n", default=15, help="notification-records 表的記錄數")
@click.option("--endpoint", default="http://localhost:4566", help="DynamoDB 端點 URL")
@click.option("--region", default="ap-southeast-1", help="AWS 區域")
def main(action, command_count, notification_count, endpoint, region):
    """測試數據填充工具"""

    populator = TestDataPopulator(endpoint, region)

    try:
        if action == "populate":
            populator.populate_all_tables(command_count, notification_count)
        elif action == "populate-command":
            populator.populate_command_records(command_count)
        elif action == "populate-notification":
            populator.populate_notification_records(notification_count)
        elif action == "clear":
            populator.clear_test_data("command-records")
            populator.clear_test_data("notification-records")
    except KeyboardInterrupt:
        console.print("\n[yellow]用戶取消操作[/yellow]")
    except Exception as e:
        console.print(f"[red]發生錯誤: {e}[/red]")


if __name__ == "__main__":
    main()
