#!/bin/bash

# 開發環境啟動腳本
# 用於快速啟動 ECS 架構的本地開發環境

set -e

# 顏色定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 函數定義
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 檢查依賴
check_dependencies() {
    log_info "檢查必要依賴..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安裝"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安裝"
        exit 1
    fi

    log_success "依賴檢查完成"
}

# 清理舊容器
cleanup_containers() {
    log_info "清理舊容器..."

    cd query-service
    docker-compose down --remove-orphans || true

    log_success "容器清理完成"
}

# 啟動服務
start_services() {
    log_info "啟動 ECS 架構服務..."

    cd query-service

    # 構建並啟動服務
    docker-compose up --build -d

    log_info "等待服務啟動..."
    sleep 10

    # 檢查服務狀態
    if docker-compose ps | grep -q "Up"; then
        log_success "服務啟動成功"
    else
        log_error "服務啟動失敗"
        docker-compose logs
        exit 1
    fi
}

# 運行驗證測試
run_validation() {
    log_info "運行架構驗證測試..."

    cd query-service

    # 等待服務完全啟動
    sleep 5

    # 運行驗證腳本
    python test_ecs_architecture.py

    if [ $? -eq 0 ]; then
        log_success "架構驗證通過"
    else
        log_warning "架構驗證失敗，但服務已啟動"
    fi
}

# 顯示服務信息
show_service_info() {
    log_info "服務信息:"
    echo "=" * 50
    echo "🌐 ECS Handler: http://localhost:8000"
    echo "📋 Health Check: http://localhost:8000/health"
    echo "🔍 User Query: http://localhost:8000/query/user?user_id=test_user_001"
    echo "❌ Fail Query: http://localhost:8000/query/fail?transaction_id=tx_002"
    echo "🐳 LocalStack: http://localhost:4566"
    echo ""
    echo "📊 查看服務狀態: docker-compose ps"
    echo "📄 查看日誌: docker-compose logs -f"
    echo "🛑 停止服務: docker-compose down"
    echo ""
    log_success "ECS 架構開發環境準備就緒！"
}

# 主函數
main() {
    echo "🚀 啟動 ECS 架構開發環境..."
    echo ""

    check_dependencies
    cleanup_containers
    start_services
    run_validation
    show_service_info
}

# 執行主函數
main
