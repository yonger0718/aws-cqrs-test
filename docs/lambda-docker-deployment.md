# Lambda Docker 部署指南

本指南說明如何使用 Docker 容器部署 AWS Lambda 函數，支援本地開發和生產環境。

## 🎯 概述

Docker 化的 Lambda 部署提供以下優勢：

- **一致性**: 開發、測試和生產環境使用相同的容器映像
- **依賴管理**: 更好的依賴隔離和版本控制
- **可重現性**: 避免了 "在我機器上能跑" 的問題
- **GUI 支援**: 解決了使用圖形介面工具時的依賴問題
- **調試能力**: 可以本地運行和調試容器化的 Lambda 函數

## 🏗️ 架構

```txt
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   Source Code       │───▶│   Docker Images      │───▶│   Lambda Functions  │
│   - app.py          │    │   - Base: AWS Lambda │    │   - LocalStack      │
│   - requirements.txt│    │   - Python 3.12     │    │   - AWS             │
│   - Dockerfile      │    │   - Dependencies     │    │   - Container Mode  │
└─────────────────────────┘    └──────────────────────┘    └─────────────────────┘
```

## 📁 檔案結構

```txt
query-service/lambdas/
├── docker-compose.lambda.yml      # Lambda 映像構建配置
├── deploy_docker_lambdas.sh       # Docker 部署腳本
├── stream_processor_lambda/
│   ├── Dockerfile                 # Stream 處理器容器定義
│   ├── .dockerignore              # 忽略不必要的檔案
│   ├── app.py                     # Lambda 函數代碼
│   ├── requirements.txt           # Python 依賴
│   └── __init__.py
├── query_lambda/
│   ├── Dockerfile                 # 查詢入口容器定義
│   ├── .dockerignore
│   ├── app.py
│   ├── requirements.txt
│   └── __init__.py
└── query_result_lambda/
    ├── Dockerfile                 # 查詢結果容器定義
    ├── .dockerignore
    ├── app.py
    ├── requirements.txt
    └── __init__.py
```

## 🐳 Dockerfile 說明

每個 Lambda 函數都使用標準化的 Dockerfile：

```dockerfile
FROM public.ecr.aws/lambda/python:3.12

# 複製 requirements.txt 文件
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式代碼
COPY app.py ${LAMBDA_TASK_ROOT}
COPY __init__.py ${LAMBDA_TASK_ROOT}

# 設置 Lambda 函數的處理程序
CMD ["app.lambda_handler"]
```

### 基礎映像特點

- **AWS 官方映像**: `public.ecr.aws/lambda/python:3.12`
- **Lambda 運行時**: 包含 AWS Lambda 運行時和 Python 3.12
- **最佳化**: 為 Lambda 冷啟動優化
- **安全性**: 定期更新，包含安全補丁

## 🚀 部署方式

### 1. 自動化部署腳本

我們提供了統一的部署管理腳本 `deploy_docker.sh`：

```bash
# 查看所有可用命令
./deploy_docker.sh help

# 啟動完整環境
./deploy_docker.sh start

# 構建所有 Lambda 映像
./deploy_docker.sh build

# 部署 Lambda 函數
./deploy_docker.sh deploy

# 檢查服務狀態
./deploy_docker.sh status
```

### 2. 手動部署流程

#### 步驟 1: 構建 Docker 映像

```bash
cd query-service/lambdas

# 構建所有 Lambda 映像
docker-compose -f docker-compose.lambda.yml build

# 或構建單個映像
docker build -t query-service-stream-processor-lambda:latest ./stream_processor_lambda
```

#### 步驟 2: 部署到 LocalStack

```bash
# 執行 Docker 部署腳本
chmod +x deploy_docker_lambdas.sh
./deploy_docker_lambdas.sh
```

#### 步驟 3: 驗證部署

```bash
# 列出 Lambda 函數
aws --endpoint-url=http://localhost:4566 lambda list-functions

# 測試函數調用
aws --endpoint-url=http://localhost:4566 lambda invoke \
    --function-name query-service-stream_processor_lambda \
    --payload '{}' \
    response.json
```

## 🔧 配置說明

### Docker Compose 配置

`docker-compose.lambda.yml` 定義了所有 Lambda 函數的構建配置：

```yaml
version: "3.8"

services:
  stream-processor-lambda:
    build:
      context: ./stream_processor_lambda
      dockerfile: Dockerfile
    image: query-service-stream-processor-lambda:latest
    environment:
      - AWS_LAMBDA_FUNCTION_NAME=query-service-stream_processor_lambda
      - LOCALSTACK_HOSTNAME=localstack
      - AWS_REGION=ap-southeast-1
```

### 環境變數

每個 Lambda 函數支援以下環境變數：

| 變數名稱                   | 說明                 | 預設值                  |
| -------------------------- | -------------------- | ----------------------- |
| `AWS_LAMBDA_FUNCTION_NAME` | Lambda 函數名稱      | -                       |
| `LOCALSTACK_HOSTNAME`      | LocalStack 主機名    | localstack              |
| `AWS_REGION`               | AWS 區域             | ap-southeast-1          |
| `NOTIFICATION_TABLE_NAME`  | 通知記錄表名稱       | notification-records    |
| `EKS_HANDLER_URL`          | EKS Handler 服務 URL | http://ecs-handler:8000 |
| `REQUEST_TIMEOUT`          | 請求超時時間（秒）   | 10                      |

