#!/bin/bash

echo "Starting LocalStack initialization..."

# 設置區域環境變數
export AWS_DEFAULT_REGION=ap-southeast-1
export AWS_REGION=ap-southeast-1

echo "Using region: $AWS_DEFAULT_REGION"

# 等待 LocalStack 準備就緒
echo "Waiting for LocalStack to be ready..."
awslocal dynamodb list-tables
while [ $? -ne 0 ]; do
    echo "LocalStack is not ready yet, waiting..."
    sleep 2
    awslocal dynamodb list-tables
done

echo "LocalStack is ready. Creating DynamoDB tables..."

# 創建寫入表（Command Side）- 支援 DynamoDB Stream
awslocal dynamodb create-table \
    --table-name command-records \
    --attribute-definitions \
        AttributeName=transaction_id,AttributeType=S \
        AttributeName=created_at,AttributeType=N \
    --key-schema \
        AttributeName=transaction_id,KeyType=HASH \
        AttributeName=created_at,KeyType=RANGE \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES

echo "Command table created successfully."

# 創建讀取表（Query Side）
awslocal dynamodb create-table \
    --table-name notification-records \
    --attribute-definitions \
        AttributeName=user_id,AttributeType=S \
        AttributeName=created_at,AttributeType=N \
        AttributeName=marketing_id,AttributeType=S \
        AttributeName=transaction_id,AttributeType=S \
        AttributeName=status,AttributeType=S \
    --key-schema \
        AttributeName=user_id,KeyType=HASH \
        AttributeName=created_at,KeyType=RANGE \
    --global-secondary-indexes \
        '[
            {
                "IndexName": "marketing_id-index",
                "KeySchema": [
                    {"AttributeName": "marketing_id", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}
            },
            {
                "IndexName": "transaction_id-status-index",
                "KeySchema": [
                    {"AttributeName": "transaction_id", "KeyType": "HASH"},
                    {"AttributeName": "status", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}
            }
        ]' \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5

echo "Query table created successfully."

# 等待表創建完成並獲取 Stream ARN
echo "Waiting for table to be active and getting stream ARN..."
sleep 5

STREAM_ARN=$(awslocal dynamodb describe-table \
    --table-name command-records \
    --query 'Table.LatestStreamArn' \
    --output text)

echo "Stream ARN: $STREAM_ARN"

# 插入測試資料到寫入表（Command Side）
echo "Inserting test data to command table..."

# 測試資料 1: 用戶 test_user_001
awslocal dynamodb put-item \
    --table-name command-records \
    --item '{
        "transaction_id": {"S": "tx_001"},
        "created_at": {"N": "1704038400000"},
        "user_id": {"S": "test_user_001"},
        "marketing_id": {"S": "campaign_2024_new_year"},
        "notification_title": {"S": "新年快樂！"},
        "status": {"S": "DELIVERED"},
        "platform": {"S": "IOS"},
        "device_token": {"S": "ios_token_123"},
        "payload": {"S": "{\"title\": \"新年快樂！\", \"body\": \"祝您新年快樂，萬事如意！\"}"}
    }'

# 測試資料 2: 失敗的推播
awslocal dynamodb put-item \
    --table-name command-records \
    --item '{
        "transaction_id": {"S": "tx_002"},
        "created_at": {"N": "1704038500000"},
        "user_id": {"S": "test_user_002"},
        "marketing_id": {"S": "campaign_2024_new_year"},
        "notification_title": {"S": "新年優惠"},
        "status": {"S": "FAILED"},
        "platform": {"S": "ANDROID"},
        "device_token": {"S": "android_token_456"},
        "error_msg": {"S": "Device token invalid"},
        "payload": {"S": "{\"title\": \"新年優惠\", \"body\": \"限時優惠活動開始！\"}"}
    }'

