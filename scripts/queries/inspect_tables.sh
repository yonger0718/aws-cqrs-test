#!/bin/bash

# DynamoDB 表檢查工具包裝腳本
# 使用 Python 工具來避免 AWS CLI 相容性問題

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

echo -e "${CYAN}DynamoDB 表檢查工具${NC}"
echo -e "========================\n"

# 檢查 Poetry 是否可用
if ! command -v poetry &> /dev/null; then
    echo -e "${RED}❌ Poetry 未安裝或不在 PATH 中${NC}"
    exit 1
fi

# 檢查 Python 工具是否存在
PYTHON_TOOL="$SCRIPT_DIR/table_inspector.py"
if [ ! -f "$PYTHON_TOOL" ]; then
    echo -e "${RED}❌ Python 工具不存在: $PYTHON_TOOL${NC}"
    exit 1
fi

# 使用說明
show_usage() {
    echo -e "${YELLOW}使用方法:${NC}"
    echo -e "  $0                          # 檢查所有表 (每表顯示 10 筆記錄)"
    echo -e "  $0 --all                    # 檢查所有表 (每表顯示 10 筆記錄)"
    echo -e "  $0 --table <表名>           # 檢查特定表 (顯示 50 筆記錄)"
    echo -e "  $0 --table <表名> --limit 20 # 檢查特定表並指定記錄數"
    echo -e "  $0 --help                   # 顯示幫助"
    echo -e ""
    echo -e "${YELLOW}範例:${NC}"
    echo -e "  $0 --table command-records"
    echo -e "  $0 --table notification-records --limit 30"
    echo -e ""
}

# 檢查參數
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_usage
    exit 0
fi

# 解析參數
TABLE_NAME=""
LIMIT=""
ENDPOINT="http://localhost:4566"
REGION="ap-southeast-1"

while [[ $# -gt 0 ]]; do
    case $1 in
        --table|-t)
            TABLE_NAME="$2"
            shift 2
            ;;
        --limit|-l)
            LIMIT="$2"
            shift 2
            ;;
        --endpoint|-e)
            ENDPOINT="$2"
            shift 2
            ;;
        --region|-r)
            REGION="$2"
            shift 2
            ;;
        --all)
            # 檢查所有表 (預設行為)
            shift
            ;;
        *)
            echo -e "${RED}未知參數: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done

# 構建 Poetry 命令
POETRY_CMD="poetry run python $PYTHON_TOOL"

if [ ! -z "$TABLE_NAME" ]; then
    POETRY_CMD="$POETRY_CMD --table $TABLE_NAME"
fi

if [ ! -z "$LIMIT" ]; then
    POETRY_CMD="$POETRY_CMD --limit $LIMIT"
fi

POETRY_CMD="$POETRY_CMD --endpoint $ENDPOINT --region $REGION"

# 執行工具
echo -e "${YELLOW}正在啟動表檢查工具...${NC}"
echo -e "${CYAN}命令: $POETRY_CMD${NC}\n"

$POETRY_CMD

# 檢查執行結果
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ 表檢查完成${NC}"
else
    echo -e "\n${RED}❌ 表檢查失敗${NC}"
    exit 1
fi
