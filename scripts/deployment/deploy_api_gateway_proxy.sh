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

# 端點設定
AWS_ENDPOINT="$LOCALSTACK_ENDPOINT"
AWS_REGION="$AWS_DEFAULT_REGION"

echo -e "\n${CYAN}部署 API Gateway 代理 Lambda${NC}"
echo -e "${GRAY}==============================${NC}\n"

# 進入 Lambda 目錄
cd "$PROJECT_ROOT/query-service/lambdas/api_gateway_proxy"

# 檢查 Lambda 函數是否存在
echo -e "${YELLOW}1. 檢查現有 Lambda 函數...${NC}"
FUNCTION_EXISTS=$(aws --endpoint-url=$AWS_ENDPOINT lambda get-function --function-name api_gateway_proxy 2>/dev/null)

if [ $? -eq 0 ]; then
    echo -e "${YELLOW}Lambda 函數已存在，正在更新...${NC}"

    # 創建部署包
    zip -r function.zip app.py

    # 更新函數代碼
    aws --endpoint-url=$AWS_ENDPOINT lambda update-function-code \
        --function-name api_gateway_proxy \
        --zip-file fileb://function.zip

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Lambda 函數代碼更新成功${NC}"
    else
        echo -e "${RED}❌ Lambda 函數代碼更新失敗${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}創建新的 Lambda 函數...${NC}"

    # 創建部署包
    zip -r function.zip app.py

    # 創建 Lambda 函數
    aws --endpoint-url=$AWS_ENDPOINT lambda create-function \
        --function-name api_gateway_proxy \
        --runtime python3.12 \
        --role arn:aws:iam::000000000000:role/lambda-role \
        --handler app.lambda_handler \
        --zip-file fileb://function.zip \
        --description "API Gateway 到 EKS Handler 的代理函數"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Lambda 函數創建成功${NC}"
    else
        echo -e "${RED}❌ Lambda 函數創建失敗${NC}"
        exit 1
    fi
fi

# 清理
rm -f function.zip

# 返回項目根目錄
cd "$PROJECT_ROOT"

echo -e "\n${YELLOW}2. 重新配置 API Gateway...${NC}"

# 運行 API Gateway 修復腳本
./scripts/infrastructure/fix_api_gateway.sh

echo -e "\n${GREEN}✅ API Gateway 代理部署完成${NC}"
