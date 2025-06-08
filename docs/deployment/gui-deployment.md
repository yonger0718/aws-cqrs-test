# 🖥️ GUI 部署指南

本指南提供通過圖形化介面部署 AWS CQRS Query Service 的詳細步驟，適合偏好使用 GUI 工具的開發者和運維人員。

## 📋 目錄

- [🖥️ GUI 部署指南](#️-gui-部署指南)
  - [📋 目錄](#-目錄)
  - [🎯 部署方式概覽](#-部署方式概覽)
  - [🔧 先決條件](#-先決條件)
  - [🏗️ AWS 管理控制台部署](#️-aws-管理控制台部署)
    - [Step 1: 設定 ECR 儲存庫](#step-1-設定-ecr-儲存庫)
    - [Step 2: 建立 ECS 叢集](#step-2-建立-ecs-叢集)
    - [Step 3: 設定任務定義](#step-3-設定任務定義)
    - [Step 4: 建立 ECS 服務](#step-4-建立-ecs-服務)
    - [Step 5: 設定 Lambda 函數](#step-5-設定-lambda-函數)
    - [Step 6: 配置 API Gateway](#step-6-配置-api-gateway)
    - [Step 7: 設定 DynamoDB](#step-7-設定-dynamodb)
  - [🚀 GitHub Actions GUI 部署](#-github-actions-gui-部署)
  - [🔄 AWS CodePipeline 部署](#-aws-codepipeline-部署)
  - [📊 Terraform Cloud 部署](#-terraform-cloud-部署)
  - [🖱️ Docker Desktop 本地部署](#️-docker-desktop-本地部署)
  - [📈 監控和管理](#-監控和管理)
  - [🔍 故障排除](#-故障排除)
  - [📚 相關資源](#-相關資源)

## 🎯 部署方式概覽

| 部署方式             | 難度     | 適用場景       | 優點               | 缺點               |
| -------------------- | -------- | -------------- | ------------------ | ------------------ |
| **AWS 管理控制台**   | ⭐⭐⭐   | 學習、小型專案 | 直觀易懂、即時反饋 | 手動操作、難以重現 |
| **GitHub Actions**   | ⭐⭐     | CI/CD 自動化   | 自動化、版本控制   | 需設定配置檔       |
| **AWS CodePipeline** | ⭐⭐⭐   | AWS 原生 CI/CD | 與 AWS 深度整合    | 學習曲線較陡       |
| **Terraform Cloud**  | ⭐⭐⭐⭐ | 基礎設施即代碼 | 狀態管理、團隊協作 | 需 Terraform 知識  |
| **Docker Desktop**   | ⭐       | 本地開發       | 簡單快速           | 僅限本地環境       |

## 🔧 先決條件

### 必要工具

- **AWS 帳戶**：具備管理員權限
- **Docker Desktop**：用於容器映像建置
- **Git 客戶端**：程式碼版本控制
- **現代瀏覽器**：建議 Chrome 或 Firefox

### 權限要求

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:*",
        "ecs:*",
        "lambda:*",
        "apigateway:*",
        "dynamodb:*",
        "iam:*",
        "logs:*",
        "application-autoscaling:*"
      ],
      "Resource": "*"
    }
  ]
}
```

## 🏗️ AWS 管理控制台部署

### Step 1: 設定 ECR 儲存庫

1. **開啟 ECR 控制台**

   - 登入 [AWS 管理控制台](https://console.aws.amazon.com/)
   - 搜尋並選擇 "Elastic Container Registry"

2. **建立儲存庫**

   ```
   儲存庫名稱: aws-cqrs-query-service
   標籤變更性: MUTABLE
   掃描設定: 啟用掃描推送
   KMS 加密: 啟用
   ```

3. **推送映像**

   - 點擊儲存庫名稱
   - 點擊「檢視推送命令」
   - 複製並執行顯示的命令

   ![ECR Push Commands](../images/ecr-push-commands.png)

### Step 2: 建立 ECS 叢集

1. **開啟 ECS 控制台**

   - 搜尋並選擇 "Elastic Container Service"

2. **建立叢集**

   ```
   叢集名稱: aws-cqrs-cluster
   基礎設施: AWS Fargate (無伺服器)
   監控: 啟用 Container Insights
   標籤:
     - Environment: production
     - Project: aws-cqrs-test
   ```

3. **設定網路**
   ```
   VPC: 選擇預設 VPC 或建立新的
   子網路: 選擇至少 2 個不同可用區域的子網路
   安全群組: 建立新的安全群組
   ```

### Step 3: 設定任務定義

1. **建立任務定義**

   ```
   任務定義系列: aws-cqrs-query-task
   啟動類型: AWS Fargate
   作業系統/架構: Linux/X86_64
   任務大小:
     - CPU: 256 CPU 單位 (0.25 vCPU)
     - 記憶體: 512 MB
   ```

2. **容器設定**

   ```
   容器名稱: query-service
   映像: [您的ECR URI]/aws-cqrs-query-service:latest
   埠對應: 80:8000
   環境變數:
     - AWS_REGION: ap-northeast-1
     - LOG_LEVEL: INFO
     - DYNAMODB_TABLE_PREFIX: aws-cqrs
   ```

   ![Task Definition Setup](../images/task-definition-setup.png)

3. **日誌設定**
   ```
   日誌驅動程式: awslogs
   日誌群組: /ecs/aws-cqrs-query-service
   日誌區域: ap-northeast-1
   日誌串流前綴: ecs
   ```

### Step 4: 建立 ECS 服務

1. **服務設定**

   ```
   服務名稱: aws-cqrs-query-service
   任務定義: aws-cqrs-query-task:1
   所需任務數量: 2
   ```

2. **網路設定**

   ```
   VPC: 與叢集相同
   子網路: 選擇私有子網路
   安全群組:
     - 允許埠 80 來自 ALB
     - 允許埠 443 來自 ALB
   ```

3. **負載平衡器設定**

   ```
   負載平衡器類型: Application Load Balancer
   負載平衡器名稱: aws-cqrs-alb
   目標群組名稱: aws-cqrs-targets
   健康檢查路徑: /health
   ```

   ![ECS Service Setup](../images/ecs-service-setup.png)

### Step 5: 設定 Lambda 函數

1. **建立查詢 Lambda**

   ```
   函數名稱: aws-cqrs-query-lambda
   執行環境: Python 3.11
   記憶體: 256 MB
   逾時: 30 秒
   ```

2. **上傳程式碼**

   - 壓縮 `query-service/lambdas/query_lambda/` 資料夾
   - 在 Lambda 控制台上傳 ZIP 檔案

3. **環境變數**

   ```
   ECS_SERVICE_URL: http://[ALB-DNS]/
   AWS_REGION: ap-northeast-1
   ```

4. **建立結果 Lambda**

   ```
   函數名稱: aws-cqrs-query-result-lambda
   執行環境: Python 3.11
   記憶體: 128 MB
   逾時: 15 秒
   ```

   ![Lambda Function Setup](../images/lambda-function-setup.png)

### Step 6: 配置 API Gateway

1. **建立 REST API**

   ```
   API 名稱: aws-cqrs-api
   API 類型: REST API
   端點類型: 區域性
   ```

2. **建立資源和方法**

   ```
   資源路徑: /query
   子資源: /user, /marketing, /fail
   方法: GET
   整合類型: Lambda 代理整合
   ```

3. **設定 CORS**

   ```
   Access-Control-Allow-Origin: *
   Access-Control-Allow-Headers: Content-Type,X-Amz-Date,Authorization
   Access-Control-Allow-Methods: GET,OPTIONS
   ```

   ![API Gateway Setup](../images/api-gateway-setup.png)

### Step 7: 設定 DynamoDB

1. **建立主要資料表**

   ```
   資料表名稱: notification-records
   分割索引鍵: notification_id (String)
   排序索引鍵: created_at (Number)
   計費模式: 隨需計費
   ```

2. **建立 GSI**

   ```
   索引名稱: user-id-index
   分割索引鍵: user_id (String)
   排序索引鍵: created_at (Number)

   索引名稱: marketing-id-index
   分割索引鍵: marketing_id (String)
   排序索引鍵: created_at (Number)

   索引名稱: transaction-id-index
   分割索引鍵: transaction_id (String)
   ```

   ![DynamoDB Table Setup](../images/dynamodb-table-setup.png)

## 🚀 GitHub Actions GUI 部署

### 1. 設定 GitHub Secrets

1. **開啟 GitHub 儲存庫**

   - 前往 Settings → Secrets and variables → Actions

2. **新增必要 Secrets**
   ```
   AWS_ACCESS_KEY_ID: [您的訪問金鑰]
   AWS_SECRET_ACCESS_KEY: [您的祕密金鑰]
   AWS_REGION: ap-northeast-1
   ECR_REPOSITORY: aws-cqrs-query-service
   ECS_CLUSTER: aws-cqrs-cluster
   ECS_SERVICE: aws-cqrs-query-service
   ```

### 2. 建立 Workflow 檔案

在儲存庫中建立 `.github/workflows/deploy.yml`：

```yaml
name: Deploy to ECS

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    name: Deploy
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ secrets.AWS_REGION }}

      - name: Login to ECR
        uses: aws-actions/amazon-ecr-login@v1

      - name: Build and push image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: ${{ secrets.ECR_REPOSITORY }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG

      - name: Deploy to ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: task-definition.json
          service: ${{ secrets.ECS_SERVICE }}
          cluster: ${{ secrets.ECS_CLUSTER }}
          wait-for-service-stability: true
```

### 3. 觸發部署

1. **手動觸發**

   - 前往 Actions 頁籤
   - 選擇 "Deploy to ECS" workflow
   - 點擊 "Run workflow"

2. **自動觸發**

   - 推送程式碼到 main 分支
   - 自動觸發部署流程

   ![GitHub Actions Deploy](../images/github-actions-deploy.png)

## 🔄 AWS CodePipeline 部署

### 1. 建立 CodePipeline

1. **開啟 CodePipeline 控制台**

   - 搜尋並選擇 "CodePipeline"

2. **建立管道**

   ```
   管道名稱: aws-cqrs-pipeline
   服務角色: 新增服務角色
   ```

3. **來源階段**
   ```
   來源提供者: GitHub (Version 2)
   連線: 建立新的 GitHub 連線
   儲存庫名稱: your-username/aws-cqrs-test
   分支名稱: main
   ```

### 2. 建置階段

1. **建立 CodeBuild 專案**

   ```
   專案名稱: aws-cqrs-build
   環境映像: 受管映像
   作業系統: Ubuntu
   執行階段: Standard
   映像: aws/codebuild/standard:5.0
   ```

2. **建置規格檔案**
   建立 `buildspec.yml`：

```yaml
version: 0.2

phases:
  pre_build:
    commands:
      - echo Logging in to Amazon ECR...
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com
  build:
    commands:
      - echo Build started on `date`
      - echo Building the Docker image...
      - docker build -t $IMAGE_REPO_NAME:$IMAGE_TAG .
      - docker tag $IMAGE_REPO_NAME:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG
  post_build:
    commands:
      - echo Build completed on `date`
      - echo Pushing the Docker image...
      - docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG
```

### 3. 部署階段

```
部署提供者: Amazon ECS
叢集名稱: aws-cqrs-cluster
服務名稱: aws-cqrs-query-service
映像定義檔案: imagedefinitions.json
```

![CodePipeline Setup](../images/codepipeline-setup.png)

## 📊 Terraform Cloud 部署

### 1. 設定 Terraform Cloud

1. **建立 Terraform Cloud 帳戶**

   - 前往 [Terraform Cloud](https://app.terraform.io/)
   - 建立組織和工作區

2. **工作區設定**
   ```
   工作區名稱: aws-cqrs-production
   執行模式: Remote
   Terraform 版本: Latest
   ```

### 2. 設定變數

1. **環境變數**

   ```
   AWS_ACCESS_KEY_ID: [您的訪問金鑰]
   AWS_SECRET_ACCESS_KEY: [您的祕密金鑰] (敏感)
   AWS_DEFAULT_REGION: ap-northeast-1
   ```

2. **Terraform 變數**
   ```
   cluster_name: aws-cqrs-cluster
   service_name: aws-cqrs-query-service
   environment: production
   ```

### 3. 連接 VCS

1. **GitHub 整合**

   - 設定 → Version Control
   - 連接到 GitHub 儲存庫
   - 設定自動觸發條件

2. **觸發部署**

   - 推送程式碼觸發自動執行
   - 或在 Terraform Cloud 中手動觸發

   ![Terraform Cloud Setup](../images/terraform-cloud-setup.png)

## 🖱️ Docker Desktop 本地部署

### 1. 安裝 Docker Desktop

1. **下載安裝**

   - 前往 [Docker Desktop](https://www.docker.com/products/docker-desktop)
   - 下載並安裝適合您作業系統的版本

2. **啟動服務**
   - 確保 Docker Desktop 正在運行
   - 檢查狀態圖示為綠色

### 2. 使用 Docker Compose

1. **建立 docker-compose.yml**

```yaml
version: "3.8"
services:
  query-service:
    build: .
    ports:
      - "8000:8000"
    environment:
      - AWS_REGION=ap-northeast-1
      - LOG_LEVEL=DEBUG
    depends_on:
      - dynamodb-local

  dynamodb-local:
    image: amazon/dynamodb-local
    ports:
      - "8001:8000"
    command: -jar DynamoDBLocal.jar -inMemory -sharedDb
```

2. **GUI 操作**

   - 開啟 Docker Desktop
   - 前往 Compose 頁籤
   - 選擇專案資料夾
   - 點擊「Start」

   ![Docker Desktop Compose](../images/docker-desktop-compose.png)

## 📈 監控和管理

### 1. CloudWatch 儀表板

1. **建立儀表板**

   - 開啟 CloudWatch 控制台
   - 建立自訂儀表板

2. **新增小工具**

   ```
   ECS 服務指標:
   - CPU 使用率
   - 記憶體使用率
   - 運行任務數量

   Lambda 指標:
   - 調用次數
   - 錯誤率
   - 持續時間

   DynamoDB 指標:
   - 讀取容量
   - 寫入容量
   - 節流事件
   ```

### 2. 警示設定

1. **建立警示**

   ```
   高 CPU 使用率: > 80%
   高錯誤率: > 5%
   回應時間: > 2000ms
   ```

2. **通知設定**

   ```
   SNS 主題: aws-cqrs-alerts
   電子郵件通知: your-email@example.com
   ```

   ![CloudWatch Dashboard](../images/cloudwatch-dashboard.png)

## 🔍 故障排除

### 常見問題

#### 1. ECS 任務無法啟動

```
檢查項目:
✅ 任務定義中的映像 URI 是否正確
✅ IAM 角色權限是否充足
✅ 安全群組規則是否正確
✅ 子網路是否有網際網路閘道
```

#### 2. Lambda 函數逾時

```
解決方案:
📝 增加函數逾時設定
📝 檢查網路連線
📝 最佳化程式碼效能
📝 增加記憶體配置
```

#### 3. API Gateway 502 錯誤

```
檢查項目:
✅ Lambda 函數是否正常運行
✅ 整合設定是否正確
✅ 函數權限是否充足
✅ 回應格式是否符合要求
```

### 除錯工具

1. **CloudWatch Logs**

   - 即時查看日誌
   - 設定日誌過濾器
   - 下載日誌檔案

2. **AWS X-Ray**

   - 分散式追蹤
   - 效能分析
   - 錯誤定位

   ![Troubleshooting Dashboard](../images/troubleshooting-dashboard.png)

## 📚 相關資源

### 文檔連結

- [AWS ECS 使用者指南](https://docs.aws.amazon.com/ecs/)
- [AWS Lambda 開發者指南](https://docs.aws.amazon.com/lambda/)
- [API Gateway 開發者指南](https://docs.aws.amazon.com/apigateway/)
- [DynamoDB 開發者指南](https://docs.aws.amazon.com/dynamodb/)

### 相關文檔

- [📋 ECS 遷移指南](../architecture/ecs-migration-guide.md)
- [⚙️ 命令列部署指南](./ecs-deployment.md)
- [🔄 API 變更文檔](../api/api-changes-v3.md)

### 支援資源

- **AWS Support**: 技術支援和諮詢
- **GitHub Issues**: 程式碼問題回報
- **Team Slack**: #aws-cqrs-support

---

💡 **提示**: 建議先在開發環境測試 GUI 部署流程，確認無誤後再部署到生產環境。

📞 **支援**: 如有任何問題，請聯絡開發團隊或提交 GitHub Issue。