## 🧪 測試和驗證

### 1. 本地測試

```bash
# 啟動服務並運行測試
./deploy_docker.sh start
./deploy_docker.sh test
```

### 2. 單元測試

```bash
# 在專案根目錄執行
poetry run pytest query-service/tests/test_lambdas/ -v
```

### 3. 整合測試

```bash
# 測試 API Gateway 端點
curl "http://localhost:4566/restapis/API_ID/dev/_user_request_/user?user_id=test_user_001"
```

### 4. Lambda 函數直接調用測試

```bash
# 測試 stream_processor_lambda
aws --endpoint-url=http://localhost:4566 lambda invoke \
    --function-name query-service-stream_processor_lambda \
    --payload '{"Records":[{"eventName":"INSERT","dynamodb":{"NewImage":{"transaction_id":{"S":"test"}}}}]}' \
    response.json

cat response.json
```

## 🔍 故障排除

### 常見問題

#### 1. Docker 映像構建失敗

```bash
# 檢查 Docker 狀態
docker info

# 清理構建快取
docker system prune -f

# 重新構建（無快取）
./deploy_docker.sh build --no-cache
```

#### 2. Lambda 函數部署失敗

```bash
# 檢查 LocalStack 狀態
curl http://localhost:4566/health

# 查看 LocalStack 日誌
docker-compose logs localstack

# 檢查網路連接
docker network ls
```

#### 3. 函數調用失敗

```bash
# 查看 Lambda 函數日誌
aws --endpoint-url=http://localhost:4566 logs describe-log-groups

# 獲取日誌
aws --endpoint-url=http://localhost:4566 logs get-log-events \
    --log-group-name /aws/lambda/FUNCTION_NAME \
    --log-stream-name STREAM_NAME
```

### 調試技巧

#### 1. 本地運行容器

```bash
# 本地運行 Lambda 容器
docker run --rm -p 9000:8080 \
    -e AWS_LAMBDA_FUNCTION_NAME=test \
    query-service-stream-processor-lambda:latest

# 在另一個終端機測試
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
    -d '{"test": "data"}'
```

#### 2. 容器內部檢查

```bash
# 進入容器內部
docker run --rm -it --entrypoint /bin/bash \
    query-service-stream-processor-lambda:latest

# 檢查已安裝的套件
pip list

# 測試模組導入
python -c "import app; print('Success')"
```

## 🔄 CI/CD 整合

### GitHub Actions 範例

```yaml
name: Lambda Docker Deployment

on:
  push:
    paths:
      - "query-service/lambdas/**"

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Lambda Images
        run: |
          cd query-service/lambdas
          docker-compose -f docker-compose.lambda.yml build

      - name: Deploy to LocalStack
        run: |
          cd query-service
          ./deploy_docker.sh start
          ./deploy_docker.sh test
```

## 📚 最佳實踐

### 1. 映像最佳化

- **多階段構建**: 減少最終映像大小
- **Layer 快取**: 合理安排 COPY 指令順序
- **依賴鎖定**: 使用具體版本號

### 2. 安全性

- **最小權限**: Lambda 函數只獲取必要的 IAM 權限
- **密碼管理**: 使用 AWS Secrets Manager 存儲敏感信息
- **映像掃描**: 定期掃描容器映像漏洞

### 3. 效能優化

- **冷啟動**: 最小化函數包大小
- **記憶體配置**: 根據實際需求調整記憶體分配
- **連線復用**: 在全域範圍初始化客戶端

### 4. 監控和日誌

- **結構化日誌**: 使用 JSON 格式日誌
- **追蹤**: 整合 AWS X-Ray 進行分散式追蹤
- **指標**: 定義自定義 CloudWatch 指標

## 🌐 生產環境部署

### AWS 部署

生產環境可以使用相同的 Docker 映像部署到 AWS Lambda：

```bash
# 推送映像到 ECR
aws ecr get-login-password --region ap-southeast-1 | \
    docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.ap-southeast-1.amazonaws.com

docker tag query-service-stream-processor-lambda:latest \
    ACCOUNT_ID.dkr.ecr.ap-southeast-1.amazonaws.com/query-service-stream-processor-lambda:latest

docker push ACCOUNT_ID.dkr.ecr.ap-southeast-1.amazonaws.com/query-service-stream-processor-lambda:latest

# 更新 Lambda 函數
aws lambda update-function-code \
    --function-name query-service-stream_processor_lambda \
    --image-uri ACCOUNT_ID.dkr.ecr.ap-southeast-1.amazonaws.com/query-service-stream-processor-lambda:latest
```

### Terraform 整合

更新 Terraform 配置以使用容器映像：

```hcl
resource "aws_lambda_function" "stream_processor" {
  function_name = "query-service-stream_processor_lambda"
  role         = aws_iam_role.lambda_role.arn

  package_type = "Image"
  image_uri    = "${var.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/query-service-stream-processor-lambda:latest"

  timeout     = 30
  memory_size = 512

  environment {
    variables = {
      NOTIFICATION_TABLE_NAME = var.notification_table_name
      AWS_REGION             = var.aws_region
    }
  }
}
```

這樣的設計確保了從開發到生產環境的一致性，並提供了更好的依賴管理和部署體驗。
