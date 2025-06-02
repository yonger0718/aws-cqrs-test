#!/usr/bin/env python3
"""
驗證改進版 Lambda 函數的腳本

此腳本驗證所有三個 Lambda 函數是否正確實現了 AWS 最佳實踐
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Dict, List, Optional


def load_lambda_module(lambda_name: str) -> Optional[ModuleType]:
    """動態載入 Lambda 模組"""
    lambda_path = Path(f"lambdas/{lambda_name}/app.py")
    if not lambda_path.exists():
        print(f"❌ Lambda 函數 {lambda_name} 不存在於 {lambda_path}")
        return None

    spec = importlib.util.spec_from_file_location(lambda_name, lambda_path)
    if spec is None:
        print(f"❌ 無法載入 Lambda 模組 {lambda_name}")
        return None

    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        print(f"❌ 無法載入 Lambda 模組 {lambda_name}")
        return None

    try:
        spec.loader.exec_module(module)
        print(f"✅ {lambda_name} 模組載入成功")
        return module
    except Exception as e:
        print(f"❌ {lambda_name} 模組載入失敗: {e}")
        return None


def validate_powertools_integration(module: ModuleType, lambda_name: str) -> bool:
    """驗證 AWS Lambda PowerTools 整合"""
    checks: List[str] = []

    # 檢查 Logger
    if hasattr(module, "logger"):
        checks.append("✅ Logger 已整合")
    else:
        checks.append("❌ Logger 未整合")

    # 檢查 Tracer
    if hasattr(module, "tracer"):
        checks.append("✅ Tracer 已整合")
    else:
        checks.append("❌ Tracer 未整合")

    # 檢查環境檢測
    if hasattr(module, "IS_LAMBDA_ENV"):
        checks.append("✅ 環境檢測已實現")
    else:
        checks.append("❌ 環境檢測未實現")

    print(f"\n📋 {lambda_name} PowerTools 整合檢查:")
    for check in checks:
        print(f"  {check}")

    return all("✅" in check for check in checks)


def validate_error_handling(module: ModuleType, lambda_name: str) -> bool:
    """驗證錯誤處理"""
    source_code = ""
    lambda_path = Path(f"lambdas/{lambda_name}/app.py")

    try:
        with open(lambda_path, "r", encoding="utf-8") as f:
            source_code = f.read()
    except Exception as e:
        print(f"❌ 無法讀取 {lambda_name} 源碼: {e}")
        return False

    checks: List[str] = []

    # 檢查是否有 try-except 區塊
    if "try:" in source_code and "except" in source_code:
        checks.append("✅ 包含 try-except 錯誤處理")
    else:
        checks.append("❌ 缺少 try-except 錯誤處理")

    # 檢查是否有 ClientError 處理 (DynamoDB)
    if "ClientError" in source_code or lambda_name == "query_lambda":
        checks.append("✅ AWS ClientError 處理已實現")
    else:
        checks.append("❌ AWS ClientError 處理未實現")

    # 檢查是否有結構化日誌
    if "extra=" in source_code or "logger.info" in source_code:
        checks.append("✅ 結構化日誌已實現")
    else:
        checks.append("❌ 結構化日誌未實現")

    print(f"\n🛡️ {lambda_name} 錯誤處理檢查:")
    for check in checks:
        print(f"  {check}")

    return all("✅" in check for check in checks)


def validate_lambda_handler(module: ModuleType, lambda_name: str) -> bool:
    """驗證 Lambda 處理器"""
    checks: List[str] = []

    # 檢查是否有 lambda_handler 函數
    if hasattr(module, "lambda_handler"):
        checks.append("✅ lambda_handler 函數存在")

        # 檢查是否有 PowerTools 裝飾器
        handler = getattr(module, "lambda_handler")
        if hasattr(handler, "__wrapped__"):
            checks.append("✅ PowerTools 裝飾器已應用")
        else:
            checks.append("⚠️ PowerTools 裝飾器可能未應用")
    else:
        checks.append("❌ lambda_handler 函數不存在")

    print(f"\n🔧 {lambda_name} Lambda 處理器檢查:")
    for check in checks:
        print(f"  {check}")

    return all("✅" in check for check in checks)


def validate_service_classes(module: ModuleType, lambda_name: str) -> bool:
    """驗證服務類別設計"""
    checks: List[str] = []

    # 根據不同 Lambda 檢查對應的服務類別
    if lambda_name == "query_lambda":
        if hasattr(module, "EKSHandlerService"):
            checks.append("✅ EKSHandlerService 類別存在")
        else:
            checks.append("❌ EKSHandlerService 類別不存在")

    elif lambda_name == "query_result_lambda":
        if hasattr(module, "QueryService"):
            checks.append("✅ QueryService 類別存在")
        else:
            checks.append("❌ QueryService 類別不存在")

    elif lambda_name == "stream_processor_lambda":
        required_classes = [
            "CommandToQueryTransformer",
            "StreamEventParser",
            "QuerySideRepository",
            "StreamProcessorService",
        ]
        for cls_name in required_classes:
            if hasattr(module, cls_name):
                checks.append(f"✅ {cls_name} 類別存在")
            else:
                checks.append(f"❌ {cls_name} 類別不存在")

    print(f"\n🏗️ {lambda_name} 服務類別檢查:")
    for check in checks:
        print(f"  {check}")

    return all("✅" in check for check in checks)


def main() -> int:
    """主驗證函數"""
    print("🚀 開始驗證改進版 Lambda 函數...\n")

    lambda_functions = ["query_lambda", "query_result_lambda", "stream_processor_lambda"]

    overall_results: Dict[str, bool] = {}

    for lambda_name in lambda_functions:
        print(f"\n{'='*60}")
        print(f"🔍 驗證 {lambda_name}")
        print(f"{'='*60}")

        # 載入模組
        module = load_lambda_module(lambda_name)
        if not module:
            overall_results[lambda_name] = False
            continue

        # 執行各項檢查
        powertools_ok = validate_powertools_integration(module, lambda_name)
        error_handling_ok = validate_error_handling(module, lambda_name)
        lambda_handler_ok = validate_lambda_handler(module, lambda_name)
        service_classes_ok = validate_service_classes(module, lambda_name)

        # 總體結果
        all_checks_passed = all(
            [powertools_ok, error_handling_ok, lambda_handler_ok, service_classes_ok]
        )

        overall_results[lambda_name] = all_checks_passed

        print(f"\n📊 {lambda_name} 總體結果: {'✅ 通過' if all_checks_passed else '❌ 需要改進'}")

    # 最終報告
    print(f"\n{'='*60}")
    print("📈 最終驗證報告")
    print(f"{'='*60}")

    all_passed = all(overall_results.values())
    if all_passed:
        print("\n🎉 所有 Lambda 函數都通過了驗證！")
        return 0
    else:
        print("\n⚠️ 部分 Lambda 函數需要改進：")
        for lambda_name, passed in overall_results.items():
            if not passed:
                print(f"  ❌ {lambda_name}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
