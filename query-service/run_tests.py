#!/usr/bin/env python3
"""
運行 ECS 架構下的查詢服務測試腳本
適用於 CQRS 模式的 ECS Fargate 部署
"""

import subprocess
import sys
import time
from typing import Any, Dict, List, Optional


def run_command(cmd: List[str], cwd: Optional[str] = None) -> Dict[str, Any]:
    """執行命令並返回結果"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=120)
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "stdout": "", "stderr": "Command timeout", "returncode": -1}
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e), "returncode": -1}


def check_docker_services() -> bool:
    """檢查 Docker 服務是否正常運行"""
    print("🔍 檢查 Docker 服務狀態...")

    # 檢查 docker-compose 服務
    result = run_command(["docker-compose", "ps"], cwd="query-service")
    if not result["success"]:
        print("❌ Docker Compose 檢查失敗:", result["stderr"])
        return False

    print("✅ Docker 服務檢查完成")
    return True


def run_unit_tests() -> bool:
    """運行單元測試"""
    print("🧪 運行單元測試...")

    test_commands = [
        ["python", "-m", "pytest", "tests/test_eks_handler.py", "-v"],
        ["python", "-m", "pytest", "tests/test_integration.py", "-v"],
    ]

    all_passed = True
    for cmd in test_commands:
        print("執行:", " ".join(cmd))
        result = run_command(cmd, cwd="query-service")

        if result["success"]:
            print("✅ 測試通過")
        else:
            print("❌ 測試失敗:")
            print("  stdout:", result["stdout"])
            print("  stderr:", result["stderr"])
            all_passed = False

    return all_passed


def test_ecs_handler_endpoints() -> bool:
    """測試 ECS Handler 端點"""
    print("🌐 測試 ECS Handler API 端點...")

    # 等待服務啟動
    print("等待 ECS Handler 服務啟動...")
    time.sleep(5)

    # 測試健康檢查端點
    result = run_command(["curl", "-f", "http://localhost:8000/health"])
    if not result["success"]:
        print("❌ ECS Handler 健康檢查失敗")
        return False

    print("✅ ECS Handler 健康檢查通過")

    # 測試用戶查詢端點
    test_endpoints = [
        ("用戶查詢", "http://localhost:8000/query/user?user_id=test_user_001"),
        ("失敗查詢", "http://localhost:8000/query/fail?transaction_id=tx_002"),
    ]

    for name, url in test_endpoints:
        print(f"測試 {name}...")
        result = run_command(["curl", "-f", "-s", url])
        if result["success"]:
            print(f"✅ {name} 測試通過")
        else:
            print(f"❌ {name} 測試失敗: {result['stderr']}")
            return False

    return True


def run_pre_commit_checks() -> bool:
    """運行 pre-commit 檢查"""
    print("🔧 運行 pre-commit 檢查...")

    result = run_command(["pre-commit", "run", "--all-files"], cwd="query-service")
    if result["success"]:
        print("✅ Pre-commit 檢查通過")
        return True
    else:
        print("❌ Pre-commit 檢查失敗:")
        print("  stdout:", result["stdout"])
        print("  stderr:", result["stderr"])
        return False


def main() -> int:
    """主函數"""
    print("🚀 開始運行 ECS 架構測試套件...\n")

    test_results = {
        "docker_services": False,
        "unit_tests": False,
        "api_endpoints": False,
        "pre_commit": False,
    }

    # 1. 檢查 Docker 服務
    test_results["docker_services"] = check_docker_services()

    # 2. 運行單元測試
    if test_results["docker_services"]:
        test_results["unit_tests"] = run_unit_tests()

    # 3. 測試 API 端點
    if test_results["unit_tests"]:
        test_results["api_endpoints"] = test_ecs_handler_endpoints()

    # 4. 運行 pre-commit 檢查
    test_results["pre_commit"] = run_pre_commit_checks()

    # 輸出測試結果
    print("\n📊 測試結果總結:")
    print("=" * 50)

    for test_name, passed in test_results.items():
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"{test_name:15}: {status}")

    all_passed = all(test_results.values())

    if all_passed:
        print("\n🎉 所有測試都通過了！ECS 架構運行正常。")
        return 0
    else:
        print("\n💥 部分測試失敗，請檢查上面的錯誤訊息。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
