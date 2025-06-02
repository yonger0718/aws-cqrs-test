#!/usr/bin/env python3
"""
測試驗證腳本

驗證所有 Lambda 函數和測試都能正常工作
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: str, description: str) -> bool:
    """運行命令並檢查結果"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(
            cmd.split(), capture_output=True, text=True, cwd=Path(__file__).parent
        )
        if result.returncode == 0:
            print(f"✅ {description} - 成功")
            return True
        else:
            print(f"❌ {description} - 失敗")
            print(f"錯誤輸出: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - 異常: {e}")
        return False


def main() -> int:
    """主函數"""
    print("🚀 開始驗證 Lambda 函數和測試...")

    tests_passed = 0
    total_tests = 0

    # 測試項目
    test_cases = [
        ("python -m pytest tests/test_lambdas/test_query_lambda.py -v", "Query Lambda 測試"),
        (
            "python -m pytest tests/test_lambdas/test_query_result_lambda.py -v",
            "Query Result Lambda 測試",
        ),
        (
            "python -m pytest tests/test_lambdas/test_stream_processor_lambda.py -v",
            "Stream Processor Lambda 測試",
        ),
    ]

    for cmd, description in test_cases:
        total_tests += 1
        if run_command(cmd, description):
            tests_passed += 1

    # 總結
    print("\n📊 測試結果總結:")
    print(f"   ✅ 通過: {tests_passed}/{total_tests}")
    print(f"   ❌ 失敗: {total_tests - tests_passed}/{total_tests}")

    if tests_passed == total_tests:
        print("\n🎉 所有測試都通過了！Lambda 函數運行正常。")
        return 0
    else:
        print(f"\n⚠️  有 {total_tests - tests_passed} 個測試失敗，請檢查問題。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
