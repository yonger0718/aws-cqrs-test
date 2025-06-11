# AWS CloudShell 整合測試指南

## 🎯 概述

本指南說明如何在 AWS CloudShell 中進行完整的服務鏈整合測試，驗證以下架構：

```
客戶端 -> HTTP API Gateway (v2) -> Query Lambda -> EKS Handler (ECS) -> Internal HTTP API Gateway -> Query Result Lambda -> DynamoDB
```

## 📌 架構特點說明

本測試指南適用於以下架構特點：

- **API Gateway**: 使用 **HTTP API Gateway (v2)** 而非 REST API Gateway (v1)
- **ECS 部署**: 可能使用直接 IP 訪問，而非通過 Application Load Balancer
- **內部通信**: 使用 HTTP API Gateway 進行內部服務間通信
- **查找方式**: 優先使用 `aws apigatewayv2` 命令，回退到 `aws apigateway` 命令

### HTTP API Gateway vs REST API Gateway

| 特性 | HTTP API Gateway (v2) | REST API Gateway (v1) |
|------|----------------------|----------------------|
| AWS CLI 命令 | `aws apigatewayv2` | `aws apigateway` |
| URL 格式 | `$default` stage 無前綴<br/>具名 stage 有前綴 | 總是包含 stage 前綴 |
| Stage 設定 | 支援 `$default` stage | 使用具名 stage |
| URL 範例 | `https://api.../endpoint`<br/>`https://api.../prod/endpoint` | `https://api.../prod/endpoint` |
| 性能 | 更快，延遲更低 | 功能更豐富 |
| 成本 | 更便宜 | 較貴但功能完整 |

## 🔧 前置準備

### 1. 設置 AWS CloudShell 環境

```bash
# 更新系統工具
sudo yum update -y
sudo yum install -y jq curl

# 確認 AWS CLI 配置
aws sts get-caller-identity
aws configure list

# 設置環境變數
export AWS_REGION=ap-southeast-1
export AWS_DEFAULT_REGION=ap-southeast-1
```

### 2. 獲取部署資源 ARN/URL

```bash
# 查找您的 HTTP API Gateway (v2)
HTTP_API_GATEWAY_ID=$(aws apigatewayv2 get-apis \
  --query 'Items[?contains(Name, `query`)].ApiId | [0]' \
  --output text)

echo "HTTP API Gateway ID: $HTTP_API_GATEWAY_ID"

# 檢查 HTTP API Gateway 的 stage 設定
if [ "$HTTP_API_GATEWAY_ID" != "None" ] && [ -n "$HTTP_API_GATEWAY_ID" ]; then
    echo "檢查 HTTP API Gateway stages..."
    aws apigatewayv2 get-stages --api-id "$HTTP_API_GATEWAY_ID" \
      --query 'Items[*].{Stage:StageName,AutoDeploy:AutoDeploy}' \
      --output table
fi

# 如果沒找到 HTTP API Gateway，嘗試 REST API Gateway (v1)
if [ "$HTTP_API_GATEWAY_ID" = "None" ] || [ -z "$HTTP_API_GATEWAY_ID" ]; then
    REST_API_GATEWAY_ID=$(aws apigateway get-rest-apis \
      --query 'items[?contains(name, `query`)].id | [0]' \
      --output text)
    echo "REST API Gateway ID: $REST_API_GATEWAY_ID"
fi

# 查找 ECS 集群和服務
CLUSTER_NAME=$(aws ecs list-clusters \
  --query 'clusterArns[0]' \
  --output text | sed 's/.*\///')

echo "ECS Cluster: $CLUSTER_NAME"

# 查找 ECS 服務
if [ "$CLUSTER_NAME" != "None" ] && [ -n "$CLUSTER_NAME" ]; then
    SERVICE_NAME=$(aws ecs list-services --cluster "$CLUSTER_NAME" \
      --query 'serviceArns[3]' \
      --output text | sed 's/.*\///')
    echo "ECS Service: $SERVICE_NAME"
fi

# 檢查是否有 ALB (可選)
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --query 'LoadBalancers[?contains(LoadBalancerName, `query`)].DNSName | [0]' \
  --output text 2>/dev/null)

if [ "$ALB_DNS" != "None" ] && [ -n "$ALB_DNS" ]; then
    echo "Application Load Balancer DNS: $ALB_DNS"
else
    echo "No ALB found - ECS service may use direct access"
fi

# 查找 DynamoDB 表
aws dynamodb list-tables \
  --query 'TableNames[?contains(@, `command`) || contains(@, `notification`) || contains(@, `EventQuery`)]'
```

