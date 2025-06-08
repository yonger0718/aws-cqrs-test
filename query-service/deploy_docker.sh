#!/bin/bash

# Docker 化 Lambda 部署管理腳本
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
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 顯示使用說明
show_usage() {
    echo -e "\n${CYAN}🐳 Docker 化 Lambda 部署管理腳本${NC}"
    echo -e "${GRAY}======================================${NC}\n"
    echo -e "${YELLOW}使用方法:${NC}"
    echo -e "  $0 [命令] [選項]"
    echo ""
    echo -e "${YELLOW}命令:${NC}"
    echo -e "  ${GREEN}build${NC}     - 構建 Lambda Docker 映像"
    echo -e "  ${GREEN}deploy${NC}    - 部署 Lambda 函數到 LocalStack"
    echo -e "  ${GREEN}start${NC}     - 啟動完整的開發環境 (LocalStack + ECS Handler)"
    echo -e "  ${GREEN}stop${NC}      - 停止所有服務"
    echo -e "  ${GREEN}restart${NC}   - 重啟服務並重新部署"
    echo -e "  ${GREEN}status${NC}    - 檢查服務狀態"
    echo -e "  ${GREEN}logs${NC}      - 查看服務日誌"
    echo -e "  ${GREEN}clean${NC}     - 清理所有容器和映像"
    echo -e "  ${GREEN}test${NC}      - 執行集成測試"
    echo ""
    echo -e "${YELLOW}選項:${NC}"
    echo -e "  ${GREEN}--no-cache${NC}  - 構建時不使用快取"
    echo -e "  ${GREEN}--verbose${NC}   - 顯示詳細輸出"
    echo ""
    echo -e "${YELLOW}範例:${NC}"
    echo -e "  $0 start          # 啟動完整環境"
    echo -e "  $0 build --no-cache  # 無快取構建"
    echo -e "  $0 deploy         # 部署 Lambda 函數"
    echo -e "  $0 test           # 執行測試"
    echo ""
}

# 檢查 Docker 環境
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker 未安裝或不可用${NC}"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        echo -e "${RED}❌ Docker 守護程序未運行${NC}"
        exit 1
    fi

    if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
        if ! command -v docker-compose &> /dev/null; then
            echo -e "${RED}❌ Docker Compose 未安裝或不可用${NC}"
            exit 1
        fi
    fi

    echo -e "${GREEN}✅ Docker 環境檢查通過${NC}"
}

# 構建 Lambda Docker 映像
build_lambda() {
    local no_cache=""
    if [[ "$*" == *"--no-cache"* ]]; then
        no_cache="--no-cache"
    fi

    echo -e "\n${YELLOW}📦 構建 Lambda Docker 映像...${NC}"

    cd "$SCRIPT_DIR/lambdas"

    docker compose -f docker-compose.lambda.yml build $no_cache

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Lambda Docker 映像構建成功${NC}"
    else
        echo -e "${RED}❌ Lambda Docker 映像構建失敗${NC}"
        exit 1
    fi
}

# 啟動開發環境
start_environment() {
    echo -e "\n${YELLOW}🚀 啟動開發環境...${NC}"

    cd "$SCRIPT_DIR"

    # 先停止現有服務
    docker compose down 2>/dev/null || true

    # 啟動 LocalStack 和 ECS Handler
    docker compose up -d localstack ecs-handler

    echo -e "${YELLOW}⏳ 等待服務啟動...${NC}"

    # 等待 LocalStack 健康檢查通過
    local max_wait=60
    local wait_time=0

    while [ $wait_time -lt $max_wait ]; do
        if docker compose exec localstack curl -f http://localhost:4566/_localstack/health &> /dev/null; then
            echo -e "${GREEN}✅ LocalStack 已啟動${NC}"
            break
        fi
        sleep 2
        wait_time=$((wait_time + 2))
        echo -n "."
    done

    if [ $wait_time -ge $max_wait ]; then
        echo -e "\n${RED}❌ LocalStack 啟動超時${NC}"
        exit 1
    fi

    # 等待 ECS Handler 啟動
    wait_time=0
    while [ $wait_time -lt $max_wait ]; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            echo -e "${GREEN}✅ ECS Handler 已啟動${NC}"
            break
        fi
        sleep 2
        wait_time=$((wait_time + 2))
    done

    if [ $wait_time -ge $max_wait ]; then
        echo -e "${YELLOW}⚠️  ECS Handler 可能尚未完全啟動，但可以繼續部署${NC}"
    fi
}

# 部署 Lambda 函數
deploy_lambda() {
    echo -e "\n${YELLOW}🚀 部署 Lambda 函數...${NC}"

    # 檢查 LocalStack 是否運行
    if ! curl -f http://localhost:4566/_localstack/health &> /dev/null; then
        echo -e "${RED}❌ LocalStack 未運行，請先執行 '$0 start'${NC}"
        exit 1
    fi

    cd "$SCRIPT_DIR/lambdas"

    # 執行 Docker 部署腳本
    if [ -f "deploy_docker_lambdas.sh" ]; then
        chmod +x deploy_docker_lambdas.sh
        ./deploy_docker_lambdas.sh
    else
        echo -e "${RED}❌ Docker 部署腳本不存在${NC}"
        exit 1
    fi
}

