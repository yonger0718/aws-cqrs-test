#!/usr/bin/env python3
"""
API Gateway 輔助工具
==================

用於替代有問題的 AWS CLI，提供 API Gateway 相關操作
"""

import json
import sys

import boto3
import click
from botocore.exceptions import ClientError


class APIGatewayHelper:
    def __init__(self, endpoint_url="http://localhost:4566", region="ap-southeast-1"):
        """初始化 API Gateway 輔助工具"""
        self.endpoint_url = endpoint_url
        self.region = region

        # 設置 API Gateway 客戶端
        self.apigateway = boto3.client(
            "apigateway",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id="test",
            aws_secret_access_key="test",  # pragma: allowlist secret
        )

    def list_rest_apis(self) -> list:
        """列出所有 REST API"""
        try:
            response = self.apigateway.get_rest_apis()
            return response.get("items", [])
        except ClientError as e:
            print(f"Error listing REST APIs: {e}", file=sys.stderr)
            return []

    def get_first_api_id(self) -> str:
        """獲取第一個 API ID"""
        apis = self.list_rest_apis()
        if apis:
            return apis[0].get("id", "")
        return ""

    def get_api_by_name(self, name: str) -> str:
        """根據名稱獲取 API ID"""
        apis = self.list_rest_apis()
        for api in apis:
            if name.lower() in api.get("name", "").lower():
                return api.get("id", "")
        return ""

    def print_apis_json(self):
        """以 JSON 格式打印所有 API"""
        apis = self.list_rest_apis()
        print(json.dumps({"items": apis}, indent=2, ensure_ascii=False))

    def print_first_api_id(self):
        """打印第一個 API ID"""
        api_id = self.get_first_api_id()
        if api_id:
            print(api_id)
        else:
            print("", file=sys.stderr)

    def print_api_id_by_name(self, name: str):
        """根據名稱打印 API ID"""
        api_id = self.get_api_by_name(name)
        if api_id:
            print(api_id)
        else:
            print("", file=sys.stderr)


@click.command()
@click.option(
    "--action",
    "-a",
    type=click.Choice(["list", "first-id", "find-by-name"]),
    default="list",
    help="執行的動作",
)
@click.option("--name", "-n", help="API 名稱（用於 find-by-name 動作）")
@click.option("--endpoint", default="http://localhost:4566", help="API Gateway 端點 URL")
@click.option("--region", default="ap-southeast-1", help="AWS 區域")
@click.option(
    "--output", "-o", type=click.Choice(["json", "text"]), default="text", help="輸出格式"
)
def main(action, name, endpoint, region, output):
    """API Gateway 輔助工具"""

    helper = APIGatewayHelper(endpoint, region)

    try:
        if action == "list":
            if output == "json":
                helper.print_apis_json()
            else:
                apis = helper.list_rest_apis()
                if apis:
                    for api in apis:
                        print(f"ID: {api.get('id', '')}, Name: {api.get('name', '')}")
                else:
                    print("No APIs found", file=sys.stderr)

        elif action == "first-id":
            helper.print_first_api_id()

        elif action == "find-by-name":
            if not name:
                print("Error: --name is required for find-by-name action", file=sys.stderr)
                sys.exit(1)
            helper.print_api_id_by_name(name)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
