# AWS Console GUI 部署指南

## 概述

本指南詳細說明如何使用 AWS Management Console 的圖形介面手動部署 CQRS Query Service 的 Lambda 函數和 ECS 服務。

## 🚀 前置準備

### 1. ECR 儲存庫準備

- 登入 AWS Console → Elastic Container Registry (ECR)
- 創建儲存庫：`query-service`
- 推送 Docker 映像到 ECR

### 2. IAM 角色準備

創建以下 IAM 角色：

- `ecsTaskExecutionRole` - ECS 任務執行角色
- `ecsTaskRole` - ECS 任務角色
- `lambda-execution-role` - Lambda 執行角色

## 📦 ECS 服務部署 (GUI 步驟)

### 步驟 1: 創建 ECS 集群

1. **進入 ECS Console**

   - 導航到 AWS Console → Elastic Container Service (ECS)
   - 點擊 "Clusters" → "Create Cluster"

2. **集群配置**

   ```
   Cluster name: query-service-cluster
   Infrastructure: AWS Fargate (serverless)
   ```

3. **網路設定**
   ```
   Namespace: query-service-namespace (可選)
   Tags:
     - Environment: production
     - Service: query-service
   ```

### 步驟 2: 創建任務定義

1. **進入任務定義**

   - ECS Console → Task definitions → Create new task definition

2. **基本配置**

   ```
   Task definition family: query-service-task
   Launch type: AWS Fargate
   Operating system family: Linux
   Task role: ecsTaskRole
   Task execution role: ecsTaskExecutionRole
   ```

3. **任務大小**

   ```
   CPU: 0.25 vCPU (256)
   Memory: 0.5 GB (512)
   ```

4. **容器定義**

   - 點擊 "Add container"

   **基本設定**

   ```
   Container name: query-service-container
   Image URI: {ACCOUNT_ID}.dkr.ecr.ap-southeast-1.amazonaws.com/query-service:latest
   ```

   **網路設定**

   ```
   Port mappings:
     - Container port: 8000
     - Protocol: TCP
   ```

   **環境變數**

   ```
   Environment variables:
   - ENVIRONMENT: production
   - INTERNAL_API_URL: https://your-api-gateway-id.execute-api.ap-southeast-1.amazonaws.com/v1
   - AWS_DEFAULT_REGION: ap-southeast-1
   - AWS_REGION: ap-southeast-1
   - REQUEST_TIMEOUT: 30
   ```

   **日誌配置**

   ```
   Log driver: awslogs
   Options:
     - awslogs-group: /ecs/query-service
     - awslogs-region: ap-southeast-1
     - awslogs-stream-prefix: ecs
   ```

   **健康檢查**

   ```
   Health check command: CMD-SHELL,curl -f http://localhost:8000/health || exit 1
   Interval: 30 seconds
   Timeout: 5 seconds
   Retries: 3
   Start period: 60 seconds
   ```

### 步驟 3: 創建 Application Load Balancer

1. **進入 EC2 Console**

   - AWS Console → EC2 → Load Balancers → Create Load Balancer

2. **選擇類型**

   - Application Load Balancer

3. **基本配置**

   ```
   Name: query-service-alb
   Scheme: Internal
   IP address type: IPv4
   ```

4. **網路映射**

   ```
   VPC: 選擇您的 VPC
   Availability Zones: 選擇至少 2 個私有子網
   ```

5. **安全群組**

   - 創建新的安全群組或選擇現有的
   - 允許入站流量：Port 80/443

6. **目標群組配置**
   ```
   Target type: IP addresses
   Protocol: HTTP
   Port: 8000
   Health check path: /health
   ```

### 步驟 4: 創建 ECS 服務

1. **進入集群**

   - ECS Console → Clusters → query-service-cluster → Services tab

2. **創建服務**

   - 點擊 "Create"

3. **服務配置**

   ```
   Launch type: Fargate
   Task Definition: query-service-task:1
   Service name: query-service
   Number of tasks: 1
   ```

4. **網路配置**

   ```
   VPC: 選擇您的 VPC
   Subnets: 選擇私有子網
   Security group: 創建新的或選擇現有的
     - 允許入站：Port 8000 from ALB security group
   Auto-assign public IP: DISABLED
   ```

5. **負載均衡器**

   ```
   Load balancer type: Application Load Balancer
   Load balancer: query-service-alb
   Container to load balance: query-service-container:8000
   Target group: 選擇先前創建的目標群組
   ```

6. **服務發現 (可選)**
   ```
   Enable service discovery: Yes
   Namespace: query-service-namespace
   Service name: query-service
   ```

## ⚡ Lambda 函數部署 (GUI 步驟)

### 步驟 1: 創建 Stream Processor Lambda

1. **進入 Lambda Console**

   - AWS Console → Lambda → Create function

