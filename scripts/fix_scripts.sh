#!/bin/bash

# 腳本修復工具
# 統一修復項目中所有腳本的常見問題

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# 確保從專案根目錄執行
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "\n${CYAN}🔧 腳本修復工具${NC}"
echo -e "${GRAY}===============${NC}\n"

echo -e "${YELLOW}1. 檢查腳本權限...${NC}"
# 設置所有腳本的執行權限
find scripts/ -name "*.sh" -type f -exec chmod +x {} \;
echo -e "${GREEN}✅ 所有腳本權限已設置${NC}"

echo -e "\n${YELLOW}2. 檢查必要依賴...${NC}"

# 檢查必要工具
MISSING_TOOLS=()

if ! command -v curl &> /dev/null; then
    MISSING_TOOLS+=(curl)
fi

if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}⚠️  jq 未安裝，部分腳本功能會受限${NC}"
    echo -e "${GRAY}   安裝: sudo apt-get install jq (Ubuntu/Debian)${NC}"
    echo -e "${GRAY}   或 brew install jq (macOS)${NC}"
fi

if ! command -v aws &> /dev/null; then
    MISSING_TOOLS+=(awscli)
fi

if ! command -v poetry &> /dev/null; then
    echo -e "${YELLOW}⚠️  Poetry 未安裝${NC}"
    echo -e "${GRAY}   安裝: curl -sSL https://install.python-poetry.org | python3 -${NC}"
fi

if [ ${#MISSING_TOOLS[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ 所有必要工具已安裝${NC}"
else
    echo -e "${RED}❌ 缺少工具: ${MISSING_TOOLS[*]}${NC}"
fi

echo -e "\n${YELLOW}3. 檢查環境變數設置...${NC}"
if [ -f "scripts/setup_env.sh" ]; then
    source scripts/setup_env.sh > /dev/null 2>&1
    echo -e "${GREEN}✅ 環境變數設置腳本已載入${NC}"
else
    echo -e "${RED}❌ 環境變數設置腳本不存在${NC}"
fi

echo -e "\n${YELLOW}4. 檢查項目結構...${NC}"

# 檢查關鍵目錄
REQUIRED_DIRS=("query-service" "query-service/eks_handler" "query-service/tests" "scripts/testing" "scripts/queries")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✅ $dir${NC}"
    else
        echo -e "${RED}❌ $dir 目錄不存在${NC}"
    fi
done

echo -e "\n${YELLOW}5. 測試腳本功能...${NC}"

# 測試環境設置腳本
echo -e "${CYAN}  5.1 測試環境設置腳本...${NC}"
if bash scripts/setup_env.sh > /dev/null 2>&1; then
    echo -e "${GREEN}  ✅ setup_env.sh 正常${NC}"
else
    echo -e "${RED}  ❌ setup_env.sh 有問題${NC}"
fi

# 測試查詢腳本
echo -e "${CYAN}  5.2 測試查詢腳本...${NC}"
if [ -f "scripts/queries/simple_query.sh" ]; then
    if bash -n scripts/queries/simple_query.sh; then
        echo -e "${GREEN}  ✅ simple_query.sh 語法正確${NC}"
    else
        echo -e "${RED}  ❌ simple_query.sh 語法錯誤${NC}"
    fi
fi

# 測試測試腳本
echo -e "${CYAN}  5.3 測試測試腳本...${NC}"
for test_script in scripts/testing/*.sh; do
    if [ -f "$test_script" ]; then
        script_name=$(basename "$test_script")
        if bash -n "$test_script"; then
            echo -e "${GREEN}  ✅ $script_name 語法正確${NC}"
        else
            echo -e "${RED}  ❌ $script_name 語法錯誤${NC}"
        fi
    fi
done

echo -e "\n${YELLOW}6. 創建腳本使用指南...${NC}"
cat > scripts/README_USAGE.md << 'EOF'
# 腳本使用指南

## 環境設置
```bash
# 設置環境變數
source scripts/setup_env.sh
```

## 測試腳本
```bash
# 快速測試
./scripts/testing/quick_test.sh

# 完整測試
./scripts/testing/run-all-tests.sh

# 覆蓋率測試
./scripts/testing/test_coverage.sh

# 完整流程測試
./scripts/testing/test_full_flow.sh
```

## 查詢腳本
```bash
# 簡單查詢工具
./scripts/queries/simple_query.sh

# 詳細查詢測試
./scripts/queries/test_query.sh
```

## 部署腳本
```bash
# 部署 API Gateway 代理
./scripts/deploy_api_gateway_proxy.sh

# 修復 API Gateway
./scripts/fix_api_gateway.sh

# 重啟服務
./scripts/restart_services.sh
```

## 故障排除

### 權限問題
```bash
chmod +x scripts/**/*.sh
```

### 環境問題
```bash
# 確保 Poetry 安裝
curl -sSL https://install.python-poetry.org | python3 -

# 安裝依賴
poetry install
```

### 服務問題
```bash
# 重啟所有服務
./scripts/restart_services.sh
```
EOF

echo -e "${GREEN}✅ 使用指南已創建: scripts/README_USAGE.md${NC}"

echo -e "\n${YELLOW}7. 修復建議...${NC}"

# 檢查常見問題並提供修復建議
if ! curl -s http://localhost:4566/health > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  LocalStack 未運行${NC}"
    echo -e "${GRAY}   修復: cd query-service && docker-compose up -d localstack${NC}"
fi

if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  EKS Handler 未運行${NC}"
    echo -e "${GRAY}   修復: cd query-service && docker-compose up -d${NC}"
fi

echo -e "\n${CYAN}📋 修復完成總結${NC}"
echo -e "${GRAY}==================${NC}"
echo -e "${GREEN}✅ 腳本權限已設置${NC}"
echo -e "${GREEN}✅ 語法檢查完成${NC}"
echo -e "${GREEN}✅ 使用指南已創建${NC}"

echo -e "\n${YELLOW}💡 下一步建議:${NC}"
echo -e "${GRAY}1. 執行 source scripts/setup_env.sh${NC}"
echo -e "${GRAY}2. 啟動服務 cd query-service && docker-compose up -d${NC}"
echo -e "${GRAY}3. 運行快速測試 ./scripts/testing/quick_test.sh${NC}"

echo -e "\n${GREEN}🎉 腳本修復完成！${NC}"
