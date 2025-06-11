#!/bin/bash

# LocalStack CQRS 架構設置腳本 - Docker 版本
set -e

echo "🐳 LocalStack CQRS Architecture Setup (Docker Version)"
echo "=================================================="

# 等待 LocalStack 完全啟動
echo "Waiting for LocalStack to be ready..."
until curl -f http://localhost:4566/_localstack/health > /dev/null 2>&1; do
    echo "LocalStack not ready yet, waiting..."
    sleep 2
done
echo "LocalStack is ready!"

# 創建 IAM 角色
echo "Creating IAM roles..."
awslocal iam create-role \
    --role-name lambda-role \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }' > /dev/null 2>&1 || echo "Role might already exist"

# 附加基本執行角色
awslocal iam attach-role-policy \
    --role-name lambda-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole > /dev/null 2>&1 || true

# 附加 DynamoDB 完整訪問權限
awslocal iam attach-role-policy \
    --role-name lambda-role \
    --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess > /dev/null 2>&1 || true

echo "IAM roles created successfully."

# 創建 DynamoDB 表
echo "Creating DynamoDB tables..."

# 檢查並刪除現有表格（如果存在）
for table in "command-records" "notification-records"; do
    if awslocal dynamodb describe-table --table-name $table > /dev/null 2>&1; then
        echo "Deleting existing table: $table"
        awslocal dynamodb delete-table --table-name $table
        awslocal dynamodb wait table-not-exists --table-name $table
    fi
done

# 創建 Command Table (寫入側)
awslocal dynamodb create-table \
    --table-name command-records \
    --attribute-definitions \
        AttributeName=transaction_id,AttributeType=S \
        AttributeName=created_at,AttributeType=N \
    --key-schema \
        AttributeName=transaction_id,KeyType=HASH \
        AttributeName=created_at,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES

# 創建 Query Table (讀取側)
awslocal dynamodb create-table \
    --table-name notification-records \
    --attribute-definitions \
        AttributeName=user_id,AttributeType=S \
        AttributeName=created_at,AttributeType=N \
        AttributeName=marketing_id,AttributeType=S \
        AttributeName=status,AttributeType=S \
    --key-schema \
        AttributeName=user_id,KeyType=HASH \
        AttributeName=created_at,KeyType=RANGE \
    --global-secondary-indexes \
        'IndexName=MarketingIndex,KeySchema=[{AttributeName=marketing_id,KeyType=HASH},{AttributeName=created_at,KeyType=RANGE}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}' \
        'IndexName=StatusIndex,KeySchema=[{AttributeName=status,KeyType=HASH},{AttributeName=created_at,KeyType=RANGE}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}' \
    --billing-mode PAY_PER_REQUEST

# 等待表格創建完成
echo "Waiting for tables to be created..."
awslocal dynamodb wait table-exists --table-name command-records
awslocal dynamodb wait table-exists --table-name notification-records

echo "DynamoDB tables created successfully."

# 獲取 DynamoDB Stream ARN
STREAM_ARN=$(awslocal dynamodb describe-table \
    --table-name command-records \
    --query 'Table.LatestStreamArn' --output text)

echo "Stream ARN: $STREAM_ARN"

# 插入測試資料到 Command Table
echo "Inserting test data to command table..."

# 測試資料 1: 成功發送
awslocal dynamodb put-item \
    --table-name command-records \
    --item '{
        "transaction_id": {"S": "tx_001"},
        "created_at": {"N": "1704067200000"},
        "user_id": {"S": "test_user_001"},
        "marketing_id": {"S": "campaign_2024_new_year"},
        "notification_title": {"S": "新年快樂促銷"},
        "status": {"S": "SENT"},
        "platform": {"S": "IOS"},
        "device_token": {"S": "ios_token_123"},
        "payload": {"S": "{\"title\": \"新年快樂促銷\", \"body\": \"新年特惠，限時搶購！\"}"},
        "ap_id": {"S": "mobile-app-001"}
    }'

# 測試資料 2: 失敗案例
awslocal dynamodb put-item \
    --table-name command-records \
    --item '{
        "transaction_id": {"S": "tx_002"},
        "created_at": {"N": "1704153600000"},
        "user_id": {"S": "test_user_002"},
        "marketing_id": {"S": "campaign_2024_valentine"},
        "notification_title": {"S": "情人節特惠"},
        "status": {"S": "FAILED"},
        "platform": {"S": "ANDROID"},
        "device_token": {"S": "android_token_456"},
        "error_msg": {"S": "Device token invalid"},
        "payload": {"S": "{\"title\": \"情人節特惠\", \"body\": \"愛心滿滿的優惠來了！\"}"},
        "ap_id": {"S": "mobile-app-002"}
    }'

