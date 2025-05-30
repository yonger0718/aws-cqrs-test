#!/bin/bash

# 測試覆蓋率報告生成腳本
# 執行所有測試並生成詳細的覆蓋率報告

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

echo -e "\n${CYAN}🧪 測試覆蓋率報告生成器${NC}"
echo -e "${GRAY}============================${NC}\n"

# 設置工作目錄
cd query-service || exit 1

echo -e "${YELLOW}1. 清理舊的覆蓋率數據...${NC}"
rm -f .coverage coverage.xml
rm -rf htmlcov/

echo -e "${YELLOW}2. 安裝測試依賴...${NC}"
pip install -r requirements.txt >/dev/null 2>&1
pip install -r tests/requirements-test.txt >/dev/null 2>&1

echo -e "${YELLOW}3. 執行單元測試 (含覆蓋率)...${NC}"
pytest tests/test_eks_handler.py -v \
    --cov=eks-handler \
    --cov-report=xml \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-config=pytest.ini

UNIT_EXIT_CODE=$?

echo -e "\n${YELLOW}4. 執行整合測試 (附加覆蓋率)...${NC}"
# 檢查是否有 LocalStack 運行
if curl -s http://localhost:4566/health >/dev/null 2>&1; then
    pytest tests/test_integration.py -v \
        --cov=eks-handler \
        --cov-append \
        --cov-report=xml \
        --cov-report=html \
        --cov-report=term-missing \
        --cov-config=pytest.ini
    INTEGRATION_EXIT_CODE=$?
else
    echo -e "${RED}⚠️  LocalStack 未運行，跳過整合測試${NC}"
    INTEGRATION_EXIT_CODE=0
fi

echo -e "\n${YELLOW}5. 生成覆蓋率報告...${NC}"
if [ -f coverage.xml ]; then
    echo -e "${GREEN}✅ 覆蓋率 XML 報告已生成: coverage.xml${NC}"
fi

if [ -d htmlcov ]; then
    echo -e "${GREEN}✅ 覆蓋率 HTML 報告已生成: htmlcov/index.html${NC}"

    # 嘗試打開瀏覽器 (可選)
    if command -v xdg-open >/dev/null 2>&1; then
        echo -e "${CYAN}💡 使用 'xdg-open htmlcov/index.html' 查看詳細報告${NC}"
    elif command -v open >/dev/null 2>&1; then
        echo -e "${CYAN}💡 使用 'open htmlcov/index.html' 查看詳細報告${NC}"
    fi
fi

echo -e "\n${YELLOW}6. 覆蓋率總結:${NC}"
coverage report --show-missing

# 設置覆蓋率閾值檢查
echo -e "\n${YELLOW}7. 覆蓋率品質檢查...${NC}"
COVERAGE_PERCENTAGE=$(coverage report --format=total)
THRESHOLD=70

if [ "$COVERAGE_PERCENTAGE" -ge "$THRESHOLD" ]; then
    echo -e "${GREEN}✅ 覆蓋率 ($COVERAGE_PERCENTAGE%) 符合要求 (>= $THRESHOLD%)${NC}"
    COVERAGE_EXIT_CODE=0
else
    echo -e "${RED}❌ 覆蓋率 ($COVERAGE_PERCENTAGE%) 低於要求 (>= $THRESHOLD%)${NC}"
    COVERAGE_EXIT_CODE=1
fi

echo -e "\n${CYAN}📊 測試結果總覽:${NC}"
echo -e "單元測試:     $([ $UNIT_EXIT_CODE -eq 0 ] && echo -e "${GREEN}✅ 通過${NC}" || echo -e "${RED}❌ 失敗${NC}")"
echo -e "整合測試:     $([ $INTEGRATION_EXIT_CODE -eq 0 ] && echo -e "${GREEN}✅ 通過${NC}" || echo -e "${RED}❌ 失敗${NC}")"
echo -e "覆蓋率要求:   $([ $COVERAGE_EXIT_CODE -eq 0 ] && echo -e "${GREEN}✅ 達標${NC}" || echo -e "${RED}❌ 不達標${NC}")"
echo -e "覆蓋率:       ${COVERAGE_PERCENTAGE}%"

# 總體退出碼
OVERALL_EXIT_CODE=$((UNIT_EXIT_CODE + INTEGRATION_EXIT_CODE + COVERAGE_EXIT_CODE))

if [ $OVERALL_EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}🎉 所有測試通過，覆蓋率達標！${NC}"
else
    echo -e "\n${RED}⚠️  部分測試失敗或覆蓋率不達標${NC}"
fi

exit $OVERALL_EXIT_CODE