### 3. 設置測試變數

```bash
# 外部 HTTP API Gateway v2 (客戶端入口)
if [ -n "$HTTP_API_GATEWAY_ID" ] && [ "$HTTP_API_GATEWAY_ID" != "None" ]; then
    # 檢查 HTTP API Gateway 的 stage 設定
    DEFAULT_STAGE=$(aws apigatewayv2 get-stages --api-id "$HTTP_API_GATEWAY_ID" \
      --query 'Items[?StageName==`$default`].StageName' \
      --output text)

    if [ "$DEFAULT_STAGE" = '$default' ]; then
        # 使用 $default stage，URL 中不包含 stage 前綴
        export EXTERNAL_API_GATEWAY="https://${HTTP_API_GATEWAY_ID}.execute-api.ap-southeast-1.amazonaws.com"
        echo "使用 HTTP API Gateway ($default stage): $EXTERNAL_API_GATEWAY"
    else
        # 使用具名 stage，通常是 prod 或其他
        STAGE_NAME=$(aws apigatewayv2 get-stages --api-id "$HTTP_API_GATEWAY_ID" \
          --query 'Items[0].StageName' \
          --output text)
        export EXTERNAL_API_GATEWAY="https://${HTTP_API_GATEWAY_ID}.execute-api.ap-southeast-1.amazonaws.com/${STAGE_NAME}"
        echo "使用 HTTP API Gateway (${STAGE_NAME} stage): $EXTERNAL_API_GATEWAY"
    fi
elif [ -n "$REST_API_GATEWAY_ID" ] && [ "$REST_API_GATEWAY_ID" != "None" ]; then
    export EXTERNAL_API_GATEWAY="https://${REST_API_GATEWAY_ID}.execute-api.ap-southeast-1.amazonaws.com/prod"
    echo "使用 REST API Gateway: $EXTERNAL_API_GATEWAY"
else
    echo "⚠️  請手動設置 API Gateway URL"
    export EXTERNAL_API_GATEWAY="https://your-api-gateway-id.execute-api.ap-southeast-1.amazonaws.com"
fi

# ECS Handler 設置
if [ -n "$ALB_DNS" ] && [ "$ALB_DNS" != "None" ]; then
    # 通過 ALB 訪問
    export ECS_HANDLER_URL="http://${ALB_DNS}:8000"
    echo "ECS Handler (通過 ALB): $ECS_HANDLER_URL"
else
    # 直接 IP 訪問（需要手動設置）
    export ECS_HANDLER_URL="http://your-ecs-public-ip:8000"
    echo "⚠️  請手動設置 ECS Handler 直接訪問 URL"
    echo "   可以通過以下命令查找 ECS 任務的公網 IP："
    echo "   aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks task-arn"
fi

# Internal HTTP API Gateway (ECS 到 Lambda)
export INTERNAL_API_GATEWAY="https://your-internal-http-api-id.execute-api.ap-southeast-1.amazonaws.com"

# DynamoDB 表名稱
export COMMAND_TABLE="command-records"
export QUERY_TABLE="notification-records"  # 或 EventQuery
```

## 🧪 完整鏈路測試

### 步驟 1: 健康檢查所有服務

