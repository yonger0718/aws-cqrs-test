#!/usr/bin/env python3
"""
DynamoDB 表檢查工具
=================

這個工具可以：
1. 檢查所有 DynamoDB 表的內容
2. 顯示表結構和數據
3. 提供詳細的統計信息
4. 支援直接連接 LocalStack
"""

import json
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3
import click
import requests
from botocore.exceptions import ClientError, EndpointConnectionError
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


class DynamoDBInspector:
    def __init__(self, endpoint_url: str = "http://localhost:4566", region: str = "ap-southeast-1"):
        """初始化 DynamoDB 檢查器"""
        self.endpoint_url = endpoint_url
        self.region = region

        # 設置 DynamoDB 客戶端
        self.dynamodb = boto3.client(
            "dynamodb",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id="test",
            aws_secret_access_key="test",  # pragma: allowlist secret
        )

        # 設置 DynamoDB 資源
        self.dynamodb_resource = boto3.resource(
            "dynamodb",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id="test",
            aws_secret_access_key="test",  # pragma: allowlist secret
        )

    def check_localstack_health(self) -> bool:
        """檢查 LocalStack 健康狀況"""
        try:
            response = requests.get(f"{self.endpoint_url}/_localstack/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def list_tables(self) -> List[str]:
        """列出所有 DynamoDB 表"""
        try:
            response = self.dynamodb.list_tables()
            return response.get("TableNames", [])
        except ClientError as e:
            console.print(f"[red]無法列出表: {e}[/red]")
            return []

    def get_table_description(self, table_name: str) -> Optional[Dict]:
        """獲取表的詳細描述"""
        try:
            response = self.dynamodb.describe_table(TableName=table_name)
            return response.get("Table", {})
        except ClientError as e:
            console.print(f"[red]無法描述表 {table_name}: {e}[/red]")
            return None

    def scan_table(self, table_name: str, limit: int = 100) -> List[Dict]:
        """掃描表並返回數據"""
        try:
            table = self.dynamodb_resource.Table(table_name)

            scan_kwargs = {"Limit": limit}

            response = table.scan(**scan_kwargs)
            items = response.get("Items", [])

            # 如果有更多數據，繼續掃描
            while "LastEvaluatedKey" in response and len(items) < limit:
                scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                response = table.scan(**scan_kwargs)
                items.extend(response.get("Items", []))

                if len(items) >= limit:
                    break

            return items[:limit]
        except ClientError as e:
            console.print(f"[red]無法掃描表 {table_name}: {e}[/red]")
            return []

    def get_table_item_count(self, table_name: str) -> int:
        """獲取表的項目總數"""
        try:
            table = self.dynamodb_resource.Table(table_name)
            return table.item_count
        except ClientError:
            # 如果無法獲取，則進行計數掃描
            try:
                response = self.dynamodb.scan(TableName=table_name, Select="COUNT")
                return response.get("Count", 0)
            except ClientError:
                return 0

    def display_table_info(self, table_name: str, description: Dict, item_count: int):
        """顯示表的基本信息"""
        table = Table(title=f"表信息: {table_name}", box=box.ROUNDED)
        table.add_column("屬性", style="cyan")
        table.add_column("值", style="white")

        # 基本信息
        table.add_row("表名", table_name)
        table.add_row("狀態", description.get("TableStatus", "Unknown"))
        table.add_row("項目數量", str(item_count))
        table.add_row("表大小 (bytes)", str(description.get("TableSizeBytes", 0)))

        # 主鍵信息
        key_schema = description.get("KeySchema", [])
        primary_keys = []
        for key in key_schema:
            key_type = key.get("KeyType", "")
            attr_name = key.get("AttributeName", "")
            primary_keys.append(f"{attr_name} ({key_type})")
        table.add_row("主鍵", ", ".join(primary_keys))

        # 屬性定義
        attributes = description.get("AttributeDefinitions", [])
        attr_info = []
        for attr in attributes:
            attr_name = attr.get("AttributeName", "")
            attr_type = attr.get("AttributeType", "")
            attr_info.append(f"{attr_name}: {attr_type}")
        table.add_row("屬性定義", "\n".join(attr_info))

        # GSI 信息
        gsi_list = description.get("GlobalSecondaryIndexes", [])
        if gsi_list:
            gsi_names = [gsi.get("IndexName", "") for gsi in gsi_list]
            table.add_row("全局二級索引", ", ".join(gsi_names))

        console.print(table)

    def display_table_data(self, table_name: str, items: List[Dict], limit: int):
        """顯示表數據"""
        if not items:
            console.print(f"[yellow]表 {table_name} 沒有數據[/yellow]")
            return

        # 創建數據表格
        data_table = Table(title=f"表數據: {table_name} (最多 {limit} 條記錄)", box=box.ROUNDED)

        # 獲取所有可能的列
        all_keys = set()
        for item in items:
            all_keys.update(item.keys())

        # 添加列
        for key in sorted(all_keys):
            data_table.add_column(key, style="white", overflow="fold")

        # 添加行
        for item in items:
            row_data = []
            for key in sorted(all_keys):
                value = item.get(key, "")
                # 處理複雜數據類型
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False, indent=2)[:100] + "..."
                else:
                    value = str(value)[:100]  # 限制長度
                row_data.append(value)
            data_table.add_row(*row_data)

        console.print(data_table)

    def inspect_all_tables(self, data_limit: int = 10):
        """檢查所有表"""
        # 檢查 LocalStack 健康狀況
        console.print(Panel.fit("[bold blue]DynamoDB 表檢查工具[/bold blue]"))

        if not self.check_localstack_health():
            console.print("[red]❌ LocalStack 連接失敗[/red]")
            return

        console.print("[green]✅ LocalStack 連接正常[/green]")

        # 列出所有表
        tables = self.list_tables()
        if not tables:
            console.print("[yellow]沒有找到任何 DynamoDB 表[/yellow]")
            return

        console.print(f"[green]找到 {len(tables)} 個表: {', '.join(tables)}[/green]\n")

        # 檢查每個表
        for table_name in tables:
            console.print(f"\n[bold cyan]正在檢查表: {table_name}[/bold cyan]")

            # 獲取表描述
            description = self.get_table_description(table_name)
            if not description:
                continue

            # 獲取項目數量
            item_count = self.get_table_item_count(table_name)

            # 顯示表信息
            self.display_table_info(table_name, description, item_count)

            # 獲取並顯示數據
            console.print(f"\n[yellow]正在掃描表數據 (最多 {data_limit} 條)...[/yellow]")
            items = self.scan_table(table_name, data_limit)
            self.display_table_data(table_name, items, data_limit)

            console.print("\n" + "=" * 80 + "\n")

    def inspect_specific_table(self, table_name: str, data_limit: int = 50):
        """檢查特定表"""
        console.print(Panel.fit(f"[bold blue]檢查表: {table_name}[/bold blue]"))

        if not self.check_localstack_health():
            console.print("[red]❌ LocalStack 連接失敗[/red]")
            return

        # 檢查表是否存在
        tables = self.list_tables()
        if table_name not in tables:
            console.print(f"[red]❌ 表 '{table_name}' 不存在[/red]")
            console.print(f"可用的表: {', '.join(tables)}")
            return

        # 獲取表描述
        description = self.get_table_description(table_name)
        if not description:
            return

        # 獲取項目數量
        item_count = self.get_table_item_count(table_name)

        # 顯示表信息
        self.display_table_info(table_name, description, item_count)

        # 獲取並顯示數據
        console.print(f"\n[yellow]正在掃描表數據 (最多 {data_limit} 條)...[/yellow]")
        items = self.scan_table(table_name, data_limit)
        self.display_table_data(table_name, items, data_limit)


@click.command()
@click.option("--table", "-t", help="檢查特定表 (留空則檢查所有表)")
@click.option("--limit", "-l", default=10, help="每個表顯示的最大記錄數 (預設: 10)")
@click.option("--endpoint", "-e", default="http://localhost:4566", help="DynamoDB 端點 URL")
@click.option("--region", "-r", default="ap-southeast-1", help="AWS 區域")
def main(table, limit, endpoint, region):
    """DynamoDB 表檢查工具"""
    inspector = DynamoDBInspector(endpoint_url=endpoint, region=region)

    try:
        if table:
            inspector.inspect_specific_table(table, limit)
        else:
            inspector.inspect_all_tables(limit)
    except KeyboardInterrupt:
        console.print("\n[yellow]用戶取消操作[/yellow]")
    except Exception as e:
        console.print(f"[red]發生錯誤: {e}[/red]")


if __name__ == "__main__":
    main()
