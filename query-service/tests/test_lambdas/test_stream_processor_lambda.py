"""
Stream Processor Lambda 統一測試入口

本模組作為主測試套件的一部分，整合 Lambda 函數測試
"""

import atexit
import importlib.util
import os
import sys
from pathlib import Path

# 設置測試環境變數
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")

# 找到正確的 lambda 目錄
lambda_dir = Path(__file__).parent.parent.parent / "lambdas" / "stream_processor_lambda"
app_path = lambda_dir / "app.py"
test_app_path = lambda_dir / "test_app.py"

# 記住原始的 app 模組（如果存在）
original_app_module = sys.modules.get("app")

# 暫時清除任何現有的 app 模組
modules_to_remove = [name for name in sys.modules if name == "app" or name.endswith(".app")]
for module_name in modules_to_remove:
    del sys.modules[module_name]

# 使用絕對路徑動態載入 app 模組
app_spec = importlib.util.spec_from_file_location("stream_processor_app", app_path)
if app_spec is None or app_spec.loader is None:
    raise ImportError(f"Cannot load app module from {app_path}")
app_module = importlib.util.module_from_spec(app_spec)
sys.modules["app"] = app_module  # 註冊為 'app' 讓 test_app.py 能找到
app_spec.loader.exec_module(app_module)

# 暫時添加 lambda 目錄到 sys.path 的最前面
original_path = sys.path.copy()
if str(lambda_dir) in sys.path:
    sys.path.remove(str(lambda_dir))
sys.path.insert(0, str(lambda_dir))

try:
    # 動態載入測試模組
    test_spec = importlib.util.spec_from_file_location("stream_processor_test_app", test_app_path)
    if test_spec is None or test_spec.loader is None:
        raise ImportError(f"Cannot load test module from {test_app_path}")
    test_module = importlib.util.module_from_spec(test_spec)
    test_spec.loader.exec_module(test_module)

    # 從動態載入的模組中取得測試類別
    TestStreamProcessorLambda = test_module.TestStreamProcessorLambda
    TestStreamProcessorLambdaErrorHandling = test_module.TestStreamProcessorLambdaErrorHandling
    TestStreamProcessorLambdaValidation = test_module.TestStreamProcessorLambdaValidation

    __all__ = [
        "TestStreamProcessorLambda",
        "TestStreamProcessorLambdaErrorHandling",
        "TestStreamProcessorLambdaValidation",
    ]

except ImportError as e:
    # 如果導入失敗，提供錯誤信息
    raise ImportError(f"Cannot import test classes from {lambda_dir}: {e}")

# 恢復原始的 sys.path
sys.path = original_path


# 清理函數（在模組卸載時會被調用）
def _cleanup() -> None:
    """在模組卸載時恢復原始的 app 模組"""
    if original_app_module is not None:
        sys.modules["app"] = original_app_module
    elif "app" in sys.modules:
        del sys.modules["app"]


atexit.register(_cleanup)
