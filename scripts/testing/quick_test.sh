#!/bin/bash

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Quick LocalStack Test${NC}"
echo -e "${GREEN}====================${NC}"

AWS_ENDPOINT="http://localhost:4566"
EKS_ENDPOINT="http://localhost:8000"

# Test 1: EKS Handler Health Check
echo -e "\n${YELLOW}1. Testing EKS Handler...${NC}"
if response=$(curl -s $EKS_ENDPOINT); then
    echo -e "${GREEN}✅ EKS Handler OK${NC}"
    echo -e "${CYAN}$response${NC}"
else
    echo -e "${RED}❌ EKS Handler Failed: Could not connect to server${NC}"
fi

# Test 2: LocalStack Health
echo -e "\n${YELLOW}2. Testing LocalStack...${NC}"
if response=$(curl -s "$AWS_ENDPOINT/health"); then
    echo -e "${GREEN}✅ LocalStack OK${NC}"
    echo "$response" | jq .services | jq -r 'to_entries | .[] | "\(.key) : \(.value)"' | while read line; do
        echo -e "${CYAN}  $line${NC}"
    done
else
    echo -e "${RED}❌ LocalStack Failed: Could not connect to server${NC}"
fi

# Test 3: DynamoDB Tables
echo -e "\n${YELLOW}3. Testing DynamoDB...${NC}"
HEADERS=(-H "Content-Type: application/x-amz-json-1.0" -H "X-Amz-Target: DynamoDB_20120810.ListTables")
if response=$(curl -s "$AWS_ENDPOINT" -X POST "${HEADERS[@]}" -d '{}'); then
    echo -e "${GREEN}✅ DynamoDB OK${NC}"
    echo -e "${CYAN}Tables:${NC}"
    echo "$response" | jq -r '.TableNames[]' | while read table; do
        echo -e "${CYAN}  - $table${NC}"
    done
else
    echo -e "${RED}❌ DynamoDB Failed: Could not connect to server${NC}"
fi

# Test 4: Query API
echo -e "\n${YELLOW}4. Testing Query API...${NC}"
if response=$(curl -s "$EKS_ENDPOINT/query/user" -X POST -H "Content-Type: application/json" -d '{"user_id":"test_user_001"}'); then
    echo -e "${GREEN}✅ Query API OK${NC}"
    count=$(echo "$response" | jq -r '.count // 0')
    echo -e "${CYAN}Records count: $count${NC}"
else
    echo -e "${RED}❌ Query API Failed: Could not connect to server${NC}"
fi

echo -e "\n${GREEN}✅ Quick test completed!${NC}"
echo "Press Enter to exit"
read
