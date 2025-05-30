#!/bin/bash

# ANSI 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

echo -e "\n${CYAN}系統環境驗證工具${NC}"
echo -e "${GRAY}===================${NC}\n"

# 檢查必要工具
echo -e "${YELLOW}1. 檢查必要工具...${NC}"

# 定義需要檢查的命令
REQUIRED_COMMANDS=("docker" "docker-compose" "aws" "jq" "curl" "python3")
MISSING_COMMANDS=()

for cmd in "${REQUIRED_COMMANDS[@]}"; do
    echo -ne "${GRAY}檢查 $cmd...${NC}"
    if command -v $cmd &> /dev/null; then
        echo -e "${GREEN}✅${NC}"
    else
        echo -e "${RED}❌${NC}"
        MISSING_COMMANDS+=("$cmd")
    fi
done

if [ ${#MISSING_COMMANDS[@]} -gt 0 ]; then
    echo -e "\n${RED}❌ 缺少以下必要工具:${NC}"
    for cmd in "${MISSING_COMMANDS[@]}"; do
        echo -e "${RED}  - $cmd${NC}"
    done
    echo -e "\n${YELLOW}請安裝缺少的工具後再繼續${NC}"
else
    echo -e "\n${GREEN}✅ 所有必要工具都已安裝${NC}"
fi

# 檢查 Docker 服務
echo -e "\n${YELLOW}2. 檢查 Docker 服務...${NC}"
docker info &> /dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker 服務正常運行${NC}"
else
    echo -e "${RED}❌ Docker 服務未運行${NC}"
    echo -e "${YELLOW}請啟動 Docker 服務後再繼續${NC}"
fi

# 檢查 AWS CLI 配置
echo -e "\n${YELLOW}3. 檢查 AWS CLI 配置...${NC}"
aws --version
echo -e "${YELLOW}注意: 在使用 LocalStack 時，請確保使用以下憑證:${NC}"
echo -e "${CYAN}export AWS_ACCESS_KEY_ID=test${NC}"
echo -e "${CYAN}export AWS_SECRET_ACCESS_KEY=test${NC}"
echo -e "${CYAN}export AWS_DEFAULT_REGION=us-east-1${NC}"

# 檢查 Python 版本和依賴
echo -e "\n${YELLOW}4. 檢查 Python 環境...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1)
echo -e "${CYAN}Python 版本: $PYTHON_VERSION${NC}"

# 檢查目錄結構
echo -e "\n${YELLOW}5. 檢查專案目錄結構...${NC}"
if [ -d "query-service" ]; then
    echo -e "${GREEN}✅ query-service 目錄存在${NC}"
else
    echo -e "${RED}❌ query-service 目錄不存在${NC}"
fi

if [ -d "scripts" ]; then
    echo -e "${GREEN}✅ scripts 目錄存在${NC}"
else
    echo -e "${RED}❌ scripts 目錄不存在${NC}"
fi

# 檢查腳本權限
echo -e "\n${YELLOW}6. 檢查腳本執行權限...${NC}"
SCRIPT_COUNT=$(find scripts -name "*.sh" | wc -l)
EXECUTABLE_COUNT=$(find scripts -name "*.sh" -executable | wc -l)

echo -e "${CYAN}找到 $SCRIPT_COUNT 個腳本，其中 $EXECUTABLE_COUNT 個有執行權限${NC}"

if [ $SCRIPT_COUNT -ne $EXECUTABLE_COUNT ]; then
    echo -e "${YELLOW}⚠️ 部分腳本缺少執行權限，運行以下命令設置:${NC}"
    echo -e "${GRAY}chmod +x scripts/*.sh scripts/*/*.sh${NC}"
else
    echo -e "${GREEN}✅ 所有腳本都有執行權限${NC}"
fi

# 檢查 LocalStack 容器
echo -e "\n${YELLOW}7. 檢查 LocalStack 容器...${NC}"
LOCALSTACK_RUNNING=$(docker ps --filter "name=localstack-query-service" --format "{{.Names}}" | grep localstack-query-service)

if [ -n "$LOCALSTACK_RUNNING" ]; then
    echo -e "${GREEN}✅ LocalStack 容器正在運行${NC}"

    # 檢查 LocalStack 健康狀況
    echo -e "\n${YELLOW}8. 檢查 LocalStack 健康狀況...${NC}"
    HEALTH_RESPONSE=$(curl -s "http://localhost:4566/health")
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ LocalStack 正常運行${NC}"
        echo "$HEALTH_RESPONSE" | jq .

        # 檢查必要的 AWS 資源
        echo -e "\n${YELLOW}9. 檢查 AWS 資源...${NC}"

        # 設置臨時憑證
        export AWS_ACCESS_KEY_ID=test
        export AWS_SECRET_ACCESS_KEY=test
        export AWS_DEFAULT_REGION=us-east-1

        # 檢查 DynamoDB 表
        TABLES=$(aws --endpoint-url=http://localhost:4566 dynamodb list-tables --query "TableNames" --output text)
        if [[ $TABLES == *"command-records"* ]] && [[ $TABLES == *"notification-records"* ]]; then
            echo -e "${GREEN}✅ DynamoDB 表存在: command-records, notification-records${NC}"
        else
            echo -e "${RED}❌ DynamoDB 表缺失${NC}"
        fi

        # 檢查 Lambda 函數
        LAMBDA_FUNCTIONS=$(aws --endpoint-url=http://localhost:4566 lambda list-functions --query "Functions[].FunctionName" --output text)
        if [[ $LAMBDA_FUNCTIONS == *"stream_processor"* ]] && [[ $LAMBDA_FUNCTIONS == *"query_lambda"* ]]; then
            echo -e "${GREEN}✅ Lambda 函數存在: stream_processor, query_lambda${NC}"
        else
            echo -e "${RED}❌ Lambda 函數缺失${NC}"
        fi

        # 檢查 API Gateway
        API_ID=$(aws --endpoint-url=http://localhost:4566 apigateway get-rest-apis --query 'items[0].id' --output text)
        if [ -n "$API_ID" ]; then
            echo -e "${GREEN}✅ API Gateway 存在，ID: $API_ID${NC}"
        else
            echo -e "${RED}❌ API Gateway 不存在${NC}"
            echo -e "${YELLOW}⚠️ 請執行: ./scripts/fix_api_gateway.sh${NC}"
        fi
    else
        echo -e "${RED}❌ 無法連接到 LocalStack 健康檢查 API${NC}"
    fi
else
    echo -e "${RED}❌ LocalStack 容器未運行${NC}"
    echo -e "${YELLOW}⚠️ 請執行: ./scripts/restart_services.sh${NC}"
fi

# 檢查 EKS Handler
echo -e "\n${YELLOW}10. 檢查 EKS Handler...${NC}"
EKS_RUNNING=$(docker ps --filter "name=eks-handler" --format "{{.Names}}" | grep eks-handler)

if [ -n "$EKS_RUNNING" ]; then
    echo -e "${GREEN}✅ EKS Handler 容器正在運行${NC}"

    # 檢查 EKS Handler 健康狀況
    EKS_HEALTH=$(curl -s "http://localhost:8000/health")
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ EKS Handler 正常運行${NC}"
        echo "$EKS_HEALTH" | jq .
    else
        echo -e "${RED}❌ 無法連接到 EKS Handler 健康檢查 API${NC}"
    fi
else
    echo -e "${RED}❌ EKS Handler 容器未運行${NC}"
    echo -e "${YELLOW}⚠️ 請執行: ./scripts/restart_services.sh${NC}"
fi

echo -e "\n${GREEN}✅ 系統驗證完成${NC}"
echo -e "${GREEN}======================================${NC}"
echo -e "${YELLOW}建議操作:${NC}"

if [ ${#MISSING_COMMANDS[@]} -gt 0 ] || [ -z "$LOCALSTACK_RUNNING" ] || [ -z "$EKS_RUNNING" ]; then
    echo -e "${GRAY}1. 安裝缺少的工具${NC}"
    echo -e "${GRAY}2. 執行 ./scripts/restart_services.sh${NC}"
    echo -e "${GRAY}3. 執行 ./scripts/fix_api_gateway.sh${NC}"
    echo -e "${GRAY}4. 執行 ./scripts/testing/test_full_flow.sh${NC}"
else
    echo -e "${GRAY}1. 執行 ./scripts/testing/quick_test.sh${NC}"
    echo -e "${GRAY}2. 執行 ./scripts/testing/test_full_flow.sh${NC}"
fi
echo -e ""
