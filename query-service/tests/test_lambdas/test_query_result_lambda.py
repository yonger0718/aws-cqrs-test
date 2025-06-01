"""
Query Result Lambda 統一測試入口

本模組作為主測試套件的一部分，整合 Lambda 函數測試
"""

# 設置測試環境變數
import os
import sys
from pathlib import Path

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")

# 添加 lambda 目錄到路徑
lambda_dir = Path(__file__).parent.parent.parent / "lambdas" / "query_result_lambda"
sys.path.insert(0, str(lambda_dir))

# 直接導入測試模組，使用更具體的模組名稱
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("query_result_test_app", lambda_dir / "test_app.py")
if spec is None:
    raise ImportError(f"Cannot load module from {lambda_dir / 'test_app.py'}")
query_result_test_module = importlib.util.module_from_spec(spec)
if spec.loader is None:
    raise ImportError(f"Cannot get loader for module from {lambda_dir / 'test_app.py'}")
spec.loader.exec_module(query_result_test_module)

# 從動態載入的模組中提取測試類
TestUserQueryIntegration = query_result_test_module.TestUserQueryIntegration
TestErrorHandling = query_result_test_module.TestErrorHandling
TestResponseFormat = query_result_test_module.TestResponseFormat

# 為向後兼容提供別名
TestQueryResultLambda = TestUserQueryIntegration
TestQueryResultLambdaErrorHandling = TestErrorHandling
TestQueryResultLambdaValidation = TestResponseFormat

__all__ = [
    "TestQueryResultLambda",
    "TestQueryResultLambdaErrorHandling",
    "TestQueryResultLambdaValidation",
    "TestErrorHandling",
    "TestResponseFormat",
    "TestUserQueryIntegration",
]
