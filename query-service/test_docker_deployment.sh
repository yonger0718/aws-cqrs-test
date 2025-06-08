#!/bin/bash

# 測試 Docker Lambda 部署腳本
set -e

# ANSI 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}🧪 測試 Docker Lambda 部署${NC}"
echo "=================================="

# 檢查 LocalStack 健康狀態
echo -e "${YELLOW}檢查 LocalStack 狀態...${NC}"
if ! curl -f http://localhost:4566/_localstack/health > /dev/null 2>&1; then
    echo -e "${RED}❌ LocalStack 未運行${NC}"
    exit 1
fi
echo -e "${GREEN}✅ LocalStack 運行正常${NC}"

# 檢查 Docker 映像
echo -e "${YELLOW}檢查 Docker 映像...${NC}"
for image in "query-service-stream-processor-lambda:latest" "query-service-query-lambda:latest" "query-service-query-result-lambda:latest"; do
    if docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "$image"; then
        echo -e "${GREEN}✅ $image 存在${NC}"
    else
        echo -e "${RED}❌ $image 不存在${NC}"
        exit 1
    fi
done

# 創建 IAM 角色
echo -e "${YELLOW}創建 IAM 角色...${NC}"
docker exec localstack-query-service aws iam create-role \
    --role-name lambda-role \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }' --region ap-southeast-1 > /dev/null 2>&1 || echo "角色可能已存在"

# 創建 DynamoDB 表
echo -e "${YELLOW}創建 DynamoDB 表...${NC}"
docker exec localstack-query-service aws dynamodb create-table \
    --table-name notification-records \
    --attribute-definitions \
        AttributeName=user_id,AttributeType=S \
        AttributeName=created_at,AttributeType=N \
    --key-schema \
        AttributeName=user_id,KeyType=HASH \
        AttributeName=created_at,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region ap-southeast-1 > /dev/null 2>&1 || echo "表可能已存在"

# 部署 Lambda 函數
echo -e "${YELLOW}部署 Lambda 函數...${NC}"

# Query Lambda
echo -e "${CYAN}部署 query-lambda...${NC}"
docker exec localstack-query-service aws lambda create-function \
    --function-name query-service-query-lambda \
    --package-type Image \
    --code ImageUri=query-service-query-lambda:latest \
    --role arn:aws:iam::000000000000:role/lambda-role \
    --environment Variables='{EKS_HANDLER_URL=http://ecs-handler:8000,REQUEST_TIMEOUT=10}' \
    --timeout 30 \
    --memory-size 512 \
    --region ap-southeast-1 > /dev/null 2>&1 || echo "函數可能已存在，嘗試更新..."

# 如果創建失敗，嘗試更新
docker exec localstack-query-service aws lambda update-function-code \
    --function-name query-service-query-lambda \
    --image-uri query-service-query-lambda:latest \
    --region ap-southeast-1 > /dev/null 2>&1 || true

# Stream Processor Lambda
echo -e "${CYAN}部署 stream-processor-lambda...${NC}"
docker exec localstack-query-service aws lambda create-function \
    --function-name query-service-stream-processor-lambda \
    --package-type Image \
    --code ImageUri=query-service-stream-processor-lambda:latest \
    --role arn:aws:iam::000000000000:role/lambda-role \
    --environment Variables='{LOCALSTACK_HOSTNAME=localstack,AWS_REGION=ap-southeast-1,NOTIFICATION_TABLE_NAME=notification-records}' \
    --timeout 30 \
    --memory-size 512 \
    --region ap-southeast-1 > /dev/null 2>&1 || echo "函數可能已存在，嘗試更新..."

docker exec localstack-query-service aws lambda update-function-code \
    --function-name query-service-stream-processor-lambda \
    --image-uri query-service-stream-processor-lambda:latest \
    --region ap-southeast-1 > /dev/null 2>&1 || true

# Query Result Lambda
echo -e "${CYAN}部署 query-result-lambda...${NC}"
docker exec localstack-query-service aws lambda create-function \
    --function-name query-service-query-result-lambda \
    --package-type Image \
    --code ImageUri=query-service-query-result-lambda:latest \
    --role arn:aws:iam::000000000000:role/lambda-role \
    --environment Variables='{LOCALSTACK_HOSTNAME=localstack,AWS_REGION=ap-southeast-1,NOTIFICATION_TABLE_NAME=notification-records}' \
    --timeout 30 \
    --memory-size 512 \
    --region ap-southeast-1 > /dev/null 2>&1 || echo "函數可能已存在，嘗試更新..."

docker exec localstack-query-service aws lambda update-function-code \
    --function-name query-service-query-result-lambda \
    --image-uri query-service-query-result-lambda:latest \
    --region ap-southeast-1 > /dev/null 2>&1 || true

echo -e "${GREEN}✅ Lambda 函數部署完成${NC}"

# 驗證部署
echo -e "${YELLOW}驗證部署...${NC}"
echo -e "${CYAN}Lambda 函數列表:${NC}"
docker exec localstack-query-service aws lambda list-functions \
    --query 'Functions[].FunctionName' \
    --output table \
    --region ap-southeast-1

# 測試 Lambda 函數
echo -e "${YELLOW}測試 Lambda 函數...${NC}"
echo -e "${CYAN}測試 query-lambda...${NC}"
docker exec localstack-query-service aws lambda invoke \
    --function-name query-service-query-lambda \
    --payload '{"user_id": "test_user", "query_type": "user"}' \
    /tmp/test_output.json \
    --region ap-southeast-1 > /dev/null 2>&1 && echo -e "${GREEN}✅ query-lambda 測試成功${NC}" || echo -e "${RED}❌ query-lambda 測試失敗${NC}"

echo -e "${GREEN}🎉 Docker Lambda 部署測試完成！${NC}"
