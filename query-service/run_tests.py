#!/usr/bin/env python3
"""
運行改進版 Lambda 函數測試的腳本
"""

import importlib.util
import os
import sys
from pathlib import Path


def run_test_file(test_file_path: str) -> bool:
    """運行單個測試文件"""
    try:
        # 添加測試目錄到 Python 路徑
        test_dir = Path(test_file_path).parent
        sys.path.insert(0, str(test_dir))

        # 動態導入測試模組
        spec = importlib.util.spec_from_file_location("test_module", test_file_path)
        if spec is None:
            print(f"❌ 無法載入測試模組 {test_file_path}")
            return False

        test_module = importlib.util.module_from_spec(spec)
        if spec.loader is None:
            print(f"❌ 無法載入測試模組 {test_file_path}")
            return False

        spec.loader.exec_module(test_module)

        # 查找並運行測試類
        import unittest

        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(test_module)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        return result.wasSuccessful()

    except Exception as e:
        print(f"運行測試文件 {test_file_path} 時發生錯誤: {e}")
        return False


def main() -> int:
    """主函數"""
    test_files = [
        "tests/test_lambdas/test_query_result_lambda_improved.py",
        "tests/test_lambdas/test_query_lambda_improved.py",
        "tests/test_lambdas/test_stream_processor_lambda_improved.py",
    ]

    print("🚀 開始運行改進版 Lambda 函數測試...\n")

    all_passed = True

    for test_file in test_files:
        print(f"📋 運行 {test_file}...")

        if os.path.exists(test_file):
            success = run_test_file(test_file)
            if success:
                print(f"✅ {test_file} 測試通過\n")
            else:
                print(f"❌ {test_file} 測試失敗\n")
                all_passed = False
        else:
            print(f"⚠️ 測試文件 {test_file} 不存在\n")
            all_passed = False

    if all_passed:
        print("🎉 所有測試都通過了！")
        return 0
    else:
        print("💥 部分測試失敗，請檢查上面的錯誤訊息")
        return 1


if __name__ == "__main__":
    sys.exit(main())
