#!/usr/bin/env python3
import re

# 讀取文件
with open("query-service/tests/test_eks_handler.py", "r", encoding="utf-8") as f:
    content = f.read()

# 修復沒有類型註釋的測試方法
# 1. 修復沒有參數的測試方法
content = re.sub(r"def (test_\w+)\(self\):", r"def \1(self) -> None:", content)

# 2. 修復有 mock 參數但沒有類型註釋的測試方法
content = re.sub(
    r"def (test_\w+)\(self, mock_lambda_adapter_class\):",
    r"def \1(self, mock_lambda_adapter_class: Any) -> None:",
    content,
)

# 寫回文件
with open("query-service/tests/test_eks_handler.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed test method type annotations")
