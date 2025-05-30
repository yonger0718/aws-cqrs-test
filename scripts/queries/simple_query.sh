#!/bin/bash

# 簡化的查詢工具
# 取代複雜的PowerShell查詢腳本

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# 端點設定
AWS_ENDPOINT="http://localhost:4566"
EKS_ENDPOINT="http://localhost:8000"

# 設置臨時憑證
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

echo -e "\n${CYAN}簡化查詢工具${NC}"
echo -e "${GRAY}============${NC}\n"

# 函數：檢查服務狀態
check_services() {
    echo -e "${YELLOW}1. 檢查服務狀態...${NC}"

    # 檢查 LocalStack
    if curl -s "$AWS_ENDPOINT/health" >/dev/null; then
        echo -e "${GREEN}✅ LocalStack 運行中${NC}"
    else
        echo -e "${RED}❌ LocalStack 未運行${NC}"
        return 1
    fi

    # 檢查 EKS Handler
    if curl -s "$EKS_ENDPOINT/health" >/dev/null; then
        echo -e "${GREEN}✅ EKS Handler 運行中${NC}"
    else
        echo -e "${RED}❌ EKS Handler 未運行${NC}"
        return 1
    fi
}

# 函數：查詢 DynamoDB 表
query_dynamodb() {
    echo -e "\n${YELLOW}2. DynamoDB 表查詢...${NC}"

    # 列出表
    echo -e "${CYAN}表列表:${NC}"
    aws --endpoint-url=$AWS_ENDPOINT dynamodb list-tables --query "TableNames[]" --output text | tr '\t' '\n' | while read table; do
        echo -e "  - ${CYAN}$table${NC}"
    done

    # 檢查 command-records 表數據
    echo -e "\n${CYAN}command-records 表統計:${NC}"
    COMMAND_COUNT=$(aws --endpoint-url=$AWS_ENDPOINT dynamodb scan --table-name command-records --select "COUNT" --query "Count" --output text)
    echo -e "  記錄數: ${GREEN}$COMMAND_COUNT${NC}"

    # 檢查 notification-records 表數據
    echo -e "\n${CYAN}notification-records 表統計:${NC}"
    NOTIFICATION_COUNT=$(aws --endpoint-url=$AWS_ENDPOINT dynamodb scan --table-name notification-records --select "COUNT" --query "Count" --output text)
    echo -e "  記錄數: ${GREEN}$NOTIFICATION_COUNT${NC}"
}

# 函數：測試查詢 API
test_query_api() {
    echo -e "\n${YELLOW}3. 測試查詢 API...${NC}"

    # 用戶查詢
    echo -e "${CYAN}用戶查詢 (test_user_001):${NC}"
    USER_RESULT=$(curl -s -X POST "$EKS_ENDPOINT/query/user" -H "Content-Type: application/json" -d '{"user_id":"test_user_001"}')
    echo "$USER_RESULT" | jq .

    # 行銷活動查詢
    echo -e "\n${CYAN}行銷活動查詢 (campaign_2024_test):${NC}"
    MARKETING_RESULT=$(curl -s -X POST "$EKS_ENDPOINT/query/marketing" -H "Content-Type: application/json" -d '{"marketing_id":"campaign_2024_test"}')
    echo "$MARKETING_RESULT" | jq .
}

# 函數：顯示選單
show_menu() {
    echo -e "\n${YELLOW}選擇操作:${NC}"
    echo -e "${GREEN}1) 檢查服務狀態${NC}"
    echo -e "${GREEN}2) 查詢 DynamoDB 表${NC}"
    echo -e "${GREEN}3) 測試查詢 API${NC}"
    echo -e "${GREEN}4) 全部執行${NC}"
    echo -e "${RED}0) 退出${NC}"
    echo -e ""
}

# 主程序
main() {
    if [ "$1" = "--all" ]; then
        check_services && query_dynamodb && test_query_api
        return
    fi

    while true; do
        show_menu
        read -p "請選擇 (0-4): " choice

        case $choice in
            1) check_services ;;
            2) query_dynamodb ;;
            3) test_query_api ;;
            4) check_services && query_dynamodb && test_query_api ;;
            0) echo -e "${GREEN}退出${NC}"; break ;;
            *) echo -e "${RED}無效選擇${NC}" ;;
        esac

        echo -e "\n${GRAY}按 Enter 繼續...${NC}"
        read
    done
}

# 執行主程序
main "$@"
