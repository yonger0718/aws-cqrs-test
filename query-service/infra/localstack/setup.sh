#!/bin/bash

# LocalStack Query Service Setup Script
# Version: v4 - Optimized for transaction_id based queries only

set -e

echo "🚀 Setting up Query Service in LocalStack..."

# Configuration
AWS_REGION=${AWS_REGION:-ap-southeast-1}
LOCALSTACK_ENDPOINT=${LOCALSTACK_ENDPOINT:-http://localhost:4566}
DYNAMODB_TABLE_NAME=${DYNAMODB_TABLE_NAME:-notification-records}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}➜ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Wait for LocalStack to be ready
wait_for_localstack() {
    print_step "Waiting for LocalStack to be ready..."

    MAX_ATTEMPTS=30
    ATTEMPT=1

    while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
        if curl -s "${LOCALSTACK_ENDPOINT}/health" > /dev/null 2>&1; then
            print_success "LocalStack is ready!"
            return 0
        fi

        echo -e "${YELLOW}Attempt $ATTEMPT/$MAX_ATTEMPTS: LocalStack not ready yet...${NC}"
        sleep 2
        ATTEMPT=$((ATTEMPT + 1))
    done

    print_error "LocalStack failed to start within expected time"
    exit 1
}

# Create DynamoDB table
create_dynamodb_table() {
    print_step "Creating DynamoDB table: $DYNAMODB_TABLE_NAME"

    aws dynamodb create-table \
        --endpoint-url $LOCALSTACK_ENDPOINT \
        --region $AWS_REGION \
        --table-name $DYNAMODB_TABLE_NAME \
        --attribute-definitions \
            AttributeName=transaction_id,AttributeType=S \
            AttributeName=created_at,AttributeType=N \
        --key-schema \
            AttributeName=transaction_id,KeyType=HASH \
            AttributeName=created_at,KeyType=RANGE \
        --billing-mode PAY_PER_REQUEST \
        --no-cli-pager > /dev/null 2>&1 || true

    print_success "DynamoDB table created/exists"
}

# Insert test data
insert_test_data() {
    print_step "Inserting test data into DynamoDB table..."

    # Test data with correct schema structure
    test_items=(
        '{
            "transaction_id": {"S": "txn-test-001"},
            "created_at": {"N": "1640995200"},
            "token": {"S": "test-device-token-001"},
            "platform": {"S": "IOS"},
            "notification_title": {"S": "Payment Confirmation"},
            "notification_body": {"S": "Your payment of $50.00 has been processed successfully"},
            "status": {"S": "DELIVERED"},
            "send_ts": {"N": "1640995200"},
            "delivered_ts": {"N": "1640995210"},
            "ap_id": {"S": "payment-service"}
        }'
        '{
            "transaction_id": {"S": "txn-test-002"},
            "created_at": {"N": "1640995300"},
            "token": {"S": "test-device-token-002"},
            "platform": {"S": "ANDROID"},
            "notification_title": {"S": "Order Update"},
            "notification_body": {"S": "Your order has been shipped"},
            "status": {"S": "SENT"},
            "send_ts": {"N": "1640995300"},
            "ap_id": {"S": "ecommerce-service"}
        }'
        '{
            "transaction_id": {"S": "txn-failed-001"},
            "created_at": {"N": "1640995400"},
            "token": {"S": "invalid-device-token"},
            "platform": {"S": "IOS"},
            "notification_title": {"S": "Account Alert"},
            "notification_body": {"S": "Suspicious activity detected"},
            "status": {"S": "FAILED"},
            "send_ts": {"N": "1640995400"},
            "failed_ts": {"N": "1640995410"},
            "ap_id": {"S": "security-service"}
        }'
        '{
            "transaction_id": {"S": "txn-failed-002"},
            "created_at": {"N": "1640995500"},
            "token": {"S": "expired-device-token"},
            "platform": {"S": "ANDROID"},
            "notification_title": {"S": "Login Notification"},
            "notification_body": {"S": "New login detected"},
            "status": {"S": "FAILED"},
            "send_ts": {"N": "1640995500"},
            "failed_ts": {"N": "1640995510"},
            "ap_id": {"S": "auth-service"}
        }'
    )

    for item in "${test_items[@]}"; do
        aws dynamodb put-item \
            --endpoint-url $LOCALSTACK_ENDPOINT \
            --region $AWS_REGION \
            --table-name $DYNAMODB_TABLE_NAME \
            --item "$item" \
            --no-cli-pager > /dev/null 2>&1
    done

    print_success "Test data inserted successfully"
}

