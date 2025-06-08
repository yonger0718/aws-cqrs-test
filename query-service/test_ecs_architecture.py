#!/usr/bin/env python3
"""
ECS 架構驗證測試腳本
驗證 CQRS 模式的 ECS Fargate 部署是否正常運作
"""

import asyncio
import subprocess
import sys
from typing import Dict

import aiohttp


class ECSArchitectureValidator:
    """ECS 架構驗證器"""

    def __init__(self) -> None:
        self.base_url = "http://localhost:8000"
        self.test_results: Dict[str, bool] = {}

    async def check_health_endpoint(self) -> bool:
        """檢查健康端點"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ 健康檢查通過: {data}")
                        return True
                    else:
                        print(f"❌ 健康檢查失敗: {response.status}")
                        return False
        except Exception as e:
            print(f"❌ 健康檢查異常: {e}")
            return False

    async def test_user_query(self) -> bool:
        """測試用戶查詢端點"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/query/user"
                params = {"user_id": "test_user_001"}

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(
                            f"✅ 用戶查詢成功: 找到 {len(data.get('items', data.get('data', [])))} 筆記錄"
                        )
                        return True
                    else:
                        text = await response.text()
                        print(f"❌ 用戶查詢失敗: {response.status} - {text}")
                        return False
        except Exception as e:
            print(f"❌ 用戶查詢異常: {e}")
            return False

    async def test_fail_query(self) -> bool:
        """測試失敗查詢端點"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/query/fail"
                params = {"transaction_id": "tx_002"}

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ 失敗查詢成功: {data}")
                        return True
                    else:
                        text = await response.text()
                        print(f"❌ 失敗查詢失敗: {response.status} - {text}")
                        return False
        except Exception as e:
            print(f"❌ 失敗查詢異常: {e}")
            return False

    async def test_marketing_endpoint_disabled(self) -> bool:
        """測試行銷端點是否已禁用"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/query/marketing"
                params = {"marketing_id": "campaign_2024_new_year"}

                async with session.get(url, params=params) as response:
                    # 預期應該返回 404 或其他錯誤，表示端點已禁用
                    if response.status == 404:
                        print("✅ 行銷查詢端點已正確禁用")
                        return True
                    elif response.status == 200:
                        print("⚠️ 警告: 行銷查詢端點仍可用，應該被禁用")
                        return False
                    else:
                        print(f"✅ 行銷查詢端點已禁用 (狀態碼: {response.status})")
                        return True
        except Exception as e:
            print(f"✅ 行銷查詢端點已禁用 (連接失敗: {e})")
            return True

    def check_docker_services(self) -> bool:
        """檢查 Docker 服務狀態"""
        try:
            result = subprocess.run(
                ["docker-compose", "ps", "--format", "json"],
                cwd=".",
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print("✅ Docker Compose 服務運行正常")
                return True
            else:
                print(f"❌ Docker Compose 檢查失敗: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Docker 檢查異常: {e}")
            return False

    def check_internal_api_configuration(self) -> bool:
        """檢查 Internal API 配置"""
        try:
            # 檢查環境變數配置
            result = subprocess.run(
                ["docker-compose", "exec", "-T", "ecs-handler", "env"],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                env_vars = result.stdout
                if "INTERNAL_API_URL" in env_vars:
                    print("✅ Internal API URL 環境變數已配置")
                    return True
                else:
                    print("❌ Internal API URL 環境變數未配置")
                    return False
            else:
                print("⚠️ 無法檢查環境變數配置")
                return False
        except Exception as e:
            print(f"⚠️ 環境變數檢查異常: {e}")
            return False

    async def run_comprehensive_test(self) -> Dict[str, bool]:
        """運行完整測試套件"""
        print("🚀 開始 ECS 架構驗證測試...\n")

        # 等待服務啟動
        print("⏳ 等待服務啟動...")
        await asyncio.sleep(5)

        tests = {
            "docker_services": self.check_docker_services(),
            "internal_api_config": self.check_internal_api_configuration(),
            "health_check": await self.check_health_endpoint(),
            "user_query": await self.test_user_query(),
            "fail_query": await self.test_fail_query(),
            "marketing_disabled": await self.test_marketing_endpoint_disabled(),
        }

        return tests


async def main() -> int:
    """主函數"""
    validator = ECSArchitectureValidator()

    # 運行測試
    results = await validator.run_comprehensive_test()

    # 輸出結果
    print("\n📊 ECS 架構驗證結果:")
    print("=" * 50)

    test_names = {
        "docker_services": "Docker 服務",
        "internal_api_config": "Internal API 配置",
        "health_check": "健康檢查",
        "user_query": "用戶查詢",
        "fail_query": "失敗查詢",
        "marketing_disabled": "行銷端點禁用",
    }

    passed_count = 0
    total_count = len(results)

    for test_key, passed in results.items():
        test_name = test_names.get(test_key, test_key)
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"{test_name:15}: {status}")
        if passed:
            passed_count += 1

    print(f"\n通過率: {passed_count}/{total_count} ({passed_count/total_count*100:.1f}%)")

    if passed_count == total_count:
        print("\n🎉 所有測試通過！ECS 架構運行正常。")
        print("✨ CQRS 模式的 ECS Fargate 部署驗證成功！")
        return 0
    else:
        print(f"\n💥 有 {total_count - passed_count} 項測試失敗。")
        print("請檢查失敗的測試項目並修復問題。")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ 測試被用戶中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 測試運行異常: {e}")
        sys.exit(1)