# 停止所有服務
stop_services() {
    echo -e "\n${YELLOW}🛑 停止所有服務...${NC}"

    cd "$SCRIPT_DIR"
    docker compose down

    echo -e "${GREEN}✅ 所有服務已停止${NC}"
}

# 檢查服務狀態
check_status() {
    echo -e "\n${CYAN}📊 服務狀態檢查${NC}"
    echo -e "${GRAY}==================${NC}\n"

    cd "$SCRIPT_DIR"

    # 檢查容器狀態
    echo -e "${YELLOW}Docker 容器狀態:${NC}"
    docker compose ps

    echo -e "\n${YELLOW}LocalStack 健康狀態:${NC}"
    if curl -f http://localhost:4566/_localstack/health 2>/dev/null; then
        echo -e "${GREEN}✅ LocalStack 運行正常${NC}"

        # 檢查 Lambda 函數
        echo -e "\n${YELLOW}Lambda 函數列表:${NC}"
        aws --endpoint-url=http://localhost:4566 lambda list-functions --query 'Functions[].FunctionName' --output table 2>/dev/null || echo "無法獲取 Lambda 函數列表"
    else
        echo -e "${RED}❌ LocalStack 未運行或不健康${NC}"
    fi

    echo -e "\n${YELLOW}ECS Handler 狀態:${NC}"
    if curl -f http://localhost:8000/health 2>/dev/null; then
        echo -e "${GREEN}✅ ECS Handler 運行正常${NC}"
    else
        echo -e "${RED}❌ ECS Handler 未運行${NC}"
    fi
}

# 查看日誌
show_logs() {
    echo -e "\n${YELLOW}📋 查看服務日誌${NC}"

    cd "$SCRIPT_DIR"
    docker compose logs -f --tail=100
}

# 清理資源
clean_resources() {
    echo -e "\n${YELLOW}🧹 清理 Docker 資源...${NC}"

    cd "$SCRIPT_DIR"

    # 停止並移除容器
    docker compose down --volumes --remove-orphans

    # 清理 Lambda Docker 映像
    echo -e "${YELLOW}清理 Lambda Docker 映像...${NC}"
    docker images --format "table {{.Repository}}:{{.Tag}}\t{{.ID}}" | grep "query-service.*lambda" | awk '{print $2}' | xargs -r docker rmi

    # 清理懸掛的映像
    docker image prune -f

    echo -e "${GREEN}✅ 清理完成${NC}"
}

# 執行集成測試
run_tests() {
    echo -e "\n${YELLOW}🧪 執行集成測試...${NC}"

    # 檢查服務是否運行
    if ! curl -f http://localhost:4566/_localstack/health &> /dev/null; then
        echo -e "${RED}❌ LocalStack 未運行，請先執行 '$0 start'${NC}"
        exit 1
    fi

    echo -e "${CYAN}測試 API Gateway 端點...${NC}"

    # 等待一下確保 Lambda 函數已部署
    sleep 5

    # 獲取 API Gateway ID
    local api_id=$(aws --endpoint-url=http://localhost:4566 apigateway get-rest-apis --query 'items[0].id' --output text 2>/dev/null)

    if [ "$api_id" != "null" ] && [ -n "$api_id" ]; then
        local base_url="http://localhost:4566/restapis/$api_id/dev/_user_request_"

        echo -e "${YELLOW}測試用戶查詢:${NC}"
        curl -s "$base_url/user?user_id=test_user_001" | jq . || echo "測試失敗"

        echo -e "\n${YELLOW}測試活動查詢:${NC}"
        curl -s "$base_url/marketing?marketing_id=campaign_2024_new_year" | jq . || echo "測試失敗"

        echo -e "\n${YELLOW}測試失敗查詢:${NC}"
        curl -s "$base_url/fail?transaction_id=tx_002" | jq . || echo "測試失敗"
    else
        echo -e "${RED}❌ 無法找到 API Gateway，請檢查部署${NC}"
    fi
}

# 主程序
main() {
    local command="$1"
    shift || true

    case "$command" in
        "build")
            check_docker
            build_lambda "$@"
            ;;
        "deploy")
            check_docker
            deploy_lambda
            ;;
        "start")
            check_docker
            start_environment
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            check_docker
            stop_services
            start_environment
            build_lambda "$@"
            deploy_lambda
            ;;
        "status")
            check_status
            ;;
        "logs")
            show_logs
            ;;
        "clean")
            clean_resources
            ;;
        "test")
            run_tests
            ;;
        "help"|"--help"|"-h"|"")
            show_usage
            ;;
        *)
            echo -e "${RED}❌ 未知命令: $command${NC}"
            show_usage
            exit 1
            ;;
    esac
}

# 執行主程序
main "$@"