# Test Lambda functions (if available)
test_lambda_functions() {
    print_step "Testing Lambda functions (if available)..."

    # Check if Lambda functions exist
    QUERY_LAMBDA_NAME="query-lambda"
    QUERY_RESULT_LAMBDA_NAME="query-result-lambda"

    # Test Query Lambda
    if aws lambda get-function --endpoint-url $LOCALSTACK_ENDPOINT --region $AWS_REGION --function-name $QUERY_LAMBDA_NAME > /dev/null 2>&1; then
        print_step "Testing Query Lambda..."

        # Test transaction query
        aws lambda invoke \
            --endpoint-url $LOCALSTACK_ENDPOINT \
            --region $AWS_REGION \
            --function-name $QUERY_LAMBDA_NAME \
            --payload '{"path": "/tx", "queryStringParameters": {"transaction_id": "txn-test-001"}}' \
            --no-cli-pager \
            /tmp/lambda-response.json > /dev/null 2>&1

        print_success "Query Lambda test completed"
    else
        print_warning "Query Lambda not found - skipping test"
    fi

    # Test Query Result Lambda
    if aws lambda get-function --endpoint-url $LOCALSTACK_ENDPOINT --region $AWS_REGION --function-name $QUERY_RESULT_LAMBDA_NAME > /dev/null 2>&1; then
        print_step "Testing Query Result Lambda..."

        # Test transaction query
        aws lambda invoke \
            --endpoint-url $LOCALSTACK_ENDPOINT \
            --region $AWS_REGION \
            --function-name $QUERY_RESULT_LAMBDA_NAME \
            --payload '{"query_type": "tx", "transaction_id": "txn-test-001"}' \
            --no-cli-pager \
            /tmp/lambda-result-response.json > /dev/null 2>&1

        print_success "Query Result Lambda test completed"
    else
        print_warning "Query Result Lambda not found - skipping test"
    fi
}

# Verify setup
verify_setup() {
    print_step "Verifying setup..."

    # Check table exists and has data
    ITEM_COUNT=$(aws dynamodb scan \
        --endpoint-url $LOCALSTACK_ENDPOINT \
        --region $AWS_REGION \
        --table-name $DYNAMODB_TABLE_NAME \
        --select COUNT \
        --no-cli-pager \
        --output text \
        --query 'Count' 2>/dev/null || echo "0")

    if [ "$ITEM_COUNT" -gt 0 ]; then
        print_success "DynamoDB table has $ITEM_COUNT items"
    else
        print_warning "DynamoDB table appears to be empty"
    fi

    # Test sample queries
    print_step "Testing sample queries..."

    # Test transaction query using scan (no GSI available)
    echo "Testing transaction query using scan (txn-test-001):"
    aws dynamodb scan \
        --endpoint-url $LOCALSTACK_ENDPOINT \
        --region $AWS_REGION \
        --table-name $DYNAMODB_TABLE_NAME \
        --filter-expression "transaction_id = :txn_id" \
        --expression-attribute-values '{":txn_id": {"S": "txn-test-001"}}' \
        --no-cli-pager \
        --output table 2>/dev/null || print_warning "Transaction query test failed"

    # Test failed status query
    echo "Testing failed notifications scan:"
    aws dynamodb scan \
        --endpoint-url $LOCALSTACK_ENDPOINT \
        --region $AWS_REGION \
        --table-name $DYNAMODB_TABLE_NAME \
        --filter-expression "#status = :failed_status" \
        --expression-attribute-names '{"#status": "status"}' \
        --expression-attribute-values '{":failed_status": {"S": "FAILED"}}' \
        --no-cli-pager \
        --output table 2>/dev/null || print_warning "Failed query test failed"
}

# Main execution
main() {
    echo "================================================="
    echo "   Query Service LocalStack Setup (v4)"
    echo "================================================="
    echo ""

    wait_for_localstack
    create_dynamodb_table
    insert_test_data
    test_lambda_functions
    verify_setup

    echo ""
    echo "================================================="
    print_success "Query Service setup completed successfully!"
    echo "================================================="
    echo ""
    echo "Available endpoints:"
    echo "  • Transaction Query: GET /tx?transaction_id=<id>"
    echo "  • Failed Query: GET /fail?transaction_id=<id>"
    echo ""
    echo "Test commands:"
    echo "  • Query specific transaction:"
    echo "    curl 'http://localhost:4566/tx?transaction_id=txn-test-001'"
    echo ""
    echo "  • Query failed transaction:"
    echo "    curl 'http://localhost:4566/fail?transaction_id=txn-failed-001'"
    echo ""
    echo "DynamoDB direct access:"
    echo "  aws dynamodb scan --endpoint-url http://localhost:4566 --table-name $DYNAMODB_TABLE_NAME"
    echo ""
}

# Run main function
main "$@"
