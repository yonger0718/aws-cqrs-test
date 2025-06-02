#!/usr/bin/env bash

# 單元測試執行腳本
# 用於 CI/CD 流程中的單元測試執行

set -e

echo "🧪 運行單元測試..."

# 確保在專案根目錄
cd "$(dirname "$0")/.."

# 運行單元測試並生成覆蓋率報告
poetry run pytest -m unit \
  --cov=query-service/eks_handler \
  --cov-report=xml \
  --cov-report=term-missing \
  --cov-report=html \
  -v

echo "✅ 單元測試完成，覆蓋率報告已生成"
echo "📊 HTML 覆蓋率報告: htmlcov/index.html"
echo "📊 XML 覆蓋率報告: coverage.xml"
