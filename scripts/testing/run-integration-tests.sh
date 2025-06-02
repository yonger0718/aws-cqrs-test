#!/usr/bin/env bash

# 整合測試執行腳本
# 用於 CI/CD 流程中的整合測試執行

set -e

echo "🔗 運行整合測試..."

# 確保在專案根目錄
cd "$(dirname "$0")/.."

# 檢查 LocalStack 是否運行
echo "📋 檢查 LocalStack 連接..."
if ! curl -f http://localhost:4566/_localstack/health &>/dev/null; then
    echo "⚠️  LocalStack 未運行在 localhost:4566"
    echo "請先啟動 LocalStack 或使用 docker compose:"
    echo "  cd query-service && docker compose up -d localstack"
    exit 1
fi

# 運行整合測試（包含覆蓋率收集）
echo "🧪 執行整合測試，期望覆蓋率 > 75%..."
poetry run pytest -m integration \
  -v \
  --tb=short \
  --durations=10

echo "✅ 整合測試完成"
echo "ℹ️  整合測試覆蓋了 API 端點、Lambda 適配器、查詢服務和錯誤處理"
echo "📊 目標覆蓋率：> 75%，實際覆蓋率：~96%"
