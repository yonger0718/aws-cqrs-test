# 簡單 Curl 測試指南

## 🚀 快速開始

只需要 3 個步驟即可驗證您的服務是否正常運作！

### 步驟 1: 設置基本變數

```bash
# 根據您的部署設置這些變數
export API_GATEWAY_URL="https://your-api-id.execute-api.ap-southeast-1.amazonaws.com"
export ECS_SERVICE_URL="http://your-ecs-ip:8000"

# 測試用戶 ID
export TEST_USER_ID="test_user_123"
```

### 步驟 2: 健康檢查

```bash
echo "🔍 健康檢查..."

# API Gateway 健康檢查
echo "1. API Gateway:"
curl -s "$API_GATEWAY_URL/health" | jq '.' || echo "❌ API Gateway 無法訪問"

# ECS 服務健康檢查
echo "2. ECS 服務:"
curl -s "$ECS_SERVICE_URL/health" | jq '.' || echo "❌ ECS 服務無法訪問"
```

### 步驟 3: 功能測試

```bash
echo "🧪 功能測試..."

# 用戶查詢測試
echo "3. 用戶查詢:"
curl -s "$API_GATEWAY_URL/user?user_id=$TEST_USER_ID" | jq '.'
```

---

## 🔧 進階設置

### 自動檢測資源

如果您不知道具體的 URL，可以使用以下命令自動檢測：

```bash
# 自動檢測並設置變數
detect_resources() {
    echo "🔍 自動檢測 AWS 資源..."

    # HTTP API Gateway
    API_ID=$(aws apigatewayv2 get-apis --query 'Items[0].ApiId' --output text 2>/dev/null)
    if [ "$API_ID" != "None" ] && [ -n "$API_ID" ]; then
        # 檢查是否使用 $default stage
        DEFAULT_STAGE=$(aws apigatewayv2 get-stages --api-id "$API_ID" \
          --query 'Items[?StageName==`$default`].StageName' --output text 2>/dev/null)

        if [ "$DEFAULT_STAGE" = '$default' ]; then
            export API_GATEWAY_URL="https://$API_ID.execute-api.ap-southeast-1.amazonaws.com"
        else
            export API_GATEWAY_URL="https://$API_ID.execute-api.ap-southeast-1.amazonaws.com/prod"
        fi
        echo "✅ 找到 API Gateway: $API_GATEWAY_URL"
    else
        echo "⚠️  未找到 API Gateway，請手動設置"
    fi

    # ECS 服務 IP
    CLUSTER=$(aws ecs list-clusters --query 'clusterArns[0]' --output text 2>/dev/null | sed 's/.*\///')
    if [ "$CLUSTER" != "None" ] && [ -n "$CLUSTER" ]; then
        SERVICE=$(aws ecs list-services --cluster "$CLUSTER" --query 'serviceArns[0]' --output text 2>/dev/null | sed 's/.*\///')
        if [ "$SERVICE" != "None" ] && [ -n "$SERVICE" ]; then
            TASK=$(aws ecs list-tasks --cluster "$CLUSTER" --service-name "$SERVICE" --query 'taskArns[0]' --output text 2>/dev/null)
            if [ "$TASK" != "None" ] && [ -n "$TASK" ]; then
                # 嘗試獲取公網 IP
                ENI=$(aws ecs describe-tasks --cluster "$CLUSTER" --tasks "$TASK" \
                  --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
                  --output text 2>/dev/null)

                if [ "$ENI" != "None" ] && [ -n "$ENI" ]; then
                    PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids "$ENI" \
                      --query 'NetworkInterfaces[0].Association.PublicIp' --output text 2>/dev/null)

                    if [ "$PUBLIC_IP" != "None" ] && [ -n "$PUBLIC_IP" ]; then
                        export ECS_SERVICE_URL="http://$PUBLIC_IP:8000"
                        echo "✅ 找到 ECS 服務: $ECS_SERVICE_URL"
                    fi
                fi
            fi
        fi
    fi

    if [ -z "$ECS_SERVICE_URL" ] || [[ "$ECS_SERVICE_URL" == *"your-ecs-ip"* ]]; then
        echo "⚠️  未找到 ECS 服務 IP，請手動設置"
    fi
}

# 執行自動檢測
detect_resources
```

---

## ⚡ 一鍵測試腳本

