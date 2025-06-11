# AWS CloudShell 手動資源查找指南

## 📋 概述

如果自動發現腳本無法找到您的資源，請使用以下命令手動查找並設置環境變數。

## 🔍 查找 HTTP API Gateway (v2)

### 列出所有 HTTP API Gateway

```bash
# 查找 HTTP API Gateway
aws apigatewayv2 get-apis

# 只顯示關鍵信息
aws apigatewayv2 get-apis --query 'Items[*].{Name:Name,ApiId:ApiId,ProtocolType:ProtocolType}' --output table

# 查找特定名稱的 API
aws apigatewayv2 get-apis --query 'Items[?contains(Name, `query`)]'
```

### 查看 HTTP API Gateway 詳細信息

```bash
# 替換 YOUR_API_ID 為實際的 API ID
HTTP_API_ID="YOUR_API_ID"

# 查看 API 詳情
aws apigatewayv2 get-api --api-id $HTTP_API_ID

# 查看路由信息
aws apigatewayv2 get-routes --api-id $HTTP_API_ID

# 查看部署階段
aws apigatewayv2 get-stages --api-id $HTTP_API_ID
```

### 測試 HTTP API Gateway

```bash
# 設置您的 HTTP API Gateway ID
export HTTP_API_GATEWAY_ID="your-actual-api-id"

# 測試端點 (注意：HTTP API Gateway 的 URL 格式不同)
curl "https://${HTTP_API_GATEWAY_ID}.execute-api.ap-southeast-1.amazonaws.com/health"
```

## 🔍 查找 REST API Gateway (v1) - 備用

### 列出所有 REST API Gateway

```bash
# 查找 REST API Gateway
aws apigateway get-rest-apis

# 只顯示關鍵信息
aws apigateway get-rest-apis --query 'items[*].{Name:name,Id:id}' --output table

# 查找特定名稱的 API
aws apigateway get-rest-apis --query 'items[?contains(name, `query`)]'
```

### 查看 REST API Gateway 詳細信息

```bash
# 替換 YOUR_API_ID 為實際的 API ID
REST_API_ID="YOUR_API_ID"

# 查看 API 詳情
aws apigateway get-rest-api --rest-api-id $REST_API_ID

# 查看資源結構
aws apigateway get-resources --rest-api-id $REST_API_ID

# 查看部署信息
aws apigateway get-deployments --rest-api-id $REST_API_ID
```

## 🔍 查找 ECS 服務和集群

### 列出 ECS 集群

```bash
# 列出所有 ECS 集群
aws ecs list-clusters

# 查看集群詳細信息
aws ecs describe-clusters --clusters cluster-name

# 查找包含特定關鍵字的集群
aws ecs list-clusters --query 'clusterArns[?contains(@, `query`) || contains(@, `service`)]'
```

### 查找 ECS 服務

```bash
# 替換 YOUR_CLUSTER_NAME 為實際的集群名稱
CLUSTER_NAME="YOUR_CLUSTER_NAME"

# 列出集群中的服務
aws ecs list-services --cluster $CLUSTER_NAME

# 查看服務詳細信息
aws ecs describe-services --cluster $CLUSTER_NAME --services service-name

# 查看任務定義
aws ecs list-task-definitions

# 查看特定任務定義詳情
aws ecs describe-task-definition --task-definition task-definition-name
```

### 查找 ECS 任務和網路信息

```bash
# 列出運行中的任務
aws ecs list-tasks --cluster $CLUSTER_NAME

# 查看任務詳情（包括 IP 地址）
aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks task-arn

# 獲取任務的公網 IP（如果有）
aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks task-arn \
  --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
  --output text | xargs -I {} aws ec2 describe-network-interfaces \
  --network-interface-ids {} \
  --query 'NetworkInterfaces[0].Association.PublicIp' \
  --output text
```

## 🔍 查找 Load Balancer (如果使用)

### 列出 Application Load Balancer

```bash
# 列出所有 ALB
aws elbv2 describe-load-balancers

# 查找特定名稱的 ALB
aws elbv2 describe-load-balancers \
  --query 'LoadBalancers[?contains(LoadBalancerName, `query`)]'

# 獲取 ALB 的 DNS 名稱
aws elbv2 describe-load-balancers \
  --names your-alb-name \
  --query 'LoadBalancers[0].DNSName' \
  --output text
```

### 查看 Target Group 和健康狀態

```bash
# 列出 Target Groups
aws elbv2 describe-target-groups

# 查看 Target Group 的健康狀態
aws elbv2 describe-target-health --target-group-arn your-target-group-arn
```

## 🔍 查找 DynamoDB 表

### 列出 DynamoDB 表

