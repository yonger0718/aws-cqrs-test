#!/bin/bash

# Lambda 函數構建腳本 - 正確的方式
set -e

echo "🔨 開始構建 Lambda 函數..."

# 設置基本變量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAMBDAS_DIR="$SCRIPT_DIR/../../lambdas"
BUILD_DIR="/tmp/lambda-build"
DIST_DIR="/tmp/lambda-dist"

# 清理舊的構建目錄
sudo rm -rf "$BUILD_DIR" "$DIST_DIR"
mkdir -p "$BUILD_DIR" "$DIST_DIR"

# Lambda 函數列表
LAMBDA_FUNCTIONS=("stream_processor_lambda" "query_lambda" "query_result_lambda")

# 構建每個 Lambda 函數
for FUNCTION_NAME in "${LAMBDA_FUNCTIONS[@]}"; do
    echo "📦 構建 $FUNCTION_NAME..."

    # 創建函數特定的構建目錄
    FUNCTION_BUILD_DIR="$BUILD_DIR/$FUNCTION_NAME"
    mkdir -p "$FUNCTION_BUILD_DIR"

    # 複製源代碼（排除不必要的文件）
    rsync -av \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude '*.pyo' \
        --exclude 'test_*.py' \
        --exclude '*_test.py' \
        --exclude 'tests/' \
        --exclude '.pytest_cache/' \
        --exclude 'requirements-test.txt' \
        --exclude 'pytest.ini' \
        "$LAMBDAS_DIR/$FUNCTION_NAME/" "$FUNCTION_BUILD_DIR/"

    # 安裝依賴（在構建目錄中）
    if [ -f "$FUNCTION_BUILD_DIR/requirements.txt" ]; then
        echo "📥 安裝依賴 for $FUNCTION_NAME..."

        # 檢查是否有 Docker 可用，如果有則使用容器構建
        if command -v docker &> /dev/null && docker info &> /dev/null; then
            echo "使用 Docker 容器構建..."
            docker run --rm \
                -v "$FUNCTION_BUILD_DIR":/var/task \
                -w /var/task \
                --entrypoint="" \
                public.ecr.aws/lambda/python:3.12 \
                pip install --no-cache-dir -r requirements.txt -t .
        else
            echo "使用本地 Python 環境構建..."
            cd "$FUNCTION_BUILD_DIR"
            pip install --no-cache-dir -r requirements.txt -t .
            cd -
        fi

        # 清理不必要的文件
        find "$FUNCTION_BUILD_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find "$FUNCTION_BUILD_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
        find "$FUNCTION_BUILD_DIR" -type f -name "*.pyo" -delete 2>/dev/null || true
        find "$FUNCTION_BUILD_DIR" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
        find "$FUNCTION_BUILD_DIR" -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    fi

    # 創建部署包
    echo "📁 打包 $FUNCTION_NAME..."
    cd "$FUNCTION_BUILD_DIR"
    zip -r "$DIST_DIR/$FUNCTION_NAME.zip" . -x "*.git*" "*.DS_Store*"

    echo "✅ $FUNCTION_NAME 構建完成: $DIST_DIR/$FUNCTION_NAME.zip"
done

echo "🎉 所有 Lambda 函數構建完成！"
echo "構建產物位於: $DIST_DIR"
ls -la "$DIST_DIR"
