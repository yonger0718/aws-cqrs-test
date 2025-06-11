#!/bin/bash

# AWS CloudShell 快速開始腳本
# 專門為在 AWS CloudShell 中測試完整服務鏈而設計

set -e

# ANSI 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

echo -e "\n${CYAN}🚀 AWS CloudShell 快速開始設置${NC}"
echo -e "${GRAY}===============================${NC}\n"

# 1. 檢查 CloudShell 環境
echo -e "${YELLOW}步驟 1: 檢查 CloudShell 環境...${NC}"

# 確認當前用戶身份
echo -e "${CYAN}當前 AWS 身份:${NC}"
aws sts get-caller-identity

# 檢查區域設置
current_region=$(aws configure get region)
echo -e "${CYAN}當前區域: ${current_region:-使用環境預設}${NC}"

# 設置預設區域（如果未設置）
if [ -z "$current_region" ]; then
    echo -e "${YELLOW}設置預設區域為 ap-southeast-1...${NC}"
    export AWS_DEFAULT_REGION=ap-southeast-1
    export AWS_REGION=ap-southeast-1
    aws configure set region ap-southeast-1
fi

# 2. 安裝必要工具
echo -e "\n${YELLOW}步驟 2: 安裝必要工具...${NC}"

# 檢查並安裝 jq
if ! command -v jq &> /dev/null; then
    echo -e "${CYAN}安裝 jq...${NC}"
    sudo yum install -y jq
else
    echo -e "${GREEN}✅ jq 已安裝${NC}"
fi

# 檢查並安裝 bc (用於計算)
if ! command -v bc &> /dev/null; then
    echo -e "${CYAN}安裝 bc...${NC}"
    sudo yum install -y bc
else
    echo -e "${GREEN}✅ bc 已安裝${NC}"
fi

echo -e "${GREEN}✅ 工具安裝完成${NC}"

# 3. 自動發現 AWS 資源
echo -e "\n${YELLOW}步驟 3: 自動發現 AWS 資源...${NC}"

# 發現 HTTP API Gateway (v2)
echo -e "${CYAN}搜尋 HTTP API Gateway (v2)...${NC}"
http_apis=$(aws apigatewayv2 get-apis --query 'Items[?contains(Name, `query`) || contains(Name, `notification`)].{Name:Name,ApiId:ApiId}' --output table 2>/dev/null || echo "")

if [ -n "$http_apis" ] && [ "$http_apis" != "No APIs found" ]; then
    echo -e "${GREEN}找到的 HTTP API Gateways:${NC}"
    echo "$http_apis"

    # 嘗試自動選擇
    HTTP_API_GATEWAY_ID=$(aws apigatewayv2 get-apis --query 'Items[?contains(Name, `query`)].ApiId | [0]' --output text 2>/dev/null)
    if [ "$HTTP_API_GATEWAY_ID" != "None" ] && [ -n "$HTTP_API_GATEWAY_ID" ]; then
        echo -e "${GREEN}自動選擇 HTTP API Gateway ID: $HTTP_API_GATEWAY_ID${NC}"
    else
        echo -e "${YELLOW}⚠️  請手動設置 HTTP_API_GATEWAY_ID 變數${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  未找到 HTTP API Gateway，嘗試搜尋 REST API Gateway...${NC}"

    # 回退到 REST API Gateway
    rest_apis=$(aws apigateway get-rest-apis --query 'items[?contains(name, `query`) || contains(name, `notification`)].{Name:name,Id:id}' --output table 2>/dev/null || echo "")

    if [ -n "$rest_apis" ] && [ "$rest_apis" != "No APIs found" ]; then
        echo -e "${GREEN}找到的 REST API Gateways:${NC}"
        echo "$rest_apis"

        # 嘗試自動選擇
        REST_API_GATEWAY_ID=$(aws apigateway get-rest-apis --query 'items[?contains(name, `query`)].id | [0]' --output text 2>/dev/null)
        if [ "$REST_API_GATEWAY_ID" != "None" ] && [ -n "$REST_API_GATEWAY_ID" ]; then
            echo -e "${GREEN}自動選擇 REST API Gateway ID: $REST_API_GATEWAY_ID${NC}"
        fi
    else
        echo -e "${RED}❌ 未找到任何 API Gateway${NC}"
    fi
fi

# ECS 服務發現（不使用 ALB）
echo -e "\n${CYAN}搜尋 ECS 服務...${NC}"