# 測試資料 3: Web 推播
awslocal dynamodb put-item \
    --table-name command-records \
    --item '{
        "transaction_id": {"S": "tx_003"},
        "created_at": {"N": "1704240000000"},
        "user_id": {"S": "test_user_001"},
        "marketing_id": {"S": "campaign_2024_spring"},
        "notification_title": {"S": "春季促銷"},
        "status": {"S": "DELIVERED"},
        "platform": {"S": "WEBPUSH"},
        "device_token": {"S": "web_token_789"},
        "payload": {"S": "{\"title\": \"春季促銷\", \"body\": \"春季大促銷活動現在開始！\"}"},
        "ap_id": {"S": "web-portal-001"}
    }'

# 測試資料 4: 另一個失敗案例
awslocal dynamodb put-item \
    --table-name command-records \
    --item '{
        "transaction_id": {"S": "tx_004"},
        "created_at": {"N": "1704211200000"},
        "user_id": {"S": "test_user_003"},
        "marketing_id": {"S": "campaign_2024_new_year"},
        "notification_title": {"S": "限時優惠"},
        "status": {"S": "FAILED"},
        "platform": {"S": "IOS"},
        "device_token": {"S": "ios_token_999"},
        "error_msg": {"S": "Network timeout"},
        "payload": {"S": "{\"title\": \"限時優惠\", \"body\": \"最後機會，不要錯過！\"}"},
        "ap_id": {"S": "mobile-app-003"}
    }'

echo "Test data inserted to command table successfully."

# 部署 Docker 化的 Lambda 函數
echo "Building and deploying Docker-based Lambda functions..."

# 進入 Lambda 目錄並運行 Docker 部署腳本
cd /opt/code/lambdas

# 檢查是否存在 Docker 部署腳本
if [ -f "deploy_docker_lambdas.sh" ]; then
    # 確保腳本有執行權限
    chmod +x deploy_docker_lambdas.sh

    # 執行 Docker 部署腳本
    echo "執行 Docker Lambda 部署..."
    ./deploy_docker_lambdas.sh
