# 環境變量設置指南

## 概述

本項目提供了統一的環境變量設置腳本，確保所有測試腳本使用一致的配置。

## 環境變量腳本

### `scripts/setup_env.sh`

這個腳本設置了所有必要的環境變量：

```bash
# AWS 憑證配置 (LocalStack 測試環境)
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

# LocalStack 端點配置
export LOCALSTACK_ENDPOINT=http://localhost:4566

# EKS Handler 端點配置
export EKS_HANDLER_ENDPOINT=http://localhost:8000

# API Gateway 配置
export API_GATEWAY_ENDPOINT=http://localhost:4566
```

## 使用方法

### 1. 手動載入環境變量

在任何終端中：

```bash
source scripts/setup_env.sh
```

### 2. 自動載入（推薦）

所有測試腳本已經自動載入環境變量：

- `scripts/testing/test_full_flow.sh`
- `scripts/testing/quick_test.sh`
- `scripts/fix_api_gateway.sh`
- `scripts/deploy_api_gateway_proxy.sh`

### 3. 驗證環境變量

檢查環境變量是否正確設置：

```bash
echo "AWS Endpoint: $LOCALSTACK_ENDPOINT"
echo "EKS Handler: $EKS_HANDLER_ENDPOINT"
echo "AWS Region: $AWS_DEFAULT_REGION"
```

## 自動化腳本

### 測試腳本

```bash
# 完整流程測試
./scripts/testing/test_full_flow.sh

# 快速測試
./scripts/testing/quick_test.sh
```

### 部署腳本

```bash
# 部署 API Gateway 代理
./scripts/deploy_api_gateway_proxy.sh

# 修復 API Gateway
./scripts/fix_api_gateway.sh
```

## 故障排除

### 常見問題

1. **環境變量未生效**

   ```bash
   # 解決方案：使用 source 而不是直接執行
   source scripts/setup_env.sh  # ✓ 正確
   ./scripts/setup_env.sh       # ✗ 錯誤
   ```

2. **無法連接到 LocalStack**

   ```bash
   # 檢查 LocalStack 是否運行
   curl -s $LOCALSTACK_ENDPOINT/_localstack/health
   ```

3. **EKS Handler 連接失敗**

   ```bash
   # 檢查 EKS Handler 健康狀況
   curl -s $EKS_HANDLER_ENDPOINT/health
   ```

### 重置環境

如果需要重置環境變量：

```bash
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_DEFAULT_REGION
unset LOCALSTACK_ENDPOINT EKS_HANDLER_ENDPOINT API_GATEWAY_ENDPOINT
source scripts/setup_env.sh
```

## 開發指南

### 添加新的環境變量

1. 編輯 `scripts/setup_env.sh`
2. 在需要的腳本中載入環境變量
3. 更新此文檔

### 腳本最佳實踐

```bash
#!/bin/bash

# 載入環境變量設置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$PROJECT_ROOT/scripts/setup_env.sh"

# 使用環境變量
AWS_ENDPOINT="$LOCALSTACK_ENDPOINT"
```

這種方式確保：

- 環境變量集中管理
- 腳本可從任何位置執行
- 配置一致性

## 相關文檔

- [CQRS 架構指南](../architecture/cqrs-hexagonal-design.md)
- [API Gateway 配置](api-gateway-setup.md)
- [測試指南](../testing/testing-guide.md)
