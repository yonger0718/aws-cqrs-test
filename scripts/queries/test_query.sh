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
HEALTH_RESPONSE=$(curl -s "$AWS_ENDPOINT/health")
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ LocalStack 正常運行${NC}"
    echo "$HEALTH_RESPONSE" | jq .
else
    echo -e "${RED}❌ LocalStack 連接失敗${NC}"
fi

# 獲取 API Gateway ID
echo -e "\n${YELLOW}2. 獲取 API Gateway ID...${NC}"
API_ID=$(aws --endpoint-url=$AWS_ENDPOINT --region $AWS_REGION apigateway get-rest-apis --query 'items[0].id' --output text)
if [ -z "$API_ID" ]; then
    echo -e "${RED}❌ 無法獲取 API Gateway ID${NC}"
    echo -e "${YELLOW}嘗試使用其他方法獲取 API Gateway ID...${NC}"

    # 嘗試列出所有 API 並選擇第一個
    API_LIST=$(aws --endpoint-url=$AWS_ENDPOINT --region $AWS_REGION apigateway get-rest-apis)
    if [ $? -eq 0 ]; then
        echo "$API_LIST" | jq .
        echo -e "${YELLOW}請從上面的列表中找到 'Query Service API' 並手動輸入其 ID:${NC}"
        read API_ID
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
