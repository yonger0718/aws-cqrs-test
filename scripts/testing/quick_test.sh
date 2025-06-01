#!/bin/bash

# 載入環境變量設置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

# 確保 Poetry 在 PATH 中
export PATH="$HOME/.local/bin:$PATH"

# ANSI 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# 端點設定
AWS_ENDPOINT="http://localhost:4566"
EKS_ENDPOINT="http://localhost:8000"

echo -e "\n${CYAN}🚀 CQRS 系統快速測試 (Poetry)${NC}"
echo -e "${GRAY}==============================${NC}\n"

# Test 0: Poetry 環境檢查
echo -e "${YELLOW}0. Poetry 環境檢查...${NC}"
if command -v poetry &> /dev/null; then
    echo -e "${GREEN}✅ Poetry 已安裝${NC}"
    poetry_version=$(poetry --version)
    echo -e "${CYAN}  $poetry_version${NC}"

    if poetry env info >/dev/null 2>&1; then
        echo -e "${GREEN}✅ 虛擬環境已建立${NC}"
        venv_path=$(poetry env info --path)
        echo -e "${CYAN}  $venv_path${NC}"
    else
        echo -e "${YELLOW}⚠️  虛擬環境未建立，執行 poetry install...${NC}"
        poetry install --no-root
    fi
else
    echo -e "${RED}❌ Poetry 未安裝${NC}"
    echo -e "${YELLOW}💡 安裝指令: curl -sSL https://install.python-poetry.org | python3 -${NC}"
fi

# Test 1: Python 快速測試
echo -e "\n${YELLOW}1. Python 測試 (基礎功能)...${NC}"
if command -v poetry &> /dev/null; then
    test_count=$(poetry run pytest query-service/tests/test_eks_handler.py::TestEdgeCases::test_invalid_endpoint -v --tb=no -q | grep -c "PASSED" || echo "0")
    if [ "$test_count" -gt 0 ]; then
        echo -e "${GREEN}✅ Python 測試基礎功能正常${NC}"
        echo -e "${CYAN}  通過 $test_count 個基礎測試${NC}"
    else
        echo -e "${RED}❌ Python 測試失敗${NC}"
    fi
else
    echo -e "${RED}❌ 跳過 Python 測試 (Poetry 不可用)${NC}"
fi

# Test 2: EKS Handler Health Check
echo -e "\n${YELLOW}2. EKS Handler 健康檢查...${NC}"
if response=$(curl -s --connect-timeout 5 $EKS_ENDPOINT 2>/dev/null); then
    echo -e "${GREEN}✅ EKS Handler 正常${NC}"
    service_name=$(echo "$response" | jq -r '.service // "Unknown"' 2>/dev/null || echo "Response received")
    echo -e "${CYAN}  Service: $service_name${NC}"
else
    echo -e "${RED}❌ EKS Handler 無法連接${NC}"
    echo -e "${GRAY}  確保 Docker Compose 已啟動: docker-compose up -d${NC}"
fi

# Test 3: LocalStack Health
echo -e "\n${YELLOW}3. LocalStack 健康檢查...${NC}"
if response=$(curl -s --connect-timeout 5 "$AWS_ENDPOINT/_localstack/health" 2>/dev/null); then
    echo -e "${GREEN}✅ LocalStack 正常${NC}"
    if command -v jq >/dev/null 2>&1; then
        echo "$response" | jq .services | jq -r 'to_entries | .[] | "\(.key) : \(.value)"' | while read line; do
            echo -e "${CYAN}  $line${NC}"
        done
    else
        echo -e "${CYAN}  服務狀態: $(echo "$response" | grep -o '"services":{[^}]*}' | wc -c) bytes${NC}"
    fi
else
    echo -e "${RED}❌ LocalStack 無法連接${NC}"
    echo -e "${GRAY}  確保 LocalStack 已啟動: cd query-service && docker-compose up -d${NC}"
fi

# Test 4: DynamoDB Tables
echo -e "\n${YELLOW}4. DynamoDB 表檢查...${NC}"
HEADERS=(-H "Content-Type: application/x-amz-json-1.0" -H "X-Amz-Target: DynamoDB_20120810.ListTables")
if response=$(curl -s --connect-timeout 5 "$AWS_ENDPOINT" -X POST "${HEADERS[@]}" -d '{}' 2>/dev/null); then
    echo -e "${GREEN}✅ DynamoDB 正常${NC}"
    if command -v jq >/dev/null 2>&1; then
        table_count=$(echo "$response" | jq -r '.TableNames | length' 2>/dev/null || echo "0")
        echo -e "${CYAN}  發現 $table_count 個表${NC}"
        echo "$response" | jq -r '.TableNames[]' 2>/dev/null | while read table; do
            echo -e "${CYAN}  - $table${NC}"
        done
    else
        echo -e "${CYAN}  Tables: $(echo "$response" | grep -o 'TableNames' | wc -l) found${NC}"
    fi
else
    echo -e "${RED}❌ DynamoDB 無法連接${NC}"
fi

# Test 5: 代碼品質檢查 (快速)
echo -e "\n${YELLOW}5. 代碼品質快速檢查...${NC}"
if command -v poetry &> /dev/null; then
    # 檢查主要文件語法
    if poetry run python -m py_compile query-service/eks_handler/main.py >/dev/null 2>&1; then
        echo -e "${GREEN}✅ 代碼語法正確${NC}"
    else
        echo -e "${RED}❌ 代碼語法錯誤${NC}"
    fi

    # 檢查基本類型
    if poetry run python -c "import query-service.eks_handler.main" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ 模組可正常導入${NC}"
    else
        echo -e "${RED}❌ 模組導入失敗${NC}"
    fi
else
    echo -e "${RED}❌ 跳過代碼品質檢查 (Poetry 不可用)${NC}"
fi

echo -e "\n${CYAN}📋 快速測試總結${NC}"
echo -e "${GRAY}================================${NC}"
echo -e "${YELLOW}📦 常用 Poetry 命令:${NC}"
echo -e "${GRAY}  poetry install          # 安裝依賴${NC}"
echo -e "${GRAY}  poetry run pytest       # 執行測試${NC}"
echo -e "${GRAY}  poetry run black .      # 代碼格式化${NC}"
echo -e "${GRAY}  poetry shell            # 進入虛擬環境${NC}"

echo -e "\n${YELLOW}🔧 故障排除:${NC}"
echo -e "${GRAY}  ./scripts/restart_services.sh     # 重啟服務${NC}"
echo -e "${GRAY}  ./scripts/fix_api_gateway.sh      # 修復 API Gateway${NC}"
echo -e "${GRAY}  ./scripts/testing/test_coverage.sh # 完整測試${NC}"

echo -e "\n${GREEN}✅ 快速測試完成！${NC}"
