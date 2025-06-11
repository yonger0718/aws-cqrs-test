#!/bin/bash

# 🚀 超簡單服務測試腳本
# 使用方法: ./simple_test.sh

echo "🚀 簡單服務測試"
echo "================"

# 自動檢測 API Gateway
echo "🔍 檢測 API Gateway..."
API_ID=$(aws apigatewayv2 get-apis --query 'Items[0].ApiId' --output text 2>/dev/null)

if [ "$API_ID" != "None" ] && [ -n "$API_ID" ]; then
    # 檢查 stage
    DEFAULT_STAGE=$(aws apigatewayv2 get-stages --api-id "$API_ID" \
      --query 'Items[?StageName==`$default`].StageName' --output text 2>/dev/null)

    if [ "$DEFAULT_STAGE" = '$default' ]; then
        API_URL="https://$API_ID.execute-api.ap-southeast-1.amazonaws.com"
    else
        API_URL="https://$API_ID.execute-api.ap-southeast-1.amazonaws.com/prod"
    fi
    echo "✅ API Gateway: $API_URL"
else
    echo "❌ 未找到 API Gateway"
    echo "請手動設置: export API_URL='https://your-api-id.execute-api.ap-southeast-1.amazonaws.com'"
    exit 1
fi

# 測試 1: 健康檢查
echo ""
echo "1. 🔍 健康檢查"
health_response=$(curl -s -w ",%{http_code}" "$API_URL/health" 2>/dev/null)
http_code="${health_response##*,}"
response_body="${health_response%,*}"

if [ "$http_code" = "200" ]; then
    echo "   ✅ 服務健康"
    echo "   $response_body" | jq -r '.service // .status // "OK"' 2>/dev/null || echo "   響應正常"
else
    echo "   ❌ 服務不健康 (HTTP: $http_code)"
fi

# 測試 2: 用戶查詢
echo ""
echo "2. 🧪 用戶查詢測試"
query_response=$(curl -s "$API_URL/user?user_id=test_user_123" 2>/dev/null)

if echo "$query_response" | jq -e '.success' >/dev/null 2>&1; then
    success=$(echo "$query_response" | jq -r '.success')
    count=$(echo "$query_response" | jq -r '.count // 0')

    if [ "$success" = "true" ]; then
        echo "   ✅ 查詢成功 (找到 $count 筆記錄)"
    else
        echo "   ⚠️  查詢完成但無數據"
    fi
else
    echo "   ❌ 查詢失敗"
    echo "   響應: $query_response"
fi

# 測試 3: 錯誤處理
echo ""
echo "3. ⚠️  錯誤處理測試"
error_response=$(curl -s "$API_URL/user" 2>/dev/null)

if echo "$error_response" | grep -q "error\|Error\|validation\|required" ||
   [ "$(echo "$error_response" | jq -r '.success // "true"')" = "false" ]; then
    echo "   ✅ 錯誤處理正常"
else
    echo "   ⚠️  錯誤處理可能有問題"
fi

echo ""
echo "🎯 測試完成！"
echo ""
echo "💡 提示："
echo "   - 如需完整測試，請參考 docs/testing/AWS_CLOUDSHELL_INTEGRATION_GUIDE.md"
echo "   - 如需更多 curl 範例，請參考 docs/testing/SIMPLE_CURL_TESTS.md"
