#!/bin/bash

# Query Lambda 測試執行腳本
echo "=========================================="
echo "執行 Query Lambda 測試"
echo "=========================================="

# 設置測試環境
export PYTHONPATH=$PWD:$PYTHONPATH
export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test

# 安裝測試依賴
echo "安裝測試依賴..."
pip install -r requirements-test.txt

# 執行測試
echo "執行單元測試..."
pytest test_app.py -v --cov=app --cov-report=term-missing --cov-report=html

# 檢查測試結果
if [ $? -eq 0 ]; then
    echo "✅ 所有測試通過！"
    echo "📊 覆蓋率報告已生成至 htmlcov/ 目錄"
else
    echo "❌ 測試失敗！"
    exit 1
fi
