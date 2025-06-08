#!/bin/bash

# ECS Fargate 部署腳本
# 用於部署 Query Service 到 AWS ECS Fargate

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置變數
AWS_REGION=${AWS_REGION:-"ap-southeast-1"}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID:-""}
SERVICE_NAME="query-service"
ECR_REPOSITORY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${SERVICE_NAME}"
DOCKERFILE_PATH="query-service/eks_handler/Dockerfile"
BUILD_CONTEXT="query-service/eks_handler"

# 函數定義
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "檢查部署前置條件..."

    # 檢查 AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI 未安裝"
        exit 1
    fi

    # 檢查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安裝"
        exit 1
    fi

    # 檢查 Terraform
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform 未安裝"
        exit 1
    fi

    # 檢查 AWS 帳號 ID
    if [ -z "$AWS_ACCOUNT_ID" ]; then
        AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        if [ -z "$AWS_ACCOUNT_ID" ]; then
            log_error "無法取得 AWS 帳號 ID"
            exit 1
        fi
    fi

    log_success "前置條件檢查完成"
    log_info "AWS 帳號 ID: $AWS_ACCOUNT_ID"
    log_info "AWS 區域: $AWS_REGION"
}

create_ecr_repository() {
    log_info "檢查/創建 ECR Repository..."

    # 檢查 ECR Repository 是否存在
    if aws ecr describe-repositories --repository-names $SERVICE_NAME --region $AWS_REGION &> /dev/null; then
        log_info "ECR Repository 已存在: $SERVICE_NAME"
    else
        log_info "創建 ECR Repository: $SERVICE_NAME"
        aws ecr create-repository \
            --repository-name $SERVICE_NAME \
            --region $AWS_REGION \
            --image-scanning-configuration scanOnPush=true
        log_success "ECR Repository 創建完成"
    fi
}

build_and_push_image() {
    log_info "構建並推送 Docker 映像..."

    # 登入 ECR
    log_info "登入 ECR..."
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY

    # 構建映像
    log_info "構建 Docker 映像..."
    docker build -t $SERVICE_NAME:latest -f $DOCKERFILE_PATH $BUILD_CONTEXT

    # 標記映像
    docker tag $SERVICE_NAME:latest $ECR_REPOSITORY:latest
    docker tag $SERVICE_NAME:latest $ECR_REPOSITORY:$(date +%Y%m%d-%H%M%S)

    # 推送映像
    log_info "推送映像到 ECR..."
    docker push $ECR_REPOSITORY:latest
    docker push $ECR_REPOSITORY:$(date +%Y%m%d-%H%M%S)

    log_success "映像推送完成"
}

deploy_infrastructure() {
    log_info "部署基礎設施..."

    cd query-service/infra/terraform

    # 初始化 Terraform
    log_info "初始化 Terraform..."
    terraform init

    # 規劃部署
    log_info "規劃 Terraform 部署..."
    terraform plan \
        -var="aws_region=$AWS_REGION" \
        -var="account_id=$AWS_ACCOUNT_ID" \
        -var="vpc_id=$VPC_ID" \
        -var="private_subnet_ids=[\"$PRIVATE_SUBNET_1\",\"$PRIVATE_SUBNET_2\"]"

    # 確認部署
    read -p "是否繼續部署基礎設施? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "開始部署基礎設施..."
        terraform apply \
            -var="aws_region=$AWS_REGION" \
            -var="account_id=$AWS_ACCOUNT_ID" \
            -var="vpc_id=$VPC_ID" \
            -var="private_subnet_ids=[\"$PRIVATE_SUBNET_1\",\"$PRIVATE_SUBNET_2\"]" \
            -auto-approve
        log_success "基礎設施部署完成"
    else
        log_warning "取消基礎設施部署"
        exit 0
    fi

    cd ../../..
}

update_ecs_service() {
    log_info "更新 ECS 服務..."

    # 強制新部署
    aws ecs update-service \
        --cluster "${SERVICE_NAME}-cluster" \
        --service $SERVICE_NAME \
        --force-new-deployment \
        --region $AWS_REGION

    log_info "等待服務更新完成..."
    aws ecs wait services-stable \
        --cluster "${SERVICE_NAME}-cluster" \
        --services $SERVICE_NAME \
        --region $AWS_REGION

    log_success "ECS 服務更新完成"
}

verify_deployment() {
    log_info "驗證部署狀態..."

    # 檢查 ECS 服務狀態
    SERVICE_STATUS=$(aws ecs describe-services \
        --cluster "${SERVICE_NAME}-cluster" \
        --services $SERVICE_NAME \
        --region $AWS_REGION \
        --query 'services[0].status' \
        --output text)

    if [ "$SERVICE_STATUS" = "ACTIVE" ]; then
        log_success "ECS 服務狀態: $SERVICE_STATUS"
    else
        log_error "ECS 服務狀態異常: $SERVICE_STATUS"
        exit 1
    fi

    # 檢查任務健康狀態
    RUNNING_COUNT=$(aws ecs describe-services \
        --cluster "${SERVICE_NAME}-cluster" \
        --services $SERVICE_NAME \
        --region $AWS_REGION \
        --query 'services[0].runningCount' \
        --output text)

    DESIRED_COUNT=$(aws ecs describe-services \
        --cluster "${SERVICE_NAME}-cluster" \
        --services $SERVICE_NAME \
        --region $AWS_REGION \
        --query 'services[0].desiredCount' \
        --output text)

    log_info "運行中任務數: $RUNNING_COUNT/$DESIRED_COUNT"

    if [ "$RUNNING_COUNT" -eq "$DESIRED_COUNT" ]; then
        log_success "所有任務運行正常"
    else
        log_warning "任務數量不匹配，可能仍在部署中"
    fi
}

show_deployment_info() {
    log_info "部署資訊:"
    echo "=================================="
    echo "服務名稱: $SERVICE_NAME"
    echo "AWS 區域: $AWS_REGION"
    echo "ECR Repository: $ECR_REPOSITORY"
    echo "ECS Cluster: ${SERVICE_NAME}-cluster"
    echo "=================================="

    # 取得 API Gateway URL
    if command -v terraform &> /dev/null; then
        cd query-service/infra/terraform
        API_GATEWAY_URL=$(terraform output -raw internal_api_gateway_url 2>/dev/null || echo "未部署")
        ALB_DNS=$(terraform output -raw load_balancer_dns_name 2>/dev/null || echo "未部署")
        cd ../../..

        echo "Internal API Gateway URL: $API_GATEWAY_URL"
        echo "Load Balancer DNS: $ALB_DNS"
        echo "=================================="
    fi
}

# 主要執行流程
main() {
    log_info "開始 ECS Fargate 部署流程..."

    # 檢查必要的環境變數
    if [ -z "$VPC_ID" ] || [ -z "$PRIVATE_SUBNET_1" ] || [ -z "$PRIVATE_SUBNET_2" ]; then
        log_error "請設定必要的環境變數:"
        echo "export VPC_ID=vpc-xxxxxxxxx"
        echo "export PRIVATE_SUBNET_1=subnet-xxxxxxxxx"
        echo "export PRIVATE_SUBNET_2=subnet-yyyyyyyyy"
        exit 1
    fi

    check_prerequisites
    create_ecr_repository
    build_and_push_image
    deploy_infrastructure
    update_ecs_service
    verify_deployment
    show_deployment_info

    log_success "ECS Fargate 部署完成！"
}

# 執行主函數
main "$@"
