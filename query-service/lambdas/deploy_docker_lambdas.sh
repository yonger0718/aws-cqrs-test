#!/bin/bash

# Lambda Docker 部署腳本
set -e

# ANSI 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# 設置基本變量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 環境變量設定
AWS_REGION=${AWS_REGION:-"ap-southeast-1"}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID:-"000000000000"}
LOCALSTACK_ENDPOINT=${LOCALSTACK_ENDPOINT:-"http://localhost:4566"}

# Lambda 函數配置
declare -A LAMBDA_CONFIGS=(
    ["stream_processor_lambda"]="query-service-stream-processor-lambda"
    ["query_lambda"]="query-service-query-lambda"
    ["query_result_lambda"]="query-service-query-result-lambda"
)

echo -e "\n${CYAN}🐳 Lambda Docker 部署腳本${NC}"
echo -e "${GRAY}======================================${NC}\n"

# 檢查 Docker 是否可用
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 未安裝或不可用${NC}"
    exit 1
fi

# 檢查 Docker 是否運行
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker 守護程序未運行${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker 環境檢查通過${NC}\n"

# 進入 Lambda 目錄
cd "$SCRIPT_DIR"

echo -e "${YELLOW}📦 構建 Lambda Docker 映像...${NC}"

# 使用 Docker Compose 構建所有 Lambda 映像
docker compose -f docker-compose.lambda.yml build --no-cache

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 所有 Lambda Docker 映像構建成功${NC}\n"
else
    echo -e "${RED}❌ Lambda Docker 映像構建失敗${NC}"
    exit 1
fi

echo -e "${YELLOW}🚀 部署 Lambda 函數到 LocalStack...${NC}"

# 檢查 LocalStack 是否運行
if ! curl -f "$LOCALSTACK_ENDPOINT/_localstack/health" &> /dev/null; then
    echo -e "${RED}❌ LocalStack 未運行或不可達: $LOCALSTACK_ENDPOINT${NC}"
    echo -e "${YELLOW}💡 請先啟動 LocalStack: docker compose up localstack${NC}"
    exit 1
fi

echo -e "${GREEN}✅ LocalStack 健康檢查通過${NC}\n"

# 部署每個 Lambda 函數
for lambda_dir in "${!LAMBDA_CONFIGS[@]}"; do
    function_name="${LAMBDA_CONFIGS[$lambda_dir]}"
    image_name="query-service-${lambda_dir//_/-}:latest"

    echo -e "${CYAN}📤 部署 $function_name...${NC}"

    # 檢查函數是否已存在
    existing_function=$(aws --endpoint-url="$LOCALSTACK_ENDPOINT" lambda get-function \
        --function-name "$function_name" 2>/dev/null || echo "")

    if [ -n "$existing_function" ]; then
        echo -e "${YELLOW}🔄 更新現有函數: $function_name${NC}"

        # 更新函數代碼使用 Docker 映像
        aws --endpoint-url="$LOCALSTACK_ENDPOINT" lambda update-function-code \
            --function-name "$function_name" \
            --image-uri "$image_name" \
            --package-type Image
    else
        echo -e "${YELLOW}🆕 創建新函數: $function_name${NC}"

        # 設置環境變量
        case "$lambda_dir" in
            "stream_processor_lambda")
                env_vars='{"LOCALSTACK_HOSTNAME":"localstack","AWS_REGION":"ap-southeast-1","NOTIFICATION_TABLE_NAME":"notification-records"}'
                ;;
            "query_lambda")
                env_vars='{"EKS_HANDLER_URL":"http://ecs-handler:8000","REQUEST_TIMEOUT":"10"}'
                ;;
            "query_result_lambda")
                env_vars='{"LOCALSTACK_HOSTNAME":"localstack","AWS_REGION":"ap-southeast-1","NOTIFICATION_TABLE_NAME":"notification-records"}'
                ;;
            *)
                env_vars='{}'
                ;;
        esac

        # 創建新的 Lambda 函數使用 Docker 映像
        aws --endpoint-url="$LOCALSTACK_ENDPOINT" lambda create-function \
            --function-name "$function_name" \
            --package-type Image \
            --code ImageUri="$image_name" \
            --role "arn:aws:iam::$AWS_ACCOUNT_ID:role/lambda-role" \
            --environment "Variables=$env_vars" \
            --timeout 30 \
            --memory-size 512
    fi

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $function_name 部署成功${NC}"
    else
        echo -e "${RED}❌ $function_name 部署失敗${NC}"
        exit 1
    fi

    echo ""
done

echo -e "${GREEN}🎉 所有 Lambda 函數 Docker 部署完成！${NC}\n"

# 顯示部署摘要
echo -e "${CYAN}📋 部署摘要:${NC}"
echo -e "${GRAY}===================${NC}"
for lambda_dir in "${!LAMBDA_CONFIGS[@]}"; do
    function_name="${LAMBDA_CONFIGS[$lambda_dir]}"
    image_name="query-service-${lambda_dir//_/-}:latest"
    echo -e "• ${YELLOW}$function_name${NC}: $image_name"
done

echo -e "\n${YELLOW}🔍 驗證部署...${NC}"

# 列出所有 Lambda 函數
echo -e "${CYAN}LocalStack Lambda 函數:${NC}"
aws --endpoint-url="$LOCALSTACK_ENDPOINT" lambda list-functions \
    --query 'Functions[].FunctionName' --output table

echo -e "\n${GREEN}✅ Lambda Docker 部署驗證完成${NC}"