```bash
echo "🔍 執行服務健康檢查..."

# 1.1 檢查外部 API Gateway
echo "1. 檢查外部 API Gateway..."
if [[ "$EXTERNAL_API_GATEWAY" != *"your-api-gateway-id"* ]]; then
    response=$(curl -s "${EXTERNAL_API_GATEWAY}/health" 2>/dev/null || echo "error")
    if [ "$response" != "error" ]; then
        echo "✅ API Gateway 可訪問"
        echo "$response" | jq '.' 2>/dev/null || echo "$response"
    else
        echo "❌ API Gateway 無法訪問，請檢查 URL 和網路連接"
    fi
else
    echo "⚠️  請先設置正確的 API Gateway URL"
fi

# 1.2 檢查 ECS Handler
echo "2. 檢查 ECS Handler..."
if [[ "$ECS_HANDLER_URL" != *"your-ecs-public-ip"* ]]; then
    response=$(curl -s "${ECS_HANDLER_URL}/health" 2>/dev/null || echo "error")
    if [ "$response" != "error" ]; then
        echo "✅ ECS Handler 可訪問"
        echo "$response" | jq '.' 2>/dev/null || echo "$response"
    else
        echo "❌ ECS Handler 無法訪問，請檢查 URL 和網路連接"
    fi
else
    echo "⚠️  請先設置正確的 ECS Handler URL"
fi

# 1.3 檢查 Lambda 函數狀態
echo "3. 檢查 Lambda 函數..."
aws lambda get-function \
  --function-name query-service-query-lambda \
  --query 'Configuration.[FunctionName,State,LastUpdateStatus]' \
  --output table

aws lambda get-function \
  --function-name query-service-query-result-lambda \
  --query 'Configuration.[FunctionName,State,LastUpdateStatus]' \
  --output table

# 1.4 檢查 DynamoDB 表
echo "4. 檢查 DynamoDB 表..."
aws dynamodb describe-table \
  --table-name $COMMAND_TABLE \
  --query 'Table.[TableName,TableStatus,ItemCount]' \
  --output table

aws dynamodb describe-table \
  --table-name $QUERY_TABLE \
  --query 'Table.[TableName,TableStatus,ItemCount]' \
  --output table
```

### 步驟 2: 準備測試數據

```bash
# 創建測試腳本
cat > prepare_test_data.sh << 'EOF'
#!/bin/bash

TIMESTAMP=$(date +%s)
TEST_USER_ID="test_user_$(shuf -i 1000-9999 -n 1)"
TEST_MARKETING_ID="marketing_campaign_$(shuf -i 100-999 -n 1)"
TEST_TRANSACTION_ID="txn_$(date +%s)_$(shuf -i 1000-9999 -n 1)"

echo "準備測試數據..."
echo "User ID: $TEST_USER_ID"
echo "Marketing ID: $TEST_MARKETING_ID"
echo "Transaction ID: $TEST_TRANSACTION_ID"

# 插入測試數據到 command-records (觸發 Stream)
aws dynamodb put-item \
  --table-name $COMMAND_TABLE \
  --item '{
    "id": {"S": "'$TEST_TRANSACTION_ID'"},
    "user_id": {"S": "'$TEST_USER_ID'"},
    "marketing_id": {"S": "'$TEST_MARKETING_ID'"},
    "transaction_id": {"S": "'$TEST_TRANSACTION_ID'"},
    "notification_title": {"S": "Test Notification from CloudShell"},
    "status": {"S": "SENT"},
    "platform": {"S": "IOS"},
    "created_at": {"N": "'$TIMESTAMP'"},
    "ap_id": {"S": "cloudshell_test_001"}
  }'

echo "✅ 測試數據已插入到 $COMMAND_TABLE"

# 等待 Stream 處理
echo "⏳ 等待 DynamoDB Stream 處理... (10秒)"
sleep 10

# 儲存測試變數到文件
cat > test_vars.env << EOV
export TEST_USER_ID="$TEST_USER_ID"
export TEST_MARKETING_ID="$TEST_MARKETING_ID"
export TEST_TRANSACTION_ID="$TEST_TRANSACTION_ID"
EOV

echo "✅ 測試變數已保存到 test_vars.env"
EOF

chmod +x prepare_test_data.sh
./prepare_test_data.sh
source test_vars.env
```

### 步驟 3: 完整鏈路測試

