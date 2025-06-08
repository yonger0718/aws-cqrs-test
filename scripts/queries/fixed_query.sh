#!/bin/bash

# 修復版查詢工具包裝腳本
# 使用 Python boto3 替代有問題的 AWS CLI

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 獲取腳本目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 切換到專案根目錄
cd "$PROJECT_ROOT"

echo -e "${CYAN}修復版查詢工具${NC}"
echo -e "================\n"

# 檢查 Poetry 是否可用
if ! command -v poetry &> /dev/null; then
    echo -e "${RED}❌ Poetry 未安裝或不在 PATH 中${NC}"
    exit 1
fi

# 檢查 Python 工具是否存在
PYTHON_TOOL="$SCRIPT_DIR/fixed_query.py"
if [ ! -f "$PYTHON_TOOL" ]; then
    echo -e "${RED}❌ Python 工具不存在: $PYTHON_TOOL${NC}"
    exit 1
fi

# 使用說明
show_usage() {
    echo -e "${YELLOW}使用方法:${NC}"
    echo -e "  $0                     # 執行所有檢查"
    echo -e "  $0 --mode services     # 只檢查服務狀態"
    echo -e "  $0 --mode dynamodb     # 只檢查 DynamoDB 表"
    echo -e "  $0 --mode api          # 只測試 API"
    echo -e "  $0 --help              # 顯示幫助"
    echo -e ""
    echo -e "${YELLOW}檢查模式:${NC}"
    echo -e "  all        - 執行所有檢查 (預設)"
    echo -e "  services   - 檢查 LocalStack 和 EKS Handler 狀態"
    echo -e "  dynamodb   - 檢查 DynamoDB 表和統計"
    echo -e "  api        - 測試查詢 API 端點"
    echo -e ""
}

# 檢查參數
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_usage
    exit 0
fi

# 解析參數
MODE="all"
AWS_ENDPOINT="http://localhost:4566"
EKS_ENDPOINT="http://localhost:8000"
REGION="ap-southeast-1"

while [[ $# -gt 0 ]]; do
    case $1 in
        --mode|-m)
            MODE="$2"
            shift 2
            ;;
        --aws-endpoint)
            AWS_ENDPOINT="$2"
            shift 2
            ;;
        --eks-endpoint)
            EKS_ENDPOINT="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}未知參數: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done

# 驗證模式
case $MODE in
    all|services|dynamodb|api)
        ;;
    *)
        echo -e "${RED}無效的檢查模式: $MODE${NC}"
        show_usage
        exit 1
        ;;
esac

# 構建 Poetry 命令
POETRY_CMD="poetry run python $PYTHON_TOOL --mode $MODE"
POETRY_CMD="$POETRY_CMD --aws-endpoint $AWS_ENDPOINT"
POETRY_CMD="$POETRY_CMD --eks-endpoint $EKS_ENDPOINT"
POETRY_CMD="$POETRY_CMD --region $REGION"

# 執行工具
echo -e "${YELLOW}正在啟動修復版查詢工具...${NC}"
echo -e "${CYAN}檢查模式: $MODE${NC}"
echo -e "${CYAN}AWS 端點: $AWS_ENDPOINT${NC}"
echo -e "${CYAN}EKS 端點: $EKS_ENDPOINT${NC}\n"

$POETRY_CMD

# 檢查執行結果
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ 查詢檢查完成${NC}"
else
    echo -e "\n${RED}❌ 查詢檢查失敗${NC}"
    exit 1
fi