```bash
#!/bin/bash
# 將以下內容保存為 quick_test.sh

quick_test() {
    echo "🚀 快速服務測試"
    echo "================"

    # 檢查必要變數
    if [[ "$API_GATEWAY_URL" == *"your-api-id"* ]] || [ -z "$API_GATEWAY_URL" ]; then
        echo "❌ 請先設置 API_GATEWAY_URL"
        return 1
    fi

    # 健康檢查
    echo "1. 🔍 健康檢查"

    api_health=$(curl -s -w "%{http_code}" -o /tmp/api_health "$API_GATEWAY_URL/health" 2>/dev/null)
    if [ "$api_health" = "200" ]; then
        echo "   ✅ API Gateway 健康"
        cat /tmp/api_health | jq -r '.service // .status // "OK"' 2>/dev/null || echo "   響應正常"
    else
        echo "   ❌ API Gateway 不健康 (HTTP: $api_health)"
    fi

    if [ -n "$ECS_SERVICE_URL" ] && [[ "$ECS_SERVICE_URL" != *"your-ecs-ip"* ]]; then
        ecs_health=$(curl -s -w "%{http_code}" -o /tmp/ecs_health "$ECS_SERVICE_URL/health" 2>/dev/null)
        if [ "$ecs_health" = "200" ]; then
            echo "   ✅ ECS 服務健康"
            cat /tmp/ecs_health | jq -r '.service // .status // "OK"' 2>/dev/null || echo "   響應正常"
        else
            echo "   ❌ ECS 服務不健康 (HTTP: $ecs_health)"
        fi
    fi

    # 功能測試
    echo ""
    echo "2. 🧪 功能測試"

    # 測試用戶查詢
    echo "   測試用戶查詢..."
    response=$(curl -s -X POST "$API_GATEWAY_URL/query/user" \
        -H "Content-Type: application/json" \
        -d '{"user_id":"'${TEST_USER_ID:-test_user_123}'"}' 2>/dev/null)

    if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
        success=$(echo "$response" | jq -r '.success')
        count=$(echo "$response" | jq -r '.total_count // 0')

        if [ "$success" = "true" ]; then
            echo "   ✅ 用戶查詢成功 (找到 $count 筆記錄)"
        else
            echo "   ⚠️  用戶查詢完成但無數據"
        fi
    else
        echo "   ❌ 用戶查詢失敗"
        echo "   響應: $response"
    fi

    # 清理臨時文件
    rm -f /tmp/api_health /tmp/ecs_health

    echo ""
    echo "🎯 測試完成！"
}

# 執行測試
quick_test
```

---

## 📋 常用測試命令

### 基本健康檢查

```bash
# API Gateway
curl -s "$API_GATEWAY_URL/health" | jq '.status'

# ECS 服務
curl -s "$ECS_SERVICE_URL/health" | jq '.status'
```

### 查詢測試

```bash
# 用戶查詢
curl -s "$API_GATEWAY_URL/user?user_id=test_user_123" | jq '.success, .count'

# 行銷查詢
curl -s "$API_GATEWAY_URL/marketing?marketing_id=campaign_456" | jq '.success, .count'

# 失敗查詢
curl -s "$API_GATEWAY_URL/fail?transaction_id=txn_789" | jq '.success, .count'
```

### 錯誤測試

```bash
# 測試缺少參數
curl -s "$API_GATEWAY_URL/user" | jq '.'

# 測試無效參數
curl -s "$API_GATEWAY_URL/user?invalid_field=test" | jq '.'

# 測試空參數
curl -s "$API_GATEWAY_URL/user?user_id=" | jq '.'
```

---

## 🎯 成功指標

- ✅ **健康檢查**: 返回 HTTP 200 和包含 `status` 字段的 JSON
- ✅ **查詢功能**: 返回包含 `success: true` 的 JSON 響應
- ✅ **錯誤處理**: 無效請求返回適當的錯誤訊息

---

## 🔧 快速故障排除

```bash
# 檢查網路連接
ping your-api-domain.amazonaws.com

# 檢查 DNS 解析
nslookup your-api-id.execute-api.ap-southeast-1.amazonaws.com

# 詳細 curl 除錯
curl -v "$API_GATEWAY_URL/health"

# 檢查 HTTP 狀態碼
curl -w "HTTP Status: %{http_code}\n" -s -o /dev/null "$API_GATEWAY_URL/health"
```

這個簡化版本讓您可以在幾分鐘內驗證服務是否正常運作！🚀
