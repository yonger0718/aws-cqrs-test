#!/usr/bin/env bash

# 完整測試執行腳本
# 按順序執行單元測試和整合測試

set -e

echo "🚀 開始執行完整測試套件..."

# 確保在專案根目錄
cd "$(dirname "$0")/.."

echo ""
echo "=========================================="
echo "第一階段：單元測試 + 覆蓋率收集"
echo "=========================================="
./scripts/run-unit-tests.sh

echo ""
echo "=========================================="
echo "第二階段：整合測試"
echo "=========================================="
# 檢查是否有 LocalStack
if curl -f http://localhost:4566/_localstack/health &>/dev/null; then
    ./scripts/run-integration-tests.sh
else
    echo "⚠️  跳過整合測試：LocalStack 未運行"
    echo "如需運行整合測試，請先啟動 LocalStack:"
    echo "  cd query-service && docker-compose up -d localstack"
fi

echo ""
echo "=========================================="
echo "測試執行摘要"
echo "=========================================="
echo "✅ 單元測試：通過（覆蓋率已收集）"
if curl -f http://localhost:4566/_localstack/health &>/dev/null; then
    echo "✅ 整合測試：通過"
else
    echo "⚠️  整合測試：跳過（LocalStack 未運行）"
fi
echo ""
echo "📊 覆蓋率報告："
echo "  - HTML: htmlcov/index.html"
echo "  - XML: coverage.xml"
echo ""
echo "🎉 所有可用測試已完成！"
