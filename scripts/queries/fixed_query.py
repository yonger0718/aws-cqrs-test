#!/usr/bin/env python3
"""
修復版查詢工具
============

取代有問題的 AWS CLI，直接使用 boto3 進行 DynamoDB 操作
"""

import json
import sys

import boto3
import click
import requests
from botocore.exceptions import ClientError
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


class FixedQueryTool:
    def __init__(
        self,
        aws_endpoint="http://localhost:4566",
        eks_endpoint="http://localhost:8000",
        region="ap-southeast-1",
    ):
        """初始化查詢工具"""
        self.aws_endpoint = aws_endpoint
        self.eks_endpoint = eks_endpoint
        self.region = region

        # 設置 DynamoDB 客戶端
        self.dynamodb = boto3.client(
            "dynamodb",
            endpoint_url=aws_endpoint,
            region_name=region,
            aws_access_key_id="test",
            aws_secret_access_key="test",  # pragma: allowlist secret
        )

    def check_localstack_health(self) -> bool:
        """檢查 LocalStack 健康狀況"""
        try:
            response = requests.get(f"{self.aws_endpoint}/_localstack/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def check_eks_health(self) -> bool:
        """檢查 EKS Handler 健康狀況"""
        try:
            response = requests.get(f"{self.eks_endpoint}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def list_tables(self) -> list:
        """列出所有 DynamoDB 表"""
        try:
            response = self.dynamodb.list_tables()
            return response.get("TableNames", [])
        except ClientError as e:
            console.print(f"[red]無法列出表: {e}[/red]")
            return []

    def get_table_count(self, table_name: str) -> int:
        """獲取表的項目數量"""
        try:
            response = self.dynamodb.scan(TableName=table_name, Select="COUNT")
            return response.get("Count", 0)
        except ClientError:
            return 0

    def test_eks_query(self, endpoint: str, data: dict) -> dict:
        """測試 EKS 查詢端點"""
        try:
            response = requests.post(
                f"{self.eks_endpoint}/{endpoint}",
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def run_service_check(self):
        """檢查服務狀態"""
        console.print(Panel.fit("[bold blue]服務狀態檢查[/bold blue]"))

        # 檢查 LocalStack
        if self.check_localstack_health():
            console.print("[green]✅ LocalStack 運行中[/green]")
        else:
            console.print("[red]❌ LocalStack 未運行[/red]")
            return False

        # 檢查 EKS Handler
        if self.check_eks_health():
            console.print("[green]✅ EKS Handler 運行中[/green]")
        else:
            console.print("[red]❌ EKS Handler 未運行[/red]")
            return False

        return True

    def run_dynamodb_check(self):
        """檢查 DynamoDB 表"""
        console.print(Panel.fit("[bold blue]DynamoDB 表檢查[/bold blue]"))

        tables = self.list_tables()
        if not tables:
            console.print("[yellow]沒有找到任何 DynamoDB 表[/yellow]")
            return

        console.print(f"[green]找到 {len(tables)} 個表:[/green]")

        for table_name in tables:
            count = self.get_table_count(table_name)
            console.print(f"  - [cyan]{table_name}[/cyan]: [white]{count} 條記錄[/white]")

    def run_api_test(self):
        """測試查詢 API"""
        console.print(Panel.fit("[bold blue]API 查詢測試[/bold blue]"))

        # 測試健康檢查
        console.print("[yellow]測試健康檢查...[/yellow]")
        try:
            response = requests.get(f"{self.eks_endpoint}/health", timeout=5)
            health_data = response.json()
            console.print(
                f"[green]健康檢查結果:[/green] {json.dumps(health_data, indent=2, ensure_ascii=False)}"
            )
        except Exception as e:
            console.print(f"[red]健康檢查失敗: {e}[/red]")

        # 測試用戶查詢
        console.print("\n[yellow]測試用戶查詢...[/yellow]")
        user_result = self.test_eks_query("query/user", {"user_id": "test_user_001"})
        console.print(
            f"[cyan]用戶查詢結果:[/cyan] {json.dumps(user_result, indent=2, ensure_ascii=False)}"
        )

        # 測試行銷活動查詢
        console.print("\n[yellow]測試行銷活動查詢...[/yellow]")
        marketing_result = self.test_eks_query(
            "query/marketing", {"marketing_id": "campaign_2024_test"}
        )
        console.print(
            f"[cyan]行銷活動查詢結果:[/cyan] {json.dumps(marketing_result, indent=2, ensure_ascii=False)}"
        )

        # 測試失敗記錄查詢 (如果存在)
        console.print("\n[yellow]測試失敗記錄查詢...[/yellow]")
        fail_result = self.test_eks_query("query/fail", {"transaction_id": "tx_test_001"})
        console.print(
            f"[cyan]失敗記錄查詢結果:[/cyan] {json.dumps(fail_result, indent=2, ensure_ascii=False)}"
        )

    def run_all_checks(self):
        """執行所有檢查"""
        if not self.run_service_check():
            console.print("[red]服務檢查失敗，停止後續檢查[/red]")
            return

        console.print("\n")
        self.run_dynamodb_check()

        console.print("\n")
        self.run_api_test()


@click.command()
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["all", "services", "dynamodb", "api"]),
    default="all",
    help="檢查模式",
)
@click.option("--aws-endpoint", default="http://localhost:4566", help="AWS LocalStack 端點")
@click.option("--eks-endpoint", default="http://localhost:8000", help="EKS Handler 端點")
@click.option("--region", default="ap-southeast-1", help="AWS 區域")
def main(mode, aws_endpoint, eks_endpoint, region):
    """修復版查詢工具 - 避免 AWS CLI 相容性問題"""

    tool = FixedQueryTool(aws_endpoint, eks_endpoint, region)

    try:
        if mode == "all":
            tool.run_all_checks()
        elif mode == "services":
            tool.run_service_check()
        elif mode == "dynamodb":
            tool.run_dynamodb_check()
        elif mode == "api":
            tool.run_api_test()
    except KeyboardInterrupt:
        console.print("\n[yellow]用戶取消操作[/yellow]")
    except Exception as e:
        console.print(f"[red]發生錯誤: {e}[/red]")


if __name__ == "__main__":
    main()