# 測試資料 3: 最近的推播
awslocal dynamodb put-item \
    --table-name command-records \
    --item '{
        "transaction_id": {"S": "tx_003"},
        "created_at": {"N": "1704124800000"},
        "user_id": {"S": "test_user_001"},
        "marketing_id": {"S": "campaign_2024_spring"},
        "notification_title": {"S": "春季促銷開始！"},
        "status": {"S": "SENT"},
        "platform": {"S": "WEBPUSH"},
        "device_token": {"S": "web_token_789"},
        "payload": {"S": "{\"title\": \"春季促銷\", \"body\": \"春季大促銷活動現在開始！\"}"}
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
        "payload": {"S": "{\"title\": \"限時優惠\", \"body\": \"最後機會，不要錯過！\"}"}
    }'

echo "Test data inserted to command table successfully."

# 創建 Lambda 函數
echo "Creating Lambda functions..."

# 使用簡化的內聯構建方式
echo "Building and deploying Lambda functions..."

# 創建環境變數文件
echo '{"Variables":{"LOCALSTACK_HOSTNAME":"localstack"}}' > /tmp/env.json
echo '{"Variables":{"LOCALSTACK_HOSTNAME":"localstack","EKS_HANDLER_URL":"http://eks-handler:8000"}}' > /tmp/query_env.json

cd /opt/code/lambdas

# 構建並部署 stream_processor_lambda
echo "部署 stream_processor_lambda..."
mkdir -p /tmp/lambda-build/stream_processor_lambda
cp -r stream_processor_lambda/* /tmp/lambda-build/stream_processor_lambda/
cd /tmp/lambda-build/stream_processor_lambda
pip install --no-cache-dir -r requirements.txt -t . > /dev/null 2>&1
find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
zip -r /tmp/stream_processor_lambda.zip . > /dev/null
awslocal lambda create-function \
    --function-name query-service-stream_processor_lambda \
    --runtime python3.12 \
    --handler app.lambda_handler \
    --zip-file fileb:///tmp/stream_processor_lambda.zip \
    --role arn:aws:iam::000000000000:role/lambda-role \
    --environment file:///tmp/env.json

# 構建並部署 query_lambda
echo "部署 query_lambda..."
cd /opt/code/lambdas
mkdir -p /tmp/lambda-build/query_lambda
cp -r query_lambda/* /tmp/lambda-build/query_lambda/
cd /tmp/lambda-build/query_lambda
pip install --no-cache-dir -r requirements.txt -t . > /dev/null 2>&1
find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
zip -r /tmp/query_lambda.zip . > /dev/null
awslocal lambda create-function \
    --function-name query-service-query_lambda \
    --runtime python3.12 \
    --handler app.lambda_handler \
    --zip-file fileb:///tmp/query_lambda.zip \
    --role arn:aws:iam::000000000000:role/lambda-role \
    --environment file:///tmp/query_env.json

# 構建並部署 query_result_lambda
echo "部署 query_result_lambda..."
cd /opt/code/lambdas
mkdir -p /tmp/lambda-build/query_result_lambda
cp -r query_result_lambda/* /tmp/lambda-build/query_result_lambda/
cd /tmp/lambda-build/query_result_lambda
pip install --no-cache-dir -r requirements.txt -t . > /dev/null 2>&1
find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
zip -r /tmp/query_result_lambda.zip . > /dev/null
awslocal lambda create-function \
    --function-name query-service-query_result_lambda \
    --runtime python3.12 \
    --handler app.lambda_handler \
    --zip-file fileb:///tmp/query_result_lambda.zip \
    --role arn:aws:iam::000000000000:role/lambda-role \
    --environment file:///tmp/env.json

echo "Lambda functions created successfully."

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

# 創建 /fail 資源
FAIL_ID=$(awslocal apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_ID \
    --path-part "fail" \
    --query 'id' --output text)

# 為每個資源創建 GET 方法並整合 Lambda
for RESOURCE_ID in $USER_ID $MARKETING_ID $FAIL_ID; do
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
echo "🎉 CQRS Architecture Setup Complete!"
echo "=================================================="
echo "📊 Architecture:"
echo "Command Table (Write) → DynamoDB Stream → Stream Processor Lambda → Query Table (Read)"
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
echo "curl \"http://localhost:4566/restapis/$API_ID/dev/_user_request_/fail?transaction_id=tx_002\""
echo ""
echo "LocalStack initialization completed!"