# 查找 ECS 集群
clusters=$(aws ecs list-clusters --query 'clusterArns[?contains(@, `query`) || contains(@, `service`)]' --output table 2>/dev/null || echo "")

if [ -n "$clusters" ] && [ "$clusters" != "No clusters found" ]; then
    echo -e "${GREEN}找到的 ECS 集群:${NC}"
    echo "$clusters"

    # 獲取第一個集群名稱
    CLUSTER_NAME=$(aws ecs list-clusters --query 'clusterArns[0]' --output text 2>/dev/null | sed 's/.*\///')

    if [ "$CLUSTER_NAME" != "None" ] && [ -n "$CLUSTER_NAME" ]; then
        echo -e "${GREEN}找到 ECS 集群: $CLUSTER_NAME${NC}"

        # 查找服務
        services=$(aws ecs list-services --cluster "$CLUSTER_NAME" --query 'serviceArns' --output table 2>/dev/null || echo "")
        if [ -n "$services" ]; then
            echo -e "${GREEN}集群中的服務:${NC}"
            echo "$services"

            # 獲取服務的任務定義，從中可能找到 ALB 信息
            service_name=$(aws ecs list-services --cluster "$CLUSTER_NAME" --query 'serviceArns[0]' --output text 2>/dev/null | sed 's/.*\///')
            if [ "$service_name" != "None" ] && [ -n "$service_name" ]; then
                echo -e "${CYAN}找到服務: $service_name${NC}"

                # 嘗試獲取負載均衡器信息
                lb_info=$(aws ecs describe-services --cluster "$CLUSTER_NAME" --services "$service_name" --query 'services[0].loadBalancers' --output json 2>/dev/null || echo "[]")
                if [ "$lb_info" != "[]" ]; then
                    echo -e "${GREEN}服務使用負載均衡器:${NC}"
                    echo "$lb_info" | jq .
                fi
            fi
        fi
    fi
else
    echo -e "${YELLOW}⚠️  未找到 ECS 集群，可能 ECS 服務使用直接 IP 訪問${NC}"
fi

# 檢查是否有 ALB（可選）
echo -e "\n${CYAN}檢查 Application Load Balancer (可選)...${NC}"
albs=$(aws elbv2 describe-load-balancers --query 'LoadBalancers[?contains(LoadBalancerName, `query`) || contains(LoadBalancerName, `service`)].{Name:LoadBalancerName,DNS:DNSName}' --output table 2>/dev/null || echo "")

if [ -n "$albs" ] && [ "$albs" != "No load balancers found" ]; then
    echo -e "${GREEN}找到的 Load Balancers:${NC}"
    echo "$albs"

    # 嘗試自動選擇
    ALB_DNS=$(aws elbv2 describe-load-balancers --query 'LoadBalancers[?contains(LoadBalancerName, `query`)].DNSName | [0]' --output text 2>/dev/null)
    if [ "$ALB_DNS" != "None" ] && [ -n "$ALB_DNS" ]; then
        echo -e "${GREEN}自動選擇 ALB DNS: $ALB_DNS${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  未找到 ALB，ECS 服務可能直接暴露端口${NC}"
fi

# 發現 DynamoDB 表
echo -e "\n${CYAN}搜尋 DynamoDB 表...${NC}"
tables=$(aws dynamodb list-tables --query 'TableNames[?contains(@, `command`) || contains(@, `notification`) || contains(@, `Event`)]' --output table)

if [ -n "$tables" ]; then
    echo -e "${GREEN}找到的 DynamoDB 表:${NC}"
    echo "$tables"

    # 嘗試自動選擇表名
    COMMAND_TABLE=$(aws dynamodb list-tables --query 'TableNames[?contains(@, `command`)] | [0]' --output text)
    QUERY_TABLE=$(aws dynamodb list-tables --query 'TableNames[?contains(@, `notification`) || contains(@, `Event`)] | [0]' --output text)

    if [ "$COMMAND_TABLE" != "None" ] && [ -n "$COMMAND_TABLE" ]; then
        echo -e "${GREEN}Command 表: $COMMAND_TABLE${NC}"
    fi
    if [ "$QUERY_TABLE" != "None" ] && [ -n "$QUERY_TABLE" ]; then
        echo -e "${GREEN}Query 表: $QUERY_TABLE${NC}"
    fi
else
    echo -e "${RED}❌ 未找到相關的 DynamoDB 表${NC}"
fi

