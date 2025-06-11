# AWS CQRS + Hexagonal Architecture 文檔

歡迎使用 AWS CQRS + 六邊形架構通知系統的完整文檔。

## 📚 文檔目錄

### 🏗️ 架構設計
- [CQRS + 六邊形架構設計 V4](architecture/cqrs-hexagonal-design-v4.md) ⭐ **最新版本**
- [CQRS + 六邊形架構設計 (舊版)](architecture/cqrs-hexagonal-design.md) ⚠️ **已廢棄**

### 📡 API 文檔
- [API 變更說明 V4](api/api-changes-v4.md) ⭐ **最新版本**
- [API 變更說明 V3](api/api-changes-v3.md) ⚠️ **已廢棄**

### 🚀 部署指南
- [Lambda Docker 部署指南](deployment/lambda-docker-deployment.md)

### 🛠️ 開發指南
- [CI/CD 與 Pre-commit 一致性](development/ci-precommit-consistency.md)
- [Pre-commit CI 一致性](development/pre-commit-ci-consistency.md)

### 🧪 測試指南
- [驗證指南](testing/VERIFICATION_GUIDE.md)

### 📄 其他資源
- [專案總結](project/)
- [遷移指南](migration/)
- [使用指南](guides/)

## 🔧 腳本工具

詳細的腳本使用說明請參考 [Scripts 目錄](../scripts/README.md)

### 快速開始
```bash
# 設定開發環境
./scripts/development/setup_env.sh

# 快速測試
./scripts/testing/quick_test.sh

# 部署服務
./scripts/deployment/restart_services.sh
```

## 📋 版本說明

### V4 (目前版本) ⭐
- 簡化的 Transaction 導向 API
- Internal API Gateway 整合
- 統一的 NotificationRecord 模型
- ECS + HTTP 通信模式

### V3 (已廢棄) ⚠️
- 多維度查詢 API
- 複雜的多端點設計
- 直接 Lambda 調用

## 🚀 快速導航

### 新用戶
1. 閱讀 [架構設計 V4](architecture/cqrs-hexagonal-design-v4.md)
2. 查看 [API 文檔 V4](api/api-changes-v4.md)
3. 運行 [快速測試](../scripts/testing/quick_test.sh)

### 開發者
1. 檢查 [開發環境設定](development/)
2. 閱讀 [測試指南](testing/)
3. 使用 [開發腳本](../scripts/development/)

### 部署人員
1. 參考 [部署指南](deployment/)
2. 使用 [部署腳本](../scripts/deployment/)
3. 執行 [驗證腳本](../scripts/verification/)

## 🔍 問題排除

如果遇到問題，請按以下順序檢查：

1. **環境設定**: [開發指南](development/)
2. **測試運行**: [測試指南](testing/)
3. **一致性檢查**: [CI/CD 一致性](development/ci-precommit-consistency.md)
4. **腳本工具**: [Scripts 目錄](../scripts/README.md)

## 📞 支援

如有問題請：
1. 檢查相關文檔
2. 運行診斷腳本
3. 查看 GitHub Issues
4. 聯絡開發團隊
