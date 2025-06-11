#!/bin/bash

# 載入環境變量設置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$PROJECT_ROOT/scripts/development/setup_env.sh"

# ANSI 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# 端點設定 (使用環境變量)
AWS_ENDPOINT="$LOCALSTACK_ENDPOINT"
AWS_REGION="$AWS_DEFAULT_REGION"

echo -e "\n${CYAN}LocalStack API Gateway 修復工具${NC}"
echo -e "${GRAY}=============================${NC}\n"

# 檢查 LocalStack 是否運行
echo -e "${YELLOW}1. 檢查 LocalStack 狀態...${NC}"
HEALTH_RESPONSE=$(curl -s "$AWS_ENDPOINT/_localstack/health")
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ LocalStack 未運行或無法連接${NC}"
    echo -e "${YELLOW}請確保 LocalStack 容器正在運行${NC}"
    exit 1
fi

echo -e "${GREEN}✅ LocalStack 正常運行${NC}"

# 設置 AWS 命令的共同參數
AWS_COMMON_ARGS="--endpoint-url=$AWS_ENDPOINT --region $AWS_REGION"

# 刪除並重新創建 API Gateway
echo -e "\n${YELLOW}2. 獲取現有 API Gateway...${NC}"
API_LIST=$(aws $AWS_COMMON_ARGS apigateway get-rest-apis)
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 無法獲取 API Gateway 列表${NC}"
    exit 1
fi

echo "$API_LIST" | jq .

# 找到並刪除現有的 API Gateway
echo -e "\n${YELLOW}3. 刪除現有 API Gateway...${NC}"
API_IDS=$(echo "$API_LIST" | jq -r '.items[].id')

for API_ID in $API_IDS; do
    echo -e "${CYAN}刪除 API ID: $API_ID${NC}"
    aws $AWS_COMMON_ARGS apigateway delete-rest-api --rest-api-id $API_ID
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 成功刪除 API ID: $API_ID${NC}"
    else
        echo -e "${RED}❌ 無法刪除 API ID: $API_ID${NC}"
    fi
done

# 重新創建 API Gateway
echo -e "\n${YELLOW}4. 重新創建 API Gateway...${NC}"

# 創建 REST API
API_ID=$(aws $AWS_COMMON_ARGS apigateway create-rest-api \
    --name "Query Service API" \
    --description "API for querying notification records with CQRS pattern" \
    --query 'id' --output text)

echo -e "${GREEN}✅ 新建 API Gateway ID: $API_ID${NC}"

# 獲取根資源 ID
ROOT_ID=$(aws $AWS_COMMON_ARGS apigateway get-resources \
    --rest-api-id $API_ID \
    --query 'items[0].id' --output text)

# 創建 /query 資源
QUERY_ID=$(aws $AWS_COMMON_ARGS apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_ID \
    --path-part "query" \
    --query 'id' --output text)

# 創建 /query/user 資源
USER_ID=$(aws $AWS_COMMON_ARGS apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $QUERY_ID \
    --path-part "user" \
    --query 'id' --output text)

# 創建 /query/marketing 資源
MARKETING_ID=$(aws $AWS_COMMON_ARGS apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $QUERY_ID \
    --path-part "marketing" \
    --query 'id' --output text)

# 創建 /query/fail 資源
FAIL_ID=$(aws $AWS_COMMON_ARGS apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $QUERY_ID \
    --path-part "fail" \
    --query 'id' --output text)

# 為每個資源創建 GET 方法並整合 Lambda
for RESOURCE_ID in $USER_ID $MARKETING_ID $FAIL_ID; do
    # 創建 GET 方法
    aws $AWS_COMMON_ARGS apigateway put-method \
        --rest-api-id $API_ID \
        --resource-id $RESOURCE_ID \
        --http-method GET \
        --authorization-type NONE \
        --request-parameters "method.request.querystring.user_id=false,method.request.querystring.marketing_id=false,method.request.querystring.transaction_id=false"

    # 創建 Lambda 整合
    aws $AWS_COMMON_ARGS apigateway put-integration \
        --rest-api-id $API_ID \
        --resource-id $RESOURCE_ID \
        --http-method GET \
        --type AWS_PROXY \
        --integration-http-method POST \
        --uri "arn:aws:apigateway:ap-southeast-1:lambda:path/2015-03-31/functions/arn:aws:lambda:ap-southeast-1:000000000000:function:query_result_lambda/invocations"

    # 設置方法響應
    aws $AWS_COMMON_ARGS apigateway put-method-response \
        --rest-api-id $API_ID \
        --resource-id $RESOURCE_ID \
        --http-method GET \
        --status-code 200

    # 設置整合響應
    aws $AWS_COMMON_ARGS apigateway put-integration-response \
        --rest-api-id $API_ID \
        --resource-id $RESOURCE_ID \
        --http-method GET \
        --status-code 200
done

# 部署 API
DEPLOYMENT_ID=$(aws $AWS_COMMON_ARGS apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name dev \
    --query 'id' --output text)

echo -e "${GREEN}✅ API Gateway 已部署，部署 ID: $DEPLOYMENT_ID${NC}"

# 測試 API Gateway
echo -e "\n${YELLOW}5. 測試 API Gateway...${NC}"

# 正確格式的 API Gateway URL
API_URL="$AWS_ENDPOINT/restapis/$API_ID/dev/_user_request_"

echo -e "${CYAN}API Gateway URL: $API_URL${NC}"

# 等待 API Gateway 部署完成
echo -e "${YELLOW}等待 API Gateway 部署完成...${NC}"
sleep 5

# 測試用戶查詢
echo -e "\n${CYAN}測試用戶查詢:${NC}"
USER_QUERY_RESULT=$(curl -s "$API_URL/query/user?user_id=test_user_001")
echo "$USER_QUERY_RESULT" | jq .

# 測試行銷活動查詢
echo -e "\n${CYAN}測試行銷活動查詢:${NC}"
MARKETING_QUERY_RESULT=$(curl -s "$API_URL/query/marketing?marketing_id=campaign_2024_new_year")
echo "$MARKETING_QUERY_RESULT" | jq .

# 測試失敗記錄查詢
echo -e "\n${CYAN}測試失敗記錄查詢:${NC}"
FAIL_QUERY_RESULT=$(curl -s "$API_URL/query/fail?transaction_id=tx_002")
echo "$FAIL_QUERY_RESULT" | jq .

echo -e "\n${GREEN}✅ API Gateway 修復完成${NC}"
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}🔗 API Gateway 資訊:${NC}"
echo -e "${CYAN}API ID: $API_ID${NC}"
echo -e "${CYAN}API URL: $API_URL${NC}"
echo -e "${GREEN}======================================${NC}"
echo -e "${YELLOW}測試命令:${NC}"
echo -e "${GRAY}curl \"$API_URL/query/user?user_id=test_user_001\"${NC}"
echo -e "${GRAY}curl \"$API_URL/query/marketing?marketing_id=campaign_2024_new_year\"${NC}"
echo -e "${GRAY}curl \"$API_URL/query/fail?transaction_id=tx_002\"${NC}"
echo -e ""