# 發現 Lambda 函數
echo -e "\n${CYAN}搜尋 Lambda 函數...${NC}"
lambdas=$(aws lambda list-functions --query 'Functions[?contains(FunctionName, `query`) || contains(FunctionName, `notification`)].{Name:FunctionName,Runtime:Runtime,State:State}' --output table)

if [ -n "$lambdas" ]; then
    echo -e "${GREEN}找到的 Lambda 函數:${NC}"
    echo "$lambdas"
else
    echo -e "${RED}❌ 未找到相關的 Lambda 函數${NC}"
fi

# 4. 創建環境變數文件
echo -e "\n${YELLOW}步驟 4: 創建環境變數文件...${NC}"

cat > cloudshell_env.sh << EOF
#!/bin/bash

# AWS CloudShell 環境變數配置
# 由 cloudshell_quick_start.sh 自動生成於 $(date)

# AWS 基本設置
export AWS_REGION=ap-southeast-1
export AWS_DEFAULT_REGION=ap-southeast-1

# HTTP API Gateway v2 設置
export HTTP_API_GATEWAY_ID="${HTTP_API_GATEWAY_ID:-YOUR_HTTP_API_GATEWAY_ID}"
export EXTERNAL_API_GATEWAY="https://\${HTTP_API_GATEWAY_ID}.execute-api.ap-southeast-1.amazonaws.com/prod"

# REST API Gateway v1 設置 (備用)
export REST_API_GATEWAY_ID="${REST_API_GATEWAY_ID:-YOUR_REST_API_GATEWAY_ID}"
export EXTERNAL_REST_API_GATEWAY="https://\${REST_API_GATEWAY_ID}.execute-api.ap-southeast-1.amazonaws.com/prod"

# ECS 設置
export ALB_DNS="${ALB_DNS:-YOUR_ALB_DNS}"
export ECS_HANDLER_URL="http://\${ALB_DNS}:8000"
export ECS_HANDLER_DIRECT_URL="http://your-ecs-public-ip:8000"  # 如果沒有 ALB

# Internal API Gateway (HTTP v2 - 請手動設置)
export INTERNAL_API_GATEWAY="https://your-internal-http-api-id.execute-api.ap-southeast-1.amazonaws.com"

# DynamoDB 表設置
export COMMAND_TABLE="${COMMAND_TABLE:-command-records}"
export QUERY_TABLE="${QUERY_TABLE:-notification-records}"

# 顯示當前設置
echo "當前環境變數設置："
echo "  HTTP API Gateway ID: \$HTTP_API_GATEWAY_ID"
echo "  REST API Gateway ID: \$REST_API_GATEWAY_ID"
echo "  ALB DNS: \$ALB_DNS"
echo "  Command Table: \$COMMAND_TABLE"
echo "  Query Table: \$QUERY_TABLE"
echo "  External API: \$EXTERNAL_API_GATEWAY"
echo "  ECS Handler: \$ECS_HANDLER_URL"
echo "  Internal API: \$INTERNAL_API_GATEWAY"
EOF

chmod +x cloudshell_env.sh

echo -e "${GREEN}✅ 環境變數文件已創建: cloudshell_env.sh${NC}"

# 5. 創建測試腳本
echo -e "\n${YELLOW}步驟 5: 創建快速測試腳本...${NC}"

cat > quick_health_check.sh << 'EOF'
#!/bin/bash

source cloudshell_env.sh

echo "🔍 快速健康檢查..."

# 檢查外部 HTTP API Gateway
echo "1. 檢查外部 HTTP API Gateway..."
if [ "${HTTP_API_GATEWAY_ID}" != "YOUR_HTTP_API_GATEWAY_ID" ]; then
    response=$(curl -s --max-time 10 "${EXTERNAL_API_GATEWAY}/health" 2>/dev/null || echo "error")
    if [ "$response" != "error" ]; then
        echo "✅ 外部 HTTP API Gateway 可訪問"
        echo "$response" | jq -r '.service // .status // "Unknown"' 2>/dev/null || echo "$response"
    else
        echo "❌ 外部 HTTP API Gateway 無法訪問"

        # 嘗試 REST API Gateway
        if [ "${REST_API_GATEWAY_ID}" != "YOUR_REST_API_GATEWAY_ID" ]; then
            echo "   嘗試 REST API Gateway..."
            response=$(curl -s --max-time 10 "${EXTERNAL_REST_API_GATEWAY}/health" 2>/dev/null || echo "error")
            if [ "$response" != "error" ]; then
                echo "✅ REST API Gateway 可訪問"
                echo "$response" | jq -r '.service // .status // "Unknown"' 2>/dev/null || echo "$response"
            fi
        fi
    fi
