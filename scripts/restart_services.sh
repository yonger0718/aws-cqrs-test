#!/bin/bash

# ANSI 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

echo -e "\n${CYAN}LocalStack 服務重啟工具${NC}"
echo -e "${GRAY}======================${NC}\n"

# 檢查 docker 命令是否可用
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 命令不可用${NC}"
    exit 1
fi

# 檢查 docker compose 命令是否可用
if ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose 命令不可用${NC}"
    echo -e "${YELLOW}請安裝 Docker Compose 或使用較新版本的 Docker${NC}"
    exit 1
fi

# 停止並移除所有容器
echo -e "${YELLOW}1. 停止並移除現有容器...${NC}"
cd query-service
docker compose down -v
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 容器已停止並移除${NC}"
else
    echo -e "${YELLOW}⚠️ 無法使用 docker compose 停止容器，嘗試直接使用 docker 命令...${NC}"
    docker stop localstack-query-service eks-handler 2>/dev/null
    docker rm localstack-query-service eks-handler 2>/dev/null
fi

# 移除舊的 volume 目錄，以 sudo 執行以確保權限
echo -e "\n${YELLOW}2. 清理 volume 目錄...${NC}"
if [ -d "volume" ]; then
    echo -e "${YELLOW}⚠️ 嘗試清理 volume 目錄，可能需要管理員權限...${NC}"
    sudo rm -rf volume/* 2>/dev/null || rm -rf volume/* 2>/dev/null
    echo -e "${GREEN}✅ 已嘗試清理 volume 目錄${NC}"
else
    echo -e "${YELLOW}⚠️ volume 目錄不存在，將創建...${NC}"
    mkdir -p volume
fi

# 啟動服務
echo -e "\n${YELLOW}3. 啟動服務...${NC}"
docker compose up -d
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 服務已啟動${NC}"
else
    echo -e "${RED}❌ 無法啟動服務${NC}"
    echo -e "${YELLOW}請檢查 Docker Compose 配置和 Docker 服務狀態${NC}"
    echo -e "${GRAY}嘗試手動執行: cd query-service && docker compose up -d${NC}"
    exit 1
fi

# 等待 LocalStack 準備就緒
echo -e "\n${YELLOW}4. 等待 LocalStack 準備就緒...${NC}"
echo -e "${GRAY}這可能需要 30-60 秒...${NC}"

# 最多等待 60 秒
for i in {1..12}; do
    echo -e "${GRAY}等待中... $i/12${NC}"
    HEALTH_RESPONSE=$(curl -s "http://localhost:4566/_localstack/health")
    if [ $? -eq 0 ]; then
        # 檢查所有服務是否都是 available
        SERVICES_READY=$(echo "$HEALTH_RESPONSE" | jq -r '.services | to_entries | map(select(.value != "available")) | length')
        if [ "$SERVICES_READY" -eq 0 ]; then
            echo -e "${GREEN}✅ LocalStack 已準備就緒${NC}"
            break
        fi
    fi
    sleep 5

    # 如果是最後一次檢查，且仍未準備就緒
    if [ $i -eq 12 ]; then
        echo -e "${YELLOW}⚠️ LocalStack 可能未完全準備就緒，但將繼續執行...${NC}"
    fi
done

# 執行初始化腳本
echo -e "\n${YELLOW}5. 執行初始化腳本...${NC}"
docker exec -it localstack-query-service /etc/localstack/init/ready.d/setup.sh
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 初始化腳本執行完成${NC}"
else
    echo -e "${RED}❌ 初始化腳本執行失敗${NC}"
fi

# 修復 API Gateway
echo -e "\n${YELLOW}6. 修復 API Gateway...${NC}"
cd ..
./scripts/fix_api_gateway.sh

echo -e "\n${GREEN}✅ 服務重啟和初始化完成${NC}"
echo -e "${GREEN}======================================${NC}"
echo -e "${YELLOW}後續步驟:${NC}"
echo -e "${GRAY}1. 運行測試查詢:${NC}"
echo -e "${GRAY}   ./scripts/queries/test_query.sh${NC}"
echo -e "${GRAY}2. 運行快速測試:${NC}"
echo -e "${GRAY}   ./scripts/testing/quick_test.sh${NC}"
echo -e "${GRAY}3. 運行完整流程測試:${NC}"
echo -e "${GRAY}   ./scripts/testing/test_full_flow.sh${NC}"
echo -e "${GRAY}4. 驗證系統狀態:${NC}"
echo -e "${GRAY}   ./scripts/verification/verify_system.sh${NC}"
echo -e "${GRAY}5. 查看 API 文檔:${NC}"
echo -e "${GRAY}   http://localhost:8000/docs${NC}"
echo -e ""
