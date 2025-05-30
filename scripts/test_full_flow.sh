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
AWS_REGION="us-east-1"

# 設置臨時憑證
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=$AWS_REGION

echo -e "\n${CYAN}CQRS 完整流程測試${NC}"
echo -e "${GRAY}===================${NC}\n"

# 檢查 LocalStack 健康狀況
echo -e "${YELLOW}1. 檢查 LocalStack 和 EKS Handler 狀態...${NC}"
LOCALSTACK_HEALTH=$(curl -s "$AWS_ENDPOINT/health")
EKS_HEALTH=$(curl -s "$EKS_ENDPOINT/health")

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ LocalStack 正常運行${NC}"
    echo "$LOCALSTACK_HEALTH" | jq .services | jq -r 'to_entries | .[] | "\(.key) : \(.value)"' | grep -E "dynamodb|lambda|apigateway" | while read line; do
        echo -e "  ${CYAN}$line${NC}"
    done
else
    echo -e "${RED}❌ LocalStack 連接失敗${NC}"
    exit 1
fi

if [[ -n "$EKS_HEALTH" ]]; then
    echo -e "${GREEN}✅ EKS Handler 正常運行${NC}"
    echo -e "  ${CYAN}$(echo "$EKS_HEALTH" | jq -r '.status // "unknown"')${NC}"
else
    echo -e "${RED}❌ EKS Handler 連接失敗${NC}"
    exit 1
fi

# 清除現有的測試數據
echo -e "\n${YELLOW}2. 清除現有的測試數據...${NC}"

# 清除命令記錄表中的測試數據
COMMAND_ITEMS=$(aws --endpoint-url=$AWS_ENDPOINT dynamodb scan --table-name command-records --select "COUNT")
COMMAND_COUNT=$(echo "$COMMAND_ITEMS" | jq -r '.Count')
echo -e "${CYAN}命令記錄表現有數據: $COMMAND_COUNT 條${NC}"

# 清除通知記錄表中的測試數據
NOTIFICATION_ITEMS=$(aws --endpoint-url=$AWS_ENDPOINT dynamodb scan --table-name notification-records --select "COUNT")
NOTIFICATION_COUNT=$(echo "$NOTIFICATION_ITEMS" | jq -r '.Count')
echo -e "${CYAN}通知記錄表現有數據: $NOTIFICATION_COUNT 條${NC}"

# 插入新的測試數據
echo -e "\n${YELLOW}3. 插入新的測試數據...${NC}"

TIMESTAMP=$(date +%s)000
TEST_ID="test_$(date +%s)"

# 插入命令記錄
echo -e "${CYAN}插入命令記錄: transaction_id = $TEST_ID${NC}"
aws --endpoint-url=$AWS_ENDPOINT dynamodb put-item \
    --table-name command-records \
    --item '{
        "transaction_id": {"S": "'$TEST_ID'"},
        "created_at": {"N": "'$TIMESTAMP'"},
        "user_id": {"S": "test_user_001"},
        "marketing_id": {"S": "campaign_2024_test"},
        "notification_title": {"S": "測試通知"},
        "status": {"S": "DELIVERED"},
        "platform": {"S": "IOS"},
        "device_token": {"S": "ios_token_test"},
        "payload": {"S": "{\"title\": \"測試通知\", \"body\": \"這是一個測試通知內容\"}"}
    }'

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 命令記錄插入成功${NC}"
else
    echo -e "${RED}❌ 命令記錄插入失敗${NC}"
    exit 1
fi

# 等待 DynamoDB Stream 處理
echo -e "\n${YELLOW}4. 等待 DynamoDB Stream 處理 (10 秒)...${NC}"
for i in {1..10}; do
    echo -e "${GRAY}等待中... $i/10${NC}"
    sleep 1
done

# 檢查通知記錄表是否有新數據
echo -e "\n${YELLOW}5. 檢查 Stream 處理結果...${NC}"
NOTIFICATION_ITEMS_AFTER=$(aws --endpoint-url=$AWS_ENDPOINT dynamodb scan --table-name notification-records --select "COUNT")
NOTIFICATION_COUNT_AFTER=$(echo "$NOTIFICATION_ITEMS_AFTER" | jq -r '.Count')
echo -e "${CYAN}通知記錄表現有數據: $NOTIFICATION_COUNT_AFTER 條${NC}"

