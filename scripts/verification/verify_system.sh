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

# 檢查必要的工具是否已安裝
echo -e "${YELLOW}1. 檢查必要工具...${NC}"

REQUIRED_COMMANDS=("docker" "aws" "jq" "curl" "python3")
MISSING_COMMANDS=()

for cmd in "${REQUIRED_COMMANDS[@]}"; do
    echo -n "檢查 $cmd..."
    if command -v $cmd &> /dev/null; then
        echo -e "${GREEN}✅${NC}"
    else
        echo -e "${RED}❌${NC}"
        MISSING_COMMANDS+=("$cmd")
    fi
done

# 檢查 docker compose 命令（新版本）
echo -n "檢查 docker compose..."
if docker compose version &> /dev/null; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌${NC}"
    MISSING_COMMANDS+=("docker compose")
fi

if [ ${#MISSING_COMMANDS[@]} -gt 0 ]; then
    echo -e "\n${RED}❌ 缺少以下必要工具:${NC}"
    for cmd in "${MISSING_COMMANDS[@]}"; do
        echo -e "${RED}  - $cmd${NC}"
    done
    echo -e "\n${YELLOW}請安裝缺少的工具後再繼續${NC}\n"
else
    echo -e "\n${GREEN}✅ 所有必要工具都已安裝${NC}\n"
fi

# 檢查 Docker 服務
echo -e "${YELLOW}2. 檢查 Docker 服務...${NC}"
if docker info &> /dev/null; then
    echo -e "${GREEN}✅ Docker 服務正常運行${NC}\n"
else
    echo -e "${RED}❌ Docker 服務未運行${NC}"
    echo -e "${YELLOW}⚠️ 請啟動 Docker 服務${NC}\n"
fi

# 檢查 AWS CLI 配置
echo -e "${YELLOW}3. 檢查 AWS CLI 配置...${NC}"
aws --version
echo -e "${GRAY}注意: 在使用 LocalStack 時，請確保使用以下憑證:${NC}"
echo -e "${GRAY}export AWS_ACCESS_KEY_ID=test${NC}"
echo -e "${GRAY}export AWS_SECRET_ACCESS_KEY=test${NC}"
echo -e "${GRAY}export AWS_DEFAULT_REGION=us-east-1${NC}\n"

# 檢查 Python 環境
echo -e "${YELLOW}4. 檢查 Python 環境...${NC}"
echo -n "Python 版本: "
python3 --version
echo ""

# 檢查專案目錄結構
echo -e "${YELLOW}5. 檢查專案目錄結構...${NC}"
REQUIRED_DIRS=("query-service" "scripts")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✅ $dir 目錄存在${NC}"
    else
        echo -e "${RED}❌ $dir 目錄不存在${NC}"
    fi
done
echo ""

# 檢查腳本執行權限
echo -e "${YELLOW}6. 檢查腳本執行權限...${NC}"
SCRIPT_COUNT=$(find scripts -name "*.sh" | wc -l)
EXECUTABLE_COUNT=$(find scripts -name "*.sh" -executable | wc -l)
echo -e "${GRAY}找到 $SCRIPT_COUNT 個腳本，其中 $EXECUTABLE_COUNT 個有執行權限${NC}"

if [ $SCRIPT_COUNT -eq $EXECUTABLE_COUNT ]; then
    echo -e "${GREEN}✅ 所有腳本都有執行權限${NC}\n"
else
    echo -e "${YELLOW}⚠️ 某些腳本可能沒有執行權限${NC}"
    echo -e "${GRAY}可執行: chmod +x scripts/**/*.sh${NC}\n"
fi

# 檢查 LocalStack 容器狀態
echo -e "${YELLOW}7. 檢查 LocalStack 容器...${NC}"
if docker ps | grep -q "localstack-query-service"; then
    echo -e "${GREEN}✅ LocalStack 容器正在運行${NC}"

    # 檢查 LocalStack 健康狀態
    echo -e "${GRAY}檢查 LocalStack 健康狀態...${NC}"
    HEALTH_RESPONSE=$(curl -s "http://localhost:4566/_localstack/health" 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ LocalStack 服務響應正常${NC}"
    else
        echo -e "${YELLOW}⚠️ LocalStack 服務可能未完全就緒${NC}"
    fi
else
    echo -e "${RED}❌ LocalStack 容器未運行${NC}"
    echo -e "${YELLOW}⚠️ 請執行: ./scripts/restart_services.sh${NC}"
fi
echo ""

# 檢查 query-service 配置
echo -e "${YELLOW}8. 檢查 query-service 配置...${NC}"
if [ -f "query-service/docker-compose.yml" ]; then
    echo -e "${GREEN}✅ docker-compose.yml 存在${NC}"
else
    echo -e "${RED}❌ docker-compose.yml 不存在${NC}"
fi

if [ -f "query-service/eks_handler/requirements.txt" ]; then
    echo -e "${GREEN}✅ requirements.txt 存在${NC}"
else
    echo -e "${RED}❌ requirements.txt 不存在${NC}"
fi
echo ""

# 檢查端口佔用
echo -e "${YELLOW}9. 檢查端口佔用...${NC}"
PORTS=(4566 8000)
for port in "${PORTS[@]}"; do
    if lsof -i:$port &> /dev/null; then
        echo -e "${GREEN}✅ 端口 $port 已被使用 (正常)${NC}"
    else
        echo -e "${YELLOW}⚠️ 端口 $port 未被使用${NC}"
    fi
done
echo ""

# 檢查 EKS Handler
echo -e "${YELLOW}10. 檢查 EKS Handler...${NC}"
if docker ps | grep -q "eks-handler"; then
    echo -e "${GREEN}✅ EKS Handler 容器正在運行${NC}"

    # 檢查 EKS Handler 健康狀態
    echo -e "${GRAY}檢查 EKS Handler 健康狀態...${NC}"
    HEALTH_RESPONSE=$(curl -s "http://localhost:8000/health" 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ EKS Handler 服務響應正常${NC}"
    else
        echo -e "${YELLOW}⚠️ EKS Handler 服務可能未完全就緒${NC}"
    fi
else
    echo -e "${RED}❌ EKS Handler 容器未運行${NC}"
    echo -e "${YELLOW}⚠️ 請執行: ./scripts/restart_services.sh${NC}"
fi

echo -e "\n${GREEN}✅ 系統驗證完成${NC}"
echo -e "${GREEN}======================================${NC}"
echo -e "${YELLOW}建議操作:${NC}"

if [ ${#MISSING_COMMANDS[@]} -gt 0 ]; then
    echo -e "${GRAY}1. 安裝缺少的工具${NC}"
    echo -e "${GRAY}2. 執行 ./scripts/restart_services.sh${NC}"
    echo -e "${GRAY}3. 執行 ./scripts/fix_api_gateway.sh${NC}"
    echo -e "${GRAY}4. 執行 ./scripts/testing/test_full_flow.sh${NC}"
else
    echo -e "${GRAY}1. 執行 ./scripts/restart_services.sh${NC}"
    echo -e "${GRAY}2. 執行 ./scripts/fix_api_gateway.sh${NC}"
    echo -e "${GRAY}3. 執行 ./scripts/testing/quick_test.sh${NC}"
    echo -e "${GRAY}4. 執行 ./scripts/testing/test_full_flow.sh${NC}"
fi

echo -e ""