```bash
# 列出所有表
aws dynamodb list-tables

# 查找特定名稱的表
aws dynamodb list-tables --query 'TableNames[?contains(@, `command`) || contains(@, `notification`) || contains(@, `Event`)]'

# 查看表詳細信息
aws dynamodb describe-table --table-name your-table-name

# 檢查表的 Stream 狀態
aws dynamodb describe-table --table-name your-table-name \
  --query 'Table.StreamSpecification'
```

### 查看表中的數據

```bash
# 掃描表（小心使用，大表會消耗很多資源）
aws dynamodb scan --table-name your-table-name --max-items 5

# 查詢特定項目
aws dynamodb get-item --table-name your-table-name \
  --key '{"id":{"S":"some-id"}}'

# 統計表中項目數量
aws dynamodb scan --table-name your-table-name \
  --select COUNT \
  --query 'Count'
```

## 🔍 查找 Lambda 函數

### 列出 Lambda 函數

```bash
# 列出所有 Lambda 函數
aws lambda list-functions

# 查找特定名稱的函數
aws lambda list-functions \
  --query 'Functions[?contains(FunctionName, `query`)]'

# 查看函數詳細信息
aws lambda get-function --function-name your-function-name

# 查看函數配置
aws lambda get-function-configuration --function-name your-function-name

# 查看函數環境變數
aws lambda get-function-configuration --function-name your-function-name \
  --query 'Environment.Variables'
```

### 測試 Lambda 函數

```bash
# 同步調用 Lambda 函數
aws lambda invoke --function-name your-function-name \
  --payload '{"test": "data"}' \
  response.json

# 查看響應
cat response.json
```

## 🔧 設置環境變數

### 基於查找結果設置變數

```bash
# 1. 設置 HTTP API Gateway
export HTTP_API_GATEWAY_ID="your-found-api-id"
export EXTERNAL_API_GATEWAY="https://${HTTP_API_GATEWAY_ID}.execute-api.ap-southeast-1.amazonaws.com/prod"

# 2. 設置 ECS 服務
# 如果有 ALB
export ALB_DNS="your-found-alb-dns"
export ECS_HANDLER_URL="http://${ALB_DNS}:8000"

# 如果沒有 ALB（直接 IP 訪問）
export ECS_PUBLIC_IP="your-found-ecs-ip"
export ECS_HANDLER_URL="http://${ECS_PUBLIC_IP}:8000"

# 3. 設置內部 API Gateway
export INTERNAL_API_GATEWAY="https://your-internal-api-id.execute-api.ap-southeast-1.amazonaws.com"

# 4. 設置 DynamoDB 表
export COMMAND_TABLE="your-command-table-name"
export QUERY_TABLE="your-query-table-name"

# 5. 儲存到文件以便重複使用
cat > my_cloudshell_env.sh << EOF
export HTTP_API_GATEWAY_ID="$HTTP_API_GATEWAY_ID"
export EXTERNAL_API_GATEWAY="$EXTERNAL_API_GATEWAY"
export ECS_HANDLER_URL="$ECS_HANDLER_URL"
export INTERNAL_API_GATEWAY="$INTERNAL_API_GATEWAY"
export COMMAND_TABLE="$COMMAND_TABLE"
export QUERY_TABLE="$QUERY_TABLE"
EOF

# 載入環境變數
source my_cloudshell_env.sh
```

## 🧪 驗證設置

### 測試連接性

```bash
# 測試 HTTP API Gateway
curl -s "${EXTERNAL_API_GATEWAY}/health" | jq .

# 測試 ECS Handler
curl -s "${ECS_HANDLER_URL}/health" | jq .

# 測試 DynamoDB 表
aws dynamodb describe-table --table-name $COMMAND_TABLE \
  --query 'Table.TableStatus'

aws dynamodb describe-table --table-name $QUERY_TABLE \
  --query 'Table.TableStatus'
```

### 執行簡單查詢測試

```bash
# 測試用戶查詢
curl -s -X POST "${EXTERNAL_API_GATEWAY}/query/user" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test_user"}' | jq .

# 測試直接 ECS Handler
curl -s -X POST "${ECS_HANDLER_URL}/query/user" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test_user"}' | jq .
```

## 📝 常見問題排除

### HTTP API Gateway vs REST API Gateway

- **HTTP API Gateway**: 使用 `aws apigatewayv2` 命令
- **REST API Gateway**: 使用 `aws apigateway` 命令
- **URL 格式不同**: HTTP API 通常沒有 stage 前綴

### ECS 網路問題

- 檢查安全群組設置
- 確認 ECS 任務是否有公網 IP
- 如果使用私有子網，確認 NAT Gateway 設置

### API Gateway 權限

- 確認 Lambda 函數有正確的執行角色
- 檢查 API Gateway 的資源政策
- 驗證 CORS 設置（如果需要）

---

使用這些命令，您應該能夠手動找到所有需要的 AWS 資源並正確設置環境變數！