```bash
echo "🔄 開始完整鏈路測試..."

# 創建完整測試腳本
cat > full_chain_test.sh << 'EOF'
#!/bin/bash

source test_vars.env

echo "🎯 測試目標："
echo "  User ID: $TEST_USER_ID"
echo "  Marketing ID: $TEST_MARKETING_ID"
echo "  Transaction ID: $TEST_TRANSACTION_ID"
echo ""

# 測試函數：通用 API 調用
test_api_call() {
    local test_name="$1"
    local endpoint="$2"
    local payload="$3"
    local expected_user_id="$4"

    echo "📍 測試: $test_name"
    echo "   端點: $endpoint"
    echo "   負載: $payload"

    response=$(curl -s -X POST "$endpoint" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -d "$payload" \
        --max-time 30)

    if [ $? -eq 0 ]; then
        echo "✅ HTTP 請求成功"

        # 檢查回應格式
        if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
            success=$(echo "$response" | jq -r '.success')
            total_count=$(echo "$response" | jq -r '.total_count // 0')
            message=$(echo "$response" | jq -r '.message // "No message"')

            echo "   成功狀態: $success"
            echo "   結果數量: $total_count"
            echo "   訊息: $message"

            if [ "$success" = "true" ] && [ "$total_count" -gt 0 ]; then
                echo "🎉 測試通過！"

                # 顯示第一筆資料
                if [ "$total_count" -gt 0 ]; then
                    first_item=$(echo "$response" | jq -r '.data[0]' 2>/dev/null)
                    if [ "$first_item" != "null" ]; then
                        echo "   第一筆資料:"
                        echo "$first_item" | jq -r '
                            "     用戶ID: " + (.user_id // "N/A") +
                            " | 標題: " + (.notification_title // "N/A") +
                            " | 狀態: " + (.status // "N/A")'
                    fi
                fi
            else
                echo "⚠️  測試完成但無數據或執行失敗"
            fi
        else
            echo "❌ 回應格式不正確"
            echo "   Raw response: $response"
        fi
    else
        echo "❌ HTTP 請求失敗"
        echo "   回應: $response"
    fi

    echo ""
}

# 3.1 測試用戶查詢 (外部 API Gateway -> Lambda -> ECS -> Internal API -> Lambda -> DynamoDB)
echo "📍 測試: 用戶查詢 (完整鏈路)"
echo "   端點: ${EXTERNAL_API_GATEWAY}/user?user_id=${TEST_USER_ID}"

response=$(curl -s "${EXTERNAL_API_GATEWAY}/user?user_id=${TEST_USER_ID}" \
    --max-time 30)

if [ $? -eq 0 ]; then
    echo "✅ HTTP 請求成功"
    if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
        success=$(echo "$response" | jq -r '.success')
        count=$(echo "$response" | jq -r '.count // 0')
        echo "   成功狀態: $success"
        echo "   結果數量: $count"
        [ "$success" = "true" ] && echo "🎉 用戶查詢測試通過！"
    else
        echo "❌ 回應格式不正確: $response"
    fi
else
    echo "❌ HTTP 請求失敗"
fi

# 3.2 測試行銷活動查詢
echo ""
echo "📍 測試: 行銷活動查詢 (完整鏈路)"
echo "   端點: ${EXTERNAL_API_GATEWAY}/marketing?marketing_id=${TEST_MARKETING_ID}"

response=$(curl -s "${EXTERNAL_API_GATEWAY}/marketing?marketing_id=${TEST_MARKETING_ID}" \
    --max-time 30)

if [ $? -eq 0 ]; then
    echo "✅ HTTP 請求成功"
    if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
        success=$(echo "$response" | jq -r '.success')
        count=$(echo "$response" | jq -r '.count // 0')
        echo "   成功狀態: $success"
        echo "   結果數量: $count"
        [ "$success" = "true" ] && echo "🎉 行銷查詢測試通過！"
    else
        echo "❌ 回應格式不正確: $response"
    fi
else
    echo "❌ HTTP 請求失敗"
fi

# 3.3 測試失敗記錄查詢
echo ""
echo "📍 測試: 失敗記錄查詢 (完整鏈路)"
echo "   端點: ${EXTERNAL_API_GATEWAY}/fail?transaction_id=${TEST_TRANSACTION_ID}"

response=$(curl -s "${EXTERNAL_API_GATEWAY}/fail?transaction_id=${TEST_TRANSACTION_ID}" \
    --max-time 30)

if [ $? -eq 0 ]; then
    echo "✅ HTTP 請求成功"
    if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
        success=$(echo "$response" | jq -r '.success')
        count=$(echo "$response" | jq -r '.count // 0')
        echo "   成功狀態: $success"
        echo "   結果數量: $count"
        [ "$success" = "true" ] && echo "🎉 失敗查詢測試通過！"
    else
        echo "❌ 回應格式不正確: $response"
    fi
else
    echo "❌ HTTP 請求失敗"
fi

# 3.4 測試直接 ECS Handler 調用（繞過外部 API Gateway）
echo ""
echo "🔄 測試直接 ECS Handler 調用..."
echo "📍 測試: 直接 ECS Handler 用戶查詢"
echo "   端點: ${ECS_HANDLER_URL}/query/user"

response=$(curl -s -X POST "${ECS_HANDLER_URL}/query/user" \
    -H "Content-Type: application/json" \
    -d '{"user_id":"'$TEST_USER_ID'"}' \
    --max-time 30)

if [ $? -eq 0 ]; then
    echo "✅ HTTP 請求成功"
    if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
        success=$(echo "$response" | jq -r '.success')
        total_count=$(echo "$response" | jq -r '.total_count // 0')
        echo "   成功狀態: $success"
        echo "   結果數量: $total_count"
        [ "$success" = "true" ] && echo "🎉 直接 ECS 測試通過！"
    else
        echo "❌ 回應格式不正確: $response"
    fi
else
    echo "❌ HTTP 請求失敗"
fi

EOF

chmod +x full_chain_test.sh
./full_chain_test.sh
```