2. **基本配置**

   ```
   Function name: query-service-stream-processor
   Runtime: 選擇 "Container image"
   Container image URI: {ACCOUNT_ID}.dkr.ecr.ap-southeast-1.amazonaws.com/query-service-stream-processor-lambda:latest
   ```

3. **執行角色**

   ```
   Execution role: Use an existing role
   Existing role: lambda-execution-role
   ```

4. **進階設定**

   ```
   Timeout: 3 minutes
   Memory: 256 MB
   ```

5. **環境變數**

   - Configuration → Environment variables

   ```
   AWS_LAMBDA_FUNCTION_NAME: query-service-stream-processor
   AWS_REGION: ap-southeast-1
   NOTIFICATION_TABLE_NAME: EventQuery
   ```

6. **觸發器設定**
   - Add trigger → DynamoDB
   ```
   DynamoDB table: command-records
   Starting position: Latest
   Batch size: 10
   Maximum batching window: 5 seconds
   ```

### 步驟 2: 創建 Query Lambda

1. **基本配置**

   ```
   Function name: query-service-query-lambda
   Runtime: Container image
   Container image URI: {ACCOUNT_ID}.dkr.ecr.ap-southeast-1.amazonaws.com/query-service-query-lambda:latest
   ```

2. **環境變數**

   ```
   AWS_LAMBDA_FUNCTION_NAME: query-service-query-lambda
   EKS_HANDLER_URL: http://your-internal-alb-url:8000
   REQUEST_TIMEOUT: 10
   ```

3. **VPC 配置**
   - Configuration → VPC
   ```
   VPC: 選擇與 ECS 相同的 VPC
   Subnets: 選擇私有子網
   Security groups: 允許出站連接到 ECS 服務
   ```

### 步驟 3: 創建 Query Result Lambda

1. **基本配置**

   ```
   Function name: query-service-query-result-lambda
   Runtime: Container image
   Container image URI: {ACCOUNT_ID}.dkr.ecr.ap-southeast-1.amazonaws.com/query-service-query-result-lambda:latest
   ```

2. **環境變數**
   ```
   AWS_LAMBDA_FUNCTION_NAME: query-service-query-result-lambda
   AWS_REGION: ap-southeast-1
   NOTIFICATION_TABLE_NAME: EventQuery
   ```

## 🔧 API Gateway 設定

### 步驟 1: 創建 REST API

1. **進入 API Gateway Console**

   - AWS Console → API Gateway → Create API → REST API

2. **API 設定**
   ```
   API name: query-service-internal-api
   Endpoint Type: Regional
   ```

### 步驟 2: 創建資源和方法

1. **創建資源結構**

   ```
   /query
     /user (GET)
     /marketing (GET)
     /fail (GET)
   ```

2. **設定 Lambda 整合**
   - 為每個端點配置對應的 Lambda 函數
   - 啟用 Lambda Proxy 整合

### 步驟 3: 部署 API

1. **創建部署**

   - Actions → Deploy API

   ```
   Deployment stage: v1
   Stage description: Production deployment
   ```

2. **獲取 API URL**
   - 記錄 Invoke URL 用於 ECS 環境變數

## 📋 驗證部署

### 健康檢查

1. **ECS 服務檢查**

   ```bash
   curl http://your-alb-url/health
   ```

2. **Lambda 函數測試**

   - Lambda Console → Test → 創建測試事件

3. **API Gateway 測試**
   - API Gateway Console → Test → 測試各個端點

### 監控設定

1. **CloudWatch 日誌群組**

   - 確認所有服務的日誌正常寫入

2. **CloudWatch 指標**

   - 設定 ECS 和 Lambda 監控面板

3. **警報設定**
   - 為關鍵指標設定 CloudWatch 警報

## 🔍 故障排除

### 常見問題

1. **ECS 任務啟動失敗**

   - 檢查 IAM 角色權限
   - 確認 ECR 映像存在
   - 查看 CloudWatch 日誌

2. **Lambda 函數執行錯誤**

   - 檢查環境變數配置
   - 確認 VPC 網路設定
   - 檢查 IAM 執行角色權限

3. **API Gateway 連接問題**
   - 確認 Lambda 函數配置正確
   - 檢查 API Gateway 部署狀態
   - 驗證 VPC 端點設定

## 📝 檢查清單

- [ ] ECR 儲存庫已創建並推送映像
- [ ] IAM 角色配置正確
- [ ] ECS 集群已創建
- [ ] ECS 任務定義已配置
- [ ] Application Load Balancer 已設定
- [ ] ECS 服務正常運行
- [ ] Lambda 函數已部署
- [ ] DynamoDB 觸發器已設定
- [ ] API Gateway 已配置並部署
- [ ] 環境變數已正確設定
- [ ] 健康檢查通過
- [ ] 日誌和監控已設定
