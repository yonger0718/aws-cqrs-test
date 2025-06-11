#!/usr/bin/env python3
"""
Lambda 測試執行腳本

使用方法:
    python test_lambda.py stream_processor single_insert
    python test_lambda.py query_lambda api_gateway_user_query
    python test_lambda.py all
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def import_lambda_handler(lambda_name: str) -> Optional[Any]:
    """動態導入指定的 Lambda handler"""
    try:
        if lambda_name == "stream_processor":
            sys.path.insert(0, str(Path(__file__).parent / "lambdas" / "stream_processor_lambda"))
            from app import lambda_handler

            return lambda_handler
        elif lambda_name == "query_lambda":
            sys.path.insert(0, str(Path(__file__).parent / "lambdas" / "query_lambda"))
            from app import lambda_handler

            return lambda_handler
        elif lambda_name == "query_result_lambda":
            sys.path.insert(0, str(Path(__file__).parent / "lambdas" / "query_result_lambda"))
            from app import lambda_handler

            return lambda_handler
        else:
            raise ValueError(f"Unknown lambda function: {lambda_name}")
    except ImportError as e:
        print(f"Failed to import lambda handler for {lambda_name}: {e}")
        return None


def load_test_templates() -> Dict[str, Any]:
    """載入測試模板"""
    template_path = Path(__file__).parent / "lambda-test-templates.json"
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        print(f"Test template file not found: {template_path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Failed to parse test template: {e}")
        return {}


def run_lambda_test(
    lambda_name: str, test_case_name: str, verbose: bool = True
) -> Optional[Dict[str, Any]]:
    """執行指定的 Lambda 測試案例"""
    # 載入測試模板
    templates = load_test_templates()

    # 根據 lambda_name 選擇正確的模板鍵
    template_key = f"{lambda_name}_lambda" if not lambda_name.endswith("_lambda") else lambda_name

    if template_key not in templates:
        print(f"No test template found for: {template_key}")
        return None

    # 尋找測試案例
    test_cases = templates[template_key].get("test_cases", [])
    test_case = None

    for case in test_cases:
        if case["name"] == test_case_name:
            test_case = case
            break

    if not test_case:
        print(f"Test case '{test_case_name}' not found for {template_key}")
        print(f"Available test cases: {[case['name'] for case in test_cases]}")
        return None

    # 導入 Lambda handler
    handler = import_lambda_handler(lambda_name)
    if not handler:
        return None

    # 設定環境變數
    env_vars = (
        templates.get("testing_instructions", {})
        .get("environment_variables", {})
        .get(template_key, {})
    )
    for key, value in env_vars.items():
        os.environ[key] = str(value)

    print(f"\n🧪 執行測試: {lambda_name} -> {test_case_name}")
    print(f"📝 描述: {test_case.get('description', 'No description')}")

    if verbose:
        print("📤 輸入事件:")
        print(json.dumps(test_case["event"], indent=2, ensure_ascii=False))

    try:
        # 執行 Lambda 函數
        result = handler(test_case["event"], None)

        if verbose:
            print("📥 回應結果:")
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

        print(f"✅ 測試完成: {lambda_name} -> {test_case_name}")
        return result if isinstance(result, dict) else None

    except Exception as e:
        print(f"❌ 測試失敗: {lambda_name} -> {test_case_name}")
        print(f"錯誤: {e}")
        if verbose:
            import traceback

            print("詳細錯誤:")
            traceback.print_exc()
        return None


def list_available_tests() -> None:
    """列出所有可用的測試案例"""
    templates = load_test_templates()

    print("\n📋 可用的測試案例:")
    print("=" * 50)

    for lambda_name, config in templates.items():
        if lambda_name == "testing_instructions":
            continue

        print(f"\n🔧 {lambda_name}:")
        print(f"   描述: {config.get('description', 'No description')}")

        test_cases = config.get("test_cases", [])
        for i, case in enumerate(test_cases, 1):
            print(f"   {i}. {case['name']}")
            print(f"      {case.get('description', 'No description')}")


def run_all_tests() -> None:
    """執行所有測試案例"""
    templates = load_test_templates()

    total_tests = 0
    passed_tests = 0
    failed_tests = 0

    print("\n🚀 執行所有測試案例")
    print("=" * 50)

    for lambda_name, config in templates.items():
        if lambda_name == "testing_instructions":
            continue

        # 移除 "_lambda" 後綴以匹配函數名稱
        clean_lambda_name = lambda_name.replace("_lambda", "")

        test_cases = config.get("test_cases", [])
        for case in test_cases:
            total_tests += 1
            result = run_lambda_test(clean_lambda_name, case["name"], verbose=False)

            if result is not None:
                passed_tests += 1
                print(f"✅ {lambda_name} -> {case['name']}")
            else:
                failed_tests += 1
                print(f"❌ {lambda_name} -> {case['name']}")

    print("\n📊 測試結果摘要:")
    print(f"   總計: {total_tests}")
    print(f"   通過: {passed_tests}")
    print(f"   失敗: {failed_tests}")
    print(
        f"   成功率: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "   成功率: 0%"
    )


def main() -> None:
    """主函數"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python test_lambda.py <lambda_name> <test_case_name>")
        print("  python test_lambda.py list")
        print("  python test_lambda.py all")
        print("\n範例:")
        print("  python test_lambda.py stream_processor dynamodb_stream_insert_event")
        print("  python test_lambda.py query_lambda api_gateway_user_query")
        return

    command = sys.argv[1]

    if command == "list":
        list_available_tests()
    elif command == "all":
        run_all_tests()
    else:
        if len(sys.argv) < 3:
            print("錯誤: 需要指定測試案例名稱")
            print("使用 'python test_lambda.py list' 查看可用的測試案例")
            return

        lambda_name = sys.argv[1]
        test_case_name = sys.argv[2]
        verbose = "--verbose" in sys.argv or "-v" in sys.argv

        run_lambda_test(lambda_name, test_case_name, verbose=verbose)


if __name__ == "__main__":
    main()