### 步驟 4: 驗證資料一致性

```bash
echo "🔍 驗證資料一致性..."

cat > verify_data_consistency.sh << 'EOF'
#!/bin/bash

source test_vars.env

echo "📊 資料一致性驗證"
echo "=================="

# 檢查 Command Side (寫入端)
echo "1. 檢查 Command Side 資料..."
command_count=$(aws dynamodb scan \
  --table-name $COMMAND_TABLE \
  --filter-expression "user_id = :uid" \
  --expression-attribute-values '{":uid":{"S":"'$TEST_USER_ID'"}}' \
  --select COUNT \
  --query 'Count' \
  --output text)

echo "   Command 表中找到 $command_count 筆記錄"

# 檢查 Query Side (讀取端)
echo "2. 檢查 Query Side 資料..."
query_count=$(aws dynamodb scan \
  --table-name $QUERY_TABLE \
  --filter-expression "user_id = :uid" \
  --expression-attribute-values '{":uid":{"S":"'$TEST_USER_ID'"}}' \
  --select COUNT \
  --query 'Count' \
  --output text)

echo "   Query 表中找到 $query_count 筆記錄"

# 資料一致性檢查
if [ "$command_count" -eq "$query_count" ] && [ "$command_count" -gt 0 ]; then
    echo "✅ 資料一致性驗證通過 ($command_count = $query_count)"
else
    echo "⚠️  資料一致性問題："
    echo "   Command Side: $command_count 筆"
    echo "   Query Side: $query_count 筆"

    if [ "$query_count" -lt "$command_count" ]; then
        echo "   可能原因: DynamoDB Stream 處理延遲或失敗"
        echo "   建議: 檢查 Stream Processor Lambda 日誌"
    fi
fi

# 顯示實際資料
echo ""
echo "3. Command Side 資料詳情:"
aws dynamodb scan \
  --table-name $COMMAND_TABLE \
  --filter-expression "user_id = :uid" \
  --expression-attribute-values '{":uid":{"S":"'$TEST_USER_ID'"}}' \
  --query 'Items[*].[id.S, user_id.S, notification_title.S, status.S]' \
  --output table

echo ""
echo "4. Query Side 資料詳情:"
aws dynamodb scan \
  --table-name $QUERY_TABLE \
  --filter-expression "user_id = :uid" \
  --expression-attribute-values '{":uid":{"S":"'$TEST_USER_ID'"}}' \
  --query 'Items[*].[transaction_id.S, user_id.S, notification_title.S, status.S]' \
  --output table

EOF

chmod +x verify_data_consistency.sh
./verify_data_consistency.sh
```

### 步驟 5: 效能與錯誤測試