else
    echo "⚠️  請先設置正確的 HTTP_API_GATEWAY_ID"
fi

# 檢查 ECS Handler
echo "2. 檢查 ECS Handler..."
if [ "${ALB_DNS}" != "YOUR_ALB_DNS" ]; then
    response=$(curl -s --max-time 10 "${ECS_HANDLER_URL}/health" 2>/dev/null || echo "error")
    if [ "$response" != "error" ]; then
        echo "✅ ECS Handler (通過 ALB) 可訪問"
        echo "$response" | jq -r '.service // .status // "Unknown"' 2>/dev/null || echo "$response"
    else
        echo "❌ ECS Handler (通過 ALB) 無法訪問"
    fi
else
    echo "⚠️  沒有設置 ALB_DNS，ECS 可能直接暴露端口"
    echo "   請嘗試設置 ECS_HANDLER_DIRECT_URL 並測試"
fi

# 檢查 DynamoDB 表
echo "3. 檢查 DynamoDB 表..."
command_status=$(aws dynamodb describe-table --table-name $COMMAND_TABLE --query 'Table.TableStatus' --output text 2>/dev/null || echo "NOT_FOUND")
query_status=$(aws dynamodb describe-table --table-name $QUERY_TABLE --query 'Table.TableStatus' --output text 2>/dev/null || echo "NOT_FOUND")

echo "   Command Table ($COMMAND_TABLE): $command_status"
echo "   Query Table ($QUERY_TABLE): $query_status"

if [ "$command_status" = "ACTIVE" ] && [ "$query_status" = "ACTIVE" ]; then
    echo "✅ DynamoDB 表狀態正常"
else
    echo "❌ DynamoDB 表狀態異常"
fi
EOF

chmod +x quick_health_check.sh

echo -e "${GREEN}✅ 快速健康檢查腳本已創建: quick_health_check.sh${NC}"

# 6. 創建完整測試腳本
cat > full_integration_test.sh << 'EOF'
#!/bin/bash

source cloudshell_env.sh

echo "🧪 完整整合測試..."

# 生成測試數據
TIMESTAMP=$(date +%s)
TEST_USER_ID="cloudshell_user_$(shuf -i 1000-9999 -n 1)"
TEST_MARKETING_ID="cloudshell_campaign_$(shuf -i 100-999 -n 1)"
TEST_TRANSACTION_ID="cloudshell_txn_$(date +%s)_$(shuf -i 1000-9999 -n 1)"

echo "測試參數："
echo "  User ID: $TEST_USER_ID"
echo "  Marketing ID: $TEST_MARKETING_ID"
echo "  Transaction ID: $TEST_TRANSACTION_ID"

# 插入測試資料
echo "1. 插入測試資料到 Command Table..."
aws dynamodb put-item \
  --table-name $COMMAND_TABLE \
  --item '{
    "id": {"S": "'$TEST_TRANSACTION_ID'"},
    "user_id": {"S": "'$TEST_USER_ID'"},
    "marketing_id": {"S": "'$TEST_MARKETING_ID'"},
    "transaction_id": {"S": "'$TEST_TRANSACTION_ID'"},
    "notification_title": {"S": "CloudShell Integration Test"},
    "status": {"S": "SENT"},
    "platform": {"S": "ANDROID"},
    "created_at": {"N": "'$TIMESTAMP'"},
    "ap_id": {"S": "cloudshell_test"}
  }'

echo "✅ 測試資料已插入"

# 等待 Stream 處理
echo "2. 等待 DynamoDB Stream 處理... (15秒)"
sleep 15

# 測試查詢 API
echo "3. 測試用戶查詢..."

