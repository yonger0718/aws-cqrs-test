#!/bin/bash

# CQRS LocalStack 環境變量設置腳本
# 使用方法: source scripts/development/setup_env.sh

# ANSI 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}設置 LocalStack 環境變量...${NC}"

# AWS 憑證配置 (LocalStack 測試環境)
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=ap-southeast-1

# LocalStack 端點配置
export LOCALSTACK_ENDPOINT=http://localhost:4566

# EKS Handler 端點配置
export EKS_HANDLER_ENDPOINT=http://localhost:8000

# API Gateway 配置
export API_GATEWAY_ENDPOINT=http://localhost:4566

echo -e "${GREEN}✅ 環境變量設置完成${NC}"
echo -e "${YELLOW}已設置的環境變量:${NC}"
echo -e "${CYAN}  AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID${NC}"
echo -e "${CYAN}  AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY${NC}"
echo -e "${CYAN}  AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION${NC}"
echo -e "${CYAN}  LOCALSTACK_ENDPOINT=$LOCALSTACK_ENDPOINT${NC}"
echo -e "${CYAN}  EKS_HANDLER_ENDPOINT=$EKS_HANDLER_ENDPOINT${NC}"
echo -e "${CYAN}  API_GATEWAY_ENDPOINT=$API_GATEWAY_ENDPOINT${NC}"
echo -e ""
echo -e "${YELLOW}提示: 要在其他終端中使用這些變量，請執行:${NC}"
echo -e "${GRAY}  source scripts/development/setup_env.sh${NC}"
echo -e ""
