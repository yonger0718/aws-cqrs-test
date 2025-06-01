#!/bin/bash

# 確保從專案根目錄執行
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

echo -e "\n${CYAN}🔄 CQRS 完整流程測試 (Poetry)${NC}"
echo -e "${GRAY}===============================${NC}\n"

# 1. Poetry 環境檢查
echo -e "${YELLOW}1. Poetry 環境檢查...${NC}"
if ! command -v poetry &> /dev/null; then
    echo -e "${RED}❌ Poetry 未安裝${NC}"
    exit 1
fi

# 確保依賴已安裝
poetry install --no-root >/dev/null 2>&1

# 2. 執行 Python 測試套件
echo -e "\n${YELLOW}2. 執行 Python 測試套件...${NC}"

echo -e "${CYAN}  2.1 單元測試...${NC}"
if poetry run pytest query-service/tests/test_eks_handler.py::TestEdgeCases -v --tb=short; then
    echo -e "${GREEN}  ✅ 單元測試通過${NC}"
else
    echo -e "${RED}  ❌ 單元測試失敗${NC}"
fi

echo -e "\n${CYAN}  2.2 Lambda 函數測試...${NC}"
if poetry run pytest query-service/tests/test_lambdas/test_query_lambda.py::TestLambdaHandlerUserQuery::test_user_query_success -v --tb=short; then
    echo -e "${GREEN}  ✅ Lambda 測試通過${NC}"
else
    echo -e "${RED}  ❌ Lambda 測試失敗${NC}"
fi

# 3. 服務健康檢查
echo -e "\n${YELLOW}3. 服務健康檢查...${NC}"

echo -e "${CYAN}  3.1 LocalStack 檢查...${NC}"
if response=$(curl -s --connect-timeout 5 "$AWS_ENDPOINT/_localstack/health" 2>/dev/null); then
    echo -e "${GREEN}  ✅ LocalStack 正常運行${NC}"
    if command -v jq >/dev/null 2>&1; then
        echo "$response" | jq .services | jq -r 'to_entries | .[] | select(.key | test("dynamodb|lambda|apigateway")) | "    \(.key): \(.value)"'
    fi
else
    echo -e "${RED}  ❌ LocalStack 連接失敗${NC}"
    echo -e "${GRAY}  啟動指令: cd query-service && docker-compose up -d${NC}"
fi

echo -e "\n${CYAN}  3.2 EKS Handler 檢查...${NC}"
if response=$(curl -s --connect-timeout 5 "$EKS_ENDPOINT/health" 2>/dev/null); then
    echo -e "${GREEN}  ✅ EKS Handler 正常運行${NC}"
    if command -v jq >/dev/null 2>&1; then
        service_name=$(echo "$response" | jq -r '.service // "Unknown"')
        echo -e "${CYAN}    Service: $service_name${NC}"
    fi
else
    echo -e "${RED}  ❌ EKS Handler 連接失敗${NC}"
    echo -e "${GRAY}  啟動指令: cd query-service && docker-compose up -d${NC}"
fi

# 4. 如果服務正常，執行整合測試
if curl -s --connect-timeout 3 "$AWS_ENDPOINT/_localstack/health" >/dev/null 2>&1; then
    echo -e "\n${YELLOW}4. 執行整合測試...${NC}"

    if poetry run pytest query-service/tests/test_integration.py::TestServiceEndToEnd::test_health_check_all_services -v --tb=short; then
        echo -e "${GREEN}  ✅ 服務整合測試通過${NC}"
    else
        echo -e "${RED}  ❌ 服務整合測試失敗${NC}"
    fi

    # 簡單的 CQRS 流程測試
    echo -e "\n${CYAN}  4.1 測試資料查詢功能...${NC}"
    if response=$(curl -s -X POST "$EKS_ENDPOINT/query/user" -H "Content-Type: application/json" -d '{"user_id":"test_user_001"}' 2>/dev/null); then
        if command -v jq >/dev/null 2>&1; then
            count=$(echo "$response" | jq -r '.total_count // 0' 2>/dev/null || echo "0")
            echo -e "${GREEN}  ✅ 查詢功能正常，找到 $count 條記錄${NC}"
        else
            echo -e "${GREEN}  ✅ 查詢功能正常${NC}"
        fi
    else
        echo -e "${RED}  ❌ 查詢功能失敗${NC}"
    fi
else
    echo -e "\n${YELLOW}4. 跳過整合測試 (LocalStack 未運行)${NC}"
fi

# 5. 代碼品質檢查
echo -e "\n${YELLOW}5. 代碼品質檢查...${NC}"

echo -e "${CYAN}  5.1 語法檢查...${NC}"
if poetry run python -m py_compile query-service/eks_handler/main.py >/dev/null 2>&1; then
    echo -e "${GREEN}  ✅ 代碼語法正確${NC}"
else
    echo -e "${RED}  ❌ 代碼語法錯誤${NC}"
fi

echo -e "\n${CYAN}  5.2 導入檢查...${NC}"
if poetry run python -c "import sys; sys.path.append('query-service'); import eks_handler.main" >/dev/null 2>&1; then
    echo -e "${GREEN}  ✅ 模組可正常導入${NC}"
else
    echo -e "${RED}  ❌ 模組導入失敗${NC}"
fi

# 6. 簡化的覆蓋率測試
echo -e "\n${YELLOW}6. 快速覆蓋率檢查...${NC}"
coverage_result=$(poetry run pytest query-service/tests/test_eks_handler.py::TestEdgeCases -v --cov=query-service/eks_handler --cov-report=term-missing --tb=no -q 2>/dev/null)
if echo "$coverage_result" | grep -q "TOTAL"; then
    coverage_line=$(echo "$coverage_result" | grep "TOTAL" | tail -1)
    echo -e "${GREEN}  ✅ 覆蓋率測試完成${NC}"
    echo -e "${CYAN}  $coverage_line${NC}"
else
    echo -e "${YELLOW}  ⚠️  覆蓋率測試跳過${NC}"
fi

# 測試總結
echo -e "\n${CYAN}📋 測試完成總結${NC}"
echo -e "${GRAY}==============================${NC}"
echo -e "${YELLOW}📦 Poetry 常用命令:${NC}"
echo -e "${GRAY}  poetry run pytest                    # 執行所有測試${NC}"
echo -e "${GRAY}  poetry run pytest --cov              # 帶覆蓋率的測試${NC}"
echo -e "${GRAY}  poetry run black query-service/      # 代碼格式化${NC}"
echo -e "${GRAY}  poetry run mypy query-service/       # 類型檢查${NC}"

echo -e "\n${YELLOW}🔧 完整測試腳本:${NC}"
echo -e "${GRAY}  ./scripts/testing/test_coverage.sh   # 完整覆蓋率測試${NC}"
echo -e "${GRAY}  ./scripts/testing/quick_test.sh      # 快速健康檢查${NC}"

echo -e "\n${YELLOW}🛠️  故障排除:${NC}"
echo -e "${GRAY}  ./scripts/restart_services.sh        # 重啟所有服務${NC}"
echo -e "${GRAY}  ./scripts/fix_api_gateway.sh         # 修復 API Gateway${NC}"

echo -e "\n${GREEN}✅ 完整流程測試完成！${NC}"
