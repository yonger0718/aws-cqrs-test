"""
Query Lambda 統一測試入口

本模組作為主測試套件的一部分，整合 Lambda 函數測試
"""

import os
import sys
from pathlib import Path

# 添加 lambda 目錄到 Python 路徑
lambda_dir = Path(__file__).parent.parent.parent / "lambdas" / "query_lambda"
sys.path.insert(0, str(lambda_dir))

# 設置測試環境變數
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")

# 導入並重新導出所有測試
try:
    from test_app import (  # noqa: E402
        TestEnvironmentConfiguration,
        TestLambdaHandlerErrorHandling,
        TestLambdaHandlerFailuresQuery,
        TestLambdaHandlerMarketingQuery,
        TestLambdaHandlerResponseFormat,
        TestLambdaHandlerUserQuery,
        TestRequestTimeout,
    )

    # 明確導出所有測試類
    __all__ = [
        "TestLambdaHandlerUserQuery",
        "TestLambdaHandlerMarketingQuery",
        "TestLambdaHandlerFailuresQuery",
        "TestLambdaHandlerErrorHandling",
        "TestLambdaHandlerResponseFormat",
        "TestEnvironmentConfiguration",
        "TestRequestTimeout",
    ]

except ImportError as e:
    # 如果導入失敗，提供更清晰的錯誤信息
    raise ImportError(f"Cannot import test_app from {lambda_dir}: {e}")