# 嘗試 HTTP API Gateway
if [ "${HTTP_API_GATEWAY_ID}" != "YOUR_HTTP_API_GATEWAY_ID" ]; then
    echo "   使用 HTTP API Gateway 測試..."
    response=$(curl -s -X POST "${EXTERNAL_API_GATEWAY}/query/user" \
        -H "Content-Type: application/json" \
        -d '{"user_id":"'$TEST_USER_ID'"}' \
        --max-time 30)

    if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
        success=$(echo "$response" | jq -r '.success')
        count=$(echo "$response" | jq -r '.total_count // 0')
        echo "✅ HTTP API Gateway 用戶查詢成功: success=$success, count=$count"

        if [ "$count" -gt 0 ]; then
            echo "🎉 完整鏈路測試通過！"
        else
            echo "⚠️  查詢成功但無數據，可能 Stream 同步未完成"
        fi
    else
        echo "❌ HTTP API Gateway 用戶查詢失敗"
        echo "Response: $response"

        # 嘗試 REST API Gateway
        if [ "${REST_API_GATEWAY_ID}" != "YOUR_REST_API_GATEWAY_ID" ]; then
            echo "   嘗試 REST API Gateway..."
            response=$(curl -s -X POST "${EXTERNAL_REST_API_GATEWAY}/query/user" \
                -H "Content-Type: application/json" \
                -d '{"user_id":"'$TEST_USER_ID'"}' \
                --max-time 30)

            if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
                success=$(echo "$response" | jq -r '.success')
                count=$(echo "$response" | jq -r '.total_count // 0')
                echo "✅ REST API Gateway 用戶查詢成功: success=$success, count=$count"
            fi
        fi
    fi
else
    echo "⚠️  跳過 HTTP API Gateway 測試，請先設置 HTTP_API_GATEWAY_ID"

    # 嘗試 REST API Gateway
    if [ "${REST_API_GATEWAY_ID}" != "YOUR_REST_API_GATEWAY_ID" ]; then
        echo "   使用 REST API Gateway 測試..."
        response=$(curl -s -X POST "${EXTERNAL_REST_API_GATEWAY}/query/user" \
            -H "Content-Type: application/json" \
            -d '{"user_id":"'$TEST_USER_ID'"}' \
            --max-time 30)

        if echo "$response" | jq -e '.success' >/dev/null 2>&1; then
            success=$(echo "$response" | jq -r '.success')
            count=$(echo "$response" | jq -r '.total_count // 0')
            echo "✅ REST API Gateway 用戶查詢成功: success=$success, count=$count"
        fi
    else
        echo "⚠️  請設置 HTTP_API_GATEWAY_ID 或 REST_API_GATEWAY_ID"
    fi
fi

# 清理測試資料
echo "4. 清理測試資料..."
aws dynamodb delete-item --table-name $COMMAND_TABLE --key '{"id":{"S":"'$TEST_TRANSACTION_ID'"}}'
# 注意：Query Table 的主鍵可能不同，需要根據實際情況調整

echo "✅ 整合測試完成"
EOF

chmod +x full_integration_test.sh

echo -e "${GREEN}✅ 完整整合測試腳本已創建: full_integration_test.sh${NC}"

# 7. 顯示下一步說明
echo -e "\n${CYAN}🎯 下一步操作指南${NC}"
echo -e "${GRAY}===============================${NC}"

echo -e "\n${YELLOW}1. 載入環境變數:${NC}"
echo -e "${GRAY}source cloudshell_env.sh${NC}"

echo -e "\n${YELLOW}2. 執行快速健康檢查:${NC}"
echo -e "${GRAY}./quick_health_check.sh${NC}"

echo -e "\n${YELLOW}3. 執行完整整合測試:${NC}"
echo -e "${GRAY}./full_integration_test.sh${NC}"

echo -e "\n${YELLOW}4. 手動設置變數 (如果自動發現失敗):${NC}"
echo -e "${GRAY}# 設置 HTTP API Gateway v2 (推薦)${NC}"
echo -e "${GRAY}export HTTP_API_GATEWAY_ID=your-actual-http-api-gateway-id${NC}"
echo -e "${GRAY}# 或設置 REST API Gateway v1${NC}"
echo -e "${GRAY}export REST_API_GATEWAY_ID=your-actual-rest-api-gateway-id${NC}"
echo -e "${GRAY}# ECS 服務設置${NC}"
echo -e "${GRAY}export ALB_DNS=your-actual-alb-dns-name  # 如果使用 ALB${NC}"
echo -e "${GRAY}export ECS_HANDLER_DIRECT_URL=http://your-ecs-ip:8000  # 如果直接訪問${NC}"
echo -e "${GRAY}# 內部 HTTP API Gateway${NC}"
echo -e "${GRAY}export INTERNAL_API_GATEWAY=https://your-internal-http-api-id.execute-api.ap-southeast-1.amazonaws.com${NC}"

echo -e "\n${YELLOW}5. 查看詳細測試指南:${NC}"
echo -e "${GRAY}cat docs/testing/AWS_CLOUDSHELL_INTEGRATION_GUIDE.md${NC}"

echo -e "\n${GREEN}🎉 AWS CloudShell 快速開始設置完成！${NC}"
echo -e "${CYAN}現在您可以開始測試完整的服務鏈了！${NC}"
