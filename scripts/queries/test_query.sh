#!/bin/bash

# ANSI 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# 端點設定
AWS_ENDPOINT="http://localhost:4566"
EKS_ENDPOINT="http://localhost:8000"
AWS_REGION="ap-southeast-1"

# 設置臨時憑證
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=$AWS_REGION

echo -e "\n${CYAN}LocalStack 查詢工具${NC}"
echo -e "${GRAY}===================${NC}\n"

# 測試 LocalStack 健康狀況
echo -e "${YELLOW}1. 測試 LocalStack 健康狀況...${NC}"
HEALTH_RESPONSE=$(curl -s "$AWS_ENDPOINT/_localstack/health")
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ LocalStack 正常運行${NC}"
    echo "$HEALTH_RESPONSE" | jq .
else
    echo -e "${RED}❌ LocalStack 連接失敗${NC}"
fi

# 獲取 API Gateway ID
echo -e "\n${YELLOW}2. 獲取 API Gateway ID...${NC}"

# 獲取腳本目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 使用 Python 輔助工具替代 AWS CLI
API_ID=$(cd "$PROJECT_ROOT" && poetry run python "$SCRIPT_DIR/api_gateway_helper.py" --action first-id --endpoint "$AWS_ENDPOINT" --region "$AWS_REGION" 2>/dev/null)

if [ ! -z "$API_ID" ] && [ "$API_ID" != "" ]; then
    echo -e "${GREEN}✅ 找到 API Gateway ID: $API_ID${NC}"
else
    echo -e "${YELLOW}嘗試列出所有 API Gateway...${NC}"

    # 列出所有 API
    API_LIST=$(cd "$PROJECT_ROOT" && poetry run python "$SCRIPT_DIR/api_gateway_helper.py" --action list --endpoint "$AWS_ENDPOINT" --region "$AWS_REGION" --output json 2>/dev/null)

    if [ $? -eq 0 ] && [ ! -z "$API_LIST" ]; then
        echo "$API_LIST" | jq .

        # 嘗試尋找包含 'query' 的 API
        API_ID=$(cd "$PROJECT_ROOT" && poetry run python "$SCRIPT_DIR/api_gateway_helper.py" --action find-by-name --name "query" --endpoint "$AWS_ENDPOINT" --region "$AWS_REGION" 2>/dev/null)

        if [ ! -z "$API_ID" ] && [ "$API_ID" != "" ]; then
            echo -e "${GREEN}✅ 找到 Query Service API ID: $API_ID${NC}"
        else
            echo -e "${YELLOW}未找到 Query Service API，請手動輸入 API ID (或按 Enter 跳過):${NC}"
            read API_ID
        fi
    else
        echo -e "${RED}❌ 無法列出 API Gateway${NC}"
        echo -e "${YELLOW}直接測試 EKS Handler...${NC}"
    fi
fi

if [ ! -z "$API_ID" ]; then
    echo -e "${GREEN}✅ API Gateway ID: $API_ID${NC}"

    # 正確格式的 API Gateway URL
    API_URL="$AWS_ENDPOINT/restapis/$API_ID/dev/_user_request_"

    # 測試 API Gateway 端點
    echo -e "\n${YELLOW}3. 測試 API Gateway 查詢...${NC}"

    echo -e "${CYAN}測試用戶查詢:${NC}"
    USER_QUERY_RESULT=$(curl -s "$API_URL/query/user?user_id=test_user_001")
    echo "$USER_QUERY_RESULT" | jq .

    echo -e "\n${CYAN}測試行銷活動查詢:${NC}"
    MARKETING_QUERY_RESULT=$(curl -s "$API_URL/query/marketing?marketing_id=campaign_2024_new_year")
    echo "$MARKETING_QUERY_RESULT" | jq .

    echo -e "\n${CYAN}測試失敗記錄查詢:${NC}"
    FAIL_QUERY_RESULT=$(curl -s "$API_URL/query/fail?transaction_id=tx_002")
    echo "$FAIL_QUERY_RESULT" | jq .
fi

# 直接測試 EKS Handler
echo -e "\n${YELLOW}4. 直接測試 EKS Handler...${NC}"

echo -e "${CYAN}健康檢查:${NC}"
EKS_HEALTH=$(curl -s "$EKS_ENDPOINT/health")
echo "$EKS_HEALTH" | jq .

echo -e "\n${CYAN}用戶查詢 (直接 POST 請求):${NC}"
USER_DIRECT=$(curl -s -X POST "$EKS_ENDPOINT/query/user" -H "Content-Type: application/json" -d '{"user_id":"test_user_001"}')
echo "$USER_DIRECT" | jq .

echo -e "\n${CYAN}行銷活動查詢 (直接 POST 請求):${NC}"
MARKETING_DIRECT=$(curl -s -X POST "$EKS_ENDPOINT/query/marketing" -H "Content-Type: application/json" -d '{"marketing_id":"campaign_2024_new_year"}')
echo "$MARKETING_DIRECT" | jq .

echo -e "\n${GREEN}✅ 查詢測試完成${NC}"