if [ $NOTIFICATION_COUNT_AFTER -gt $NOTIFICATION_COUNT ]; then
    echo -e "${GREEN}✅ DynamoDB Stream 處理成功，通知記錄表中新增了數據${NC}"
else
    echo -e "${YELLOW}⚠️ 通知記錄表數據未增加，可能 Stream 處理失敗${NC}"
fi

# 直接使用 EKS Handler 查詢
echo -e "\n${YELLOW}6. 使用 EKS Handler 直接查詢...${NC}"
USER_QUERY_RESULT=$(curl -s -X POST "$EKS_ENDPOINT/query/user" -H "Content-Type: application/json" -d '{"user_id":"test_user_001"}')
USER_COUNT=$(echo "$USER_QUERY_RESULT" | jq -r '.count')

echo -e "${CYAN}用戶查詢結果 (user_id=test_user_001):${NC}"
echo "$USER_QUERY_RESULT" | jq .

echo -e "\n${CYAN}行銷活動查詢結果 (marketing_id=campaign_2024_test):${NC}"
MARKETING_QUERY_RESULT=$(curl -s -X POST "$EKS_ENDPOINT/query/marketing" -H "Content-Type: application/json" -d '{"marketing_id":"campaign_2024_test"}')
echo "$MARKETING_QUERY_RESULT" | jq .

if [ $USER_COUNT -gt 0 ]; then
    echo -e "${GREEN}✅ 查詢成功，找到 $USER_COUNT 條記錄${NC}"
else
    echo -e "${RED}❌ 查詢未返回任何結果${NC}"
fi

# 檢查 API Gateway
echo -e "\n${YELLOW}7. 檢查 API Gateway...${NC}"
API_ID=$(aws --endpoint-url=$AWS_ENDPOINT apigateway get-rest-apis --query 'items[0].id' --output text)

if [ -z "$API_ID" ]; then
    echo -e "${RED}❌ 無法獲取 API Gateway ID${NC}"
    echo -e "${YELLOW}運行修復腳本...${NC}"
    ./scripts/fix_api_gateway.sh
    API_ID=$(aws --endpoint-url=$AWS_ENDPOINT apigateway get-rest-apis --query 'items[0].id' --output text)
fi

if [ ! -z "$API_ID" ]; then
    echo -e "${GREEN}✅ API Gateway ID: $API_ID${NC}"

    # 修復部署
    echo -e "${YELLOW}重新部署 API Gateway...${NC}"
    aws --endpoint-url=$AWS_ENDPOINT apigateway create-deployment \
        --rest-api-id $API_ID \
        --stage-name dev

    # 正確格式的 API Gateway URL
    API_URL="$AWS_ENDPOINT/restapis/$API_ID/dev/_user_request_"

    echo -e "${CYAN}API Gateway URL: $API_URL${NC}"

    # 測試 API Gateway 端點
    echo -e "\n${YELLOW}8. 測試 API Gateway 查詢...${NC}"

    echo -e "${CYAN}測試用戶查詢:${NC}"
    USER_QUERY_RESULT=$(curl -s "$API_URL/query/user?user_id=test_user_001")
    echo "$USER_QUERY_RESULT" | jq .

    echo -e "\n${CYAN}測試行銷活動查詢:${NC}"
    MARKETING_QUERY_RESULT=$(curl -s "$API_URL/query/marketing?marketing_id=campaign_2024_test")
    echo "$MARKETING_QUERY_RESULT" | jq .
fi

echo -e "\n${GREEN}✅ 完整流程測試完成${NC}"
echo -e "${GREEN}======================================${NC}"
echo -e "${YELLOW}測試命令:${NC}"
echo -e "${GRAY}# 直接使用 EKS Handler${NC}"
echo -e "${GRAY}curl -s -X POST \"$EKS_ENDPOINT/query/user\" -H \"Content-Type: application/json\" -d '{\"user_id\":\"test_user_001\"}' | jq .${NC}"
echo -e ""
echo -e "${GRAY}# 使用 API Gateway${NC}"
echo -e "${GRAY}curl -s \"$API_URL/query/user?user_id=test_user_001\" | jq .${NC}"
echo -e "${GREEN}======================================${NC}"