```bash
echo "⚡ 效能與錯誤測試..."

cat > performance_error_test.sh << 'EOF'
#!/bin/bash

echo "🚀 效能測試"
echo "========="

# 並發查詢測試
echo "1. 並發查詢測試 (5次同時查詢)..."
for i in {1..5}; do
    (
        start_time=$(date +%s.%N)
        response=$(curl -s -X POST "${EXTERNAL_API_GATEWAY}/query/user" \
            -H "Content-Type: application/json" \
            -d '{"user_id":"'$TEST_USER_ID'"}' \
            --max-time 10)
        end_time=$(date +%s.%N)
        duration=$(echo "$end_time - $start_time" | bc -l)

        success=$(echo "$response" | jq -r '.success // false')
        echo "   查詢 $i: 成功=$success, 耗時=${duration}s"
    ) &
done
wait

echo ""
echo "🚨 錯誤處理測試"
echo "============="

# 測試不存在的用戶
echo "2. 測試不存在的用戶..."
response=$(curl -s -X POST "${EXTERNAL_API_GATEWAY}/query/user" \
    -H "Content-Type: application/json" \
    -d '{"user_id":"nonexistent_user_999999"}')

success=$(echo "$response" | jq -r '.success')
count=$(echo "$response" | jq -r '.total_count // 0')
echo "   結果: 成功=$success, 數量=$count (預期: true, 0)"

# 測試無效參數
echo "3. 測試無效參數..."
response=$(curl -s -X POST "${EXTERNAL_API_GATEWAY}/query/user" \
    -H "Content-Type: application/json" \
    -d '{"invalid_field":"test"}')

if echo "$response" | grep -q "error\|Error\|ERROR" || [ "$(echo "$response" | jq -r '.success')" = "false" ]; then
    echo "   ✅ 正確處理無效參數"
else
    echo "   ⚠️  無效參數處理可能有問題"
    echo "   回應: $response"
fi

# 測試空請求
echo "4. 測試空請求..."
response=$(curl -s -X POST "${EXTERNAL_API_GATEWAY}/query/user" \
    -H "Content-Type: application/json" \
    -d '{}')

if echo "$response" | grep -q "error\|Error\|ERROR" || [ "$(echo "$response" | jq -r '.success')" = "false" ]; then
    echo "   ✅ 正確處理空請求"
else
    echo "   ⚠️  空請求處理可能有問題"
    echo "   回應: $response"
fi

EOF

chmod +x performance_error_test.sh
./performance_error_test.sh
```

## 📋 監控與除錯

### 查看日誌

```bash
# 查看 Lambda 函數日誌
echo "📄 查看 Lambda 日誌..."

# Query Lambda 日誌
echo "1. Query Lambda 日誌:"
aws logs describe-log-groups \
  --log-group-name-prefix "/aws/lambda/query-service-query" \
  --query 'logGroups[*].logGroupName'

# 獲取最新日誌
latest_log_stream=$(aws logs describe-log-streams \
  --log-group-name "/aws/lambda/query-service-query-lambda" \
  --order-by LastEventTime \
  --descending \
  --max-items 1 \
  --query 'logStreams[0].logStreamName' \
  --output text)

if [ "$latest_log_stream" != "None" ]; then
    aws logs get-log-events \
      --log-group-name "/aws/lambda/query-service-query-lambda" \
      --log-stream-name "$latest_log_stream" \
      --limit 10 \
      --query 'events[*].[timestamp,message]' \
      --output table
fi

# ECS 服務日誌
echo "2. ECS 服務日誌:"
aws logs describe-log-streams \
  --log-group-name "/ecs/query-service" \
  --order-by LastEventTime \
  --descending \
  --max-items 1 \
  --query 'logStreams[0].logStreamName'
```

### API Gateway 分析

```bash
# API Gateway 執行記錄
echo "📊 API Gateway 分析..."

# HTTP API Gateway (v2) 分析
if [ -n "$HTTP_API_GATEWAY_ID" ] && [ "$HTTP_API_GATEWAY_ID" != "None" ]; then
    echo "分析 HTTP API Gateway..."

    # 獲取 API 資訊
    aws apigatewayv2 get-api --api-id $HTTP_API_GATEWAY_ID

    # 查看路由
    aws apigatewayv2 get-routes --api-id $HTTP_API_GATEWAY_ID \
      --query 'Items[*].[RouteKey,Target]' \
      --output table

    # 查看部署階段
    aws apigatewayv2 get-stages --api-id $HTTP_API_GATEWAY_ID \
      --query 'Items[*].[StageName,CreatedDate]' \
      --output table

# REST API Gateway (v1) 分析
elif [ -n "$REST_API_GATEWAY_ID" ] && [ "$REST_API_GATEWAY_ID" != "None" ]; then
    echo "分析 REST API Gateway..."

    # 獲取部署資訊
    aws apigateway get-deployments \
      --rest-api-id $REST_API_GATEWAY_ID \
      --query 'items[*].[id,description,createdDate]' \
      --output table

    # 查看資源配置
    aws apigateway get-resources \
      --rest-api-id $REST_API_GATEWAY_ID \
      --query 'items[*].[path,resourceMethods]' \
      --output table
else
    echo "⚠️  未找到 API Gateway，請先設置 API Gateway ID"
fi
```

## 🎯 測試成功標準