else
    echo "❌ Docker 部署腳本不存在，回退到傳統部署方式..."

    # 回退到原始的 ZIP 包部署方式
    echo "Creating environment variable files..."
    echo '{"Variables":{"LOCALSTACK_HOSTNAME":"localstack","AWS_REGION":"ap-southeast-1","NOTIFICATION_TABLE_NAME":"notification-records"}}' > /tmp/env.json
    echo '{"Variables":{"EKS_HANDLER_URL":"http://ecs-handler:8000","REQUEST_TIMEOUT":"10"}}' > /tmp/query_env.json

    # Lambda 函數列表
    declare -A LAMBDA_FUNCTIONS=(
        ["stream_processor_lambda"]="query-service-stream_processor_lambda"
        ["query_lambda"]="query-service-query_lambda"
        ["query_result_lambda"]="query-service-query_result_lambda"
    )

    # 構建並部署每個 Lambda 函數
    for lambda_dir in "${!LAMBDA_FUNCTIONS[@]}"; do
        function_name="${LAMBDA_FUNCTIONS[$lambda_dir]}"
        echo "部署 $function_name..."

        # 創建構建目錄
        mkdir -p /tmp/lambda-build/$lambda_dir
        cp -r $lambda_dir/* /tmp/lambda-build/$lambda_dir/
        cd /tmp/lambda-build/$lambda_dir

        # 安裝依賴
        if [ -f "requirements.txt" ]; then
            pip install --no-cache-dir -r requirements.txt -t . > /dev/null 2>&1
        fi

        # 清理不必要的文件
        find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find . -name "test_*.py" -delete 2>/dev/null || true
        find . -name "*_test.py" -delete 2>/dev/null || true
        find . -name "pytest.ini" -delete 2>/dev/null || true
        find . -name "run_tests.sh" -delete 2>/dev/null || true

        # 打包
        zip -r /tmp/$lambda_dir.zip . > /dev/null

        # 設置環境變量
        case "$lambda_dir" in
            "query_lambda")
                env_file="/tmp/query_env.json"
                ;;
            *)
                env_file="/tmp/env.json"
                ;;
        esac

        # 部署
        awslocal lambda create-function \
            --function-name $function_name \
            --runtime python3.12 \
            --handler app.lambda_handler \
            --zip-file fileb:///tmp/$lambda_dir.zip \
            --role arn:aws:iam::000000000000:role/lambda-role \
            --environment file://$env_file \
            --timeout 30 \
            --memory-size 512

        echo "✅ $function_name 部署成功"
        cd /opt/code/lambdas
    done
fi

echo "Lambda functions deployment completed."

# 創建 DynamoDB Stream 事件源映射
echo "Creating DynamoDB Stream event source mapping..."
awslocal lambda create-event-source-mapping \
    --function-name query-service-stream_processor_lambda \
    --event-source-arn $STREAM_ARN \
    --starting-position LATEST \
    --batch-size 10

echo "Event source mapping created successfully."

# 等待一下讓 Stream 處理完成
echo "Waiting for stream processing to complete..."
sleep 10

# 創建 API Gateway
echo "Creating API Gateway..."

# 創建 REST API
API_ID=$(awslocal apigateway create-rest-api \
    --name "Query Service API" \
    --description "API for querying notification records with CQRS pattern" \
    --query 'id' --output text)

# 獲取根資源 ID
ROOT_ID=$(awslocal apigateway get-resources \
    --rest-api-id $API_ID \
    --query 'items[0].id' --output text)

# 創建 /user 資源
USER_ID=$(awslocal apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_ID \
    --path-part "user" \
    --query 'id' --output text)

# 創建 /marketing 資源
MARKETING_ID=$(awslocal apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_ID \
    --path-part "marketing" \
    --query 'id' --output text)

# 創建 /tx 資源
TX_ID=$(awslocal apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_ID \
    --path-part "tx" \
    --query 'id' --output text)

# 創建 /fail 資源
FAIL_ID=$(awslocal apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_ID \
    --path-part "fail" \
    --query 'id' --output text)

# 為每個資源創建 GET 方法並整合 Lambda
for RESOURCE_ID in $USER_ID $MARKETING_ID $TX_ID $FAIL_ID; do
    # 創建 GET 方法
    awslocal apigateway put-method \
        --rest-api-id $API_ID \
        --resource-id $RESOURCE_ID \
        --http-method GET \
        --authorization-type NONE \
        --request-parameters "method.request.querystring.user_id=false,method.request.querystring.marketing_id=false,method.request.querystring.transaction_id=false"

    # 創建 Lambda 整合
    awslocal apigateway put-integration \
        --rest-api-id $API_ID \
        --resource-id $RESOURCE_ID \
        --http-method GET \
        --type AWS_PROXY \
        --integration-http-method POST \
        --uri "arn:aws:apigateway:ap-southeast-1:lambda:path/2015-03-31/functions/arn:aws:lambda:ap-southeast-1:000000000000:function:query-service-query_lambda/invocations"

    # 設置方法響應
    awslocal apigateway put-method-response \
        --rest-api-id $API_ID \
        --resource-id $RESOURCE_ID \
        --http-method GET \
        --status-code 200

    # 設置整合響應
    awslocal apigateway put-integration-response \
        --rest-api-id $API_ID \
        --resource-id $RESOURCE_ID \
        --http-method GET \
        --status-code 200
done

# 部署 API
awslocal apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name dev

echo "API Gateway created successfully."
echo ""
echo "🎉 CQRS Architecture Setup Complete! (Docker Version)"
echo "=================================================="
echo "📊 Architecture:"
echo "Command Table (Write) → DynamoDB Stream → Stream Processor Lambda → Query Table (Read)"
echo ""
echo "🐳 Lambda Deployment Method: Docker Containers"
echo ""
echo "📋 Tables:"
echo "- Command Table: command-records (寫入側)"
echo "- Query Table: notification-records (讀取側)"
echo "- Stream ARN: $STREAM_ARN"
echo ""
echo "🔗 API Gateway:"
echo "- API ID: $API_ID"
echo "- Endpoint: http://localhost:4566/restapis/$API_ID/dev/_user_request_"
echo ""
echo "🧪 Test Commands:"
echo "curl \"http://localhost:4566/restapis/$API_ID/dev/_user_request_/user?user_id=test_user_001\""
echo "curl \"http://localhost:4566/restapis/$API_ID/dev/_user_request_/marketing?marketing_id=campaign_2024_new_year\""
echo "curl \"http://localhost:4566/restapis/$API_ID/dev/_user_request_/tx?transaction_id=txn_001\""
echo "curl \"http://localhost:4566/restapis/$API_ID/dev/_user_request_/fail?transaction_id=tx_002\""
echo ""
echo "LocalStack Docker initialization completed!"