### ✅ 完整鏈路測試通過標準

1. **健康檢查**: 所有服務回應 200 狀態碼
2. **資料流動**: Command Side → Query Side 資料同步成功
3. **API 回應**: 所有查詢 API 返回正確格式的 JSON
4. **錯誤處理**: 無效請求得到適當的錯誤回應
5. **效能**: 單次查詢在 5 秒內完成

### 🔧 故障排除檢查清單

- [ ] 確認所有 AWS 資源已正確部署
- [ ] 檢查 IAM 角色權限配置
- [ ] 驗證網路和安全群組設定
- [ ] 確認環境變數配置正確
- [ ] 檢查 DynamoDB Stream 是否啟用
- [ ] 查看各服務的 CloudWatch 日誌

### 🚨 常見問題與解決方案

#### HTTP API Gateway 問題

**問題**: `aws apigateway get-rest-apis` 返回空列表
**解決**: 改用 `aws apigatewayv2 get-apis` 查找 HTTP API Gateway

```bash
# 正確的查找方式
aws apigatewayv2 get-apis --query 'Items[*].{Name:Name,ApiId:ApiId}' --output table
```

#### ECS 直接訪問問題

**問題**: 沒有 ALB，無法訪問 ECS 服務
**解決**: 查找 ECS 任務的公網 IP

```bash
# 1. 找到集群和服務
CLUSTER_NAME=$(aws ecs list-clusters --query 'clusterArns[0]' --output text | sed 's/.*\///')
SERVICE_NAME=$(aws ecs list-services --cluster "$CLUSTER_NAME" --query 'serviceArns[0]' --output text | sed 's/.*\///')

# 2. 獲取運行中的任務
TASK_ARN=$(aws ecs list-tasks --cluster "$CLUSTER_NAME" --service-name "$SERVICE_NAME" --query 'taskArns[0]' --output text)

# 3. 獲取任務的網路介面
NETWORK_INTERFACE_ID=$(aws ecs describe-tasks --cluster "$CLUSTER_NAME" --tasks "$TASK_ARN" \
  --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
  --output text)

# 4. 獲取公網 IP
PUBLIC_IP=$(aws ec2 describe-network-interfaces \
  --network-interface-ids "$NETWORK_INTERFACE_ID" \
  --query 'NetworkInterfaces[0].Association.PublicIp' \
  --output text)

echo "ECS 任務公網 IP: $PUBLIC_IP"
export ECS_HANDLER_URL="http://$PUBLIC_IP:8000"
```

#### API Gateway URL 格式問題

**問題**: HTTP API Gateway URL 格式不正確
**解決**: HTTP API Gateway 的 URL 格式取決於 stage 設定

```bash
# 檢查 stage 設定
aws apigatewayv2 get-stages --api-id YOUR_API_ID --query 'Items[*].{Stage:StageName}' --output table

# $default stage (無 stage 前綴)
https://your-api-id.execute-api.region.amazonaws.com/endpoint

# 具名 stage (包含 stage 前綴)
https://your-api-id.execute-api.region.amazonaws.com/prod/endpoint
https://your-api-id.execute-api.region.amazonaws.com/dev/endpoint

# REST API Gateway (總是包含 stage)
https://your-api-id.execute-api.region.amazonaws.com/stage/endpoint
```

**$default Stage 說明**:
- HTTP API Gateway 使用 `$default` 作為預設 stage 名稱
- 當使用 `$default` 時，URL 中不需要包含 stage 前綴
- 這是 HTTP API Gateway 簡化 URL 結構的特性

## 📝 清理測試資源

```bash
# 清理測試數據
echo "🧹 清理測試數據..."

# 刪除測試數據
aws dynamodb delete-item \
  --table-name $COMMAND_TABLE \
  --key '{"id":{"S":"'$TEST_TRANSACTION_ID'"}}'

aws dynamodb delete-item \
  --table-name $QUERY_TABLE \
  --key '{"transaction_id":{"S":"'$TEST_TRANSACTION_ID'"}}'

# 刪除測試文件
rm -f prepare_test_data.sh full_chain_test.sh verify_data_consistency.sh performance_error_test.sh test_vars.env

echo "✅ 測試資源清理完成"
```

---

通過這個指南，您可以在 AWS CloudShell 中完整地測試您的 CQRS 系統，從外部 API Gateway 一直到 DynamoDB 的完整鏈路！
