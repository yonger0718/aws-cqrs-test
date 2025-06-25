# AWS CQRS + Hexagonal Architecture 文檔

歡迎使用 AWS CQRS + 六邊形架構通知系統的完整文檔。

## 📚 文檔目錄

### 🏗️ 架構設計
- [CQRS + 六邊形架構設計 V4](architecture/cqrs-hexagonal-design-v4.md) ⭐ **最新版本**
- [ECS 遷移指南](architecture/ecs-migration-guide.md)

### 📡 API 文檔
- [API 變更說明 V4.2](api/api-changes-v4.2.md) 🆕 **最新版本 - 穩定性修復**
- [API 變更說明 V4.1](api/api-changes-v4.1.md) ✅ SNS 查詢功能
- [API 變更說明 V4](api/api-changes-v4.md) ✅ 核心功能

### 🚀 部署指南
- [Lambda Docker 部署指南](deployment/lambda-docker-deployment.md)
- [環境設定指南](deployment/environment-setup.md)
- [IAM 角色設定指南](deployment/iam-roles-setup-guide.md)

### 🛠️ 開發指南
- [CI/CD 與 Pre-commit 一致性](development/ci-precommit-consistency.md)

### 🧪 測試指南
- [驗證指南](testing/VERIFICATION_GUIDE.md)
- [快速測試指南](testing/QUICK_TEST_GUIDE.md)

### 📖 使用指南
- [最終使用指南](guides/FINAL_USAGE_GUIDE.md) ⭐ **推薦閱讀**
- [查詢工具 README](guides/README_QUERY_TOOLS.md)

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

# 系統驗證
./scripts/verification/verify_system.sh
```

## 📋 版本說明

### V4.2 (目前版本) 🆕
- **穩定性修復**：時間戳處理和資料驗證
- **功能增強**：可選參數支援和 UTC+8 時區
- **架構改進**：統一 HTTP GET 語義
- **品質提升**：錯誤處理和測試覆蓋

### V4.1 ✅
- **SNS 查詢功能**：新增 `/sns` 端點
- **Schema 擴展**：支援 `sns_id` 欄位
- **測試完整性**：完整 SNS 查詢測試

### V4.0 ✅
- **Transaction 導向 API**：簡化的查詢介面
- **Internal API Gateway**：統一的後端整合
- **ECS + HTTP 通信**：現代化的服務架構

## 🚀 快速導航

### 新用戶
1. 閱讀 [最終使用指南](guides/FINAL_USAGE_GUIDE.md) ⭐
2. 查看 [API 文檔 V4.2](api/api-changes-v4.2.md) 🆕
3. 運行 [快速測試](../scripts/testing/quick_test.sh)

### 開發者
1. 檢查 [開發環境設定](deployment/environment-setup.md)
2. 閱讀 [測試指南](testing/VERIFICATION_GUIDE.md)
3. 使用 [開發腳本](../scripts/development/)

### 部署人員
1. 參考 [部署指南](deployment/)
2. 使用 [部署腳本](../scripts/deployment/)
3. 執行 [驗證腳本](../scripts/verification/)

## 🆕 V4.2 重點功能

### 🔧 穩定性修復
- **時間戳處理**：解決排序崩潰問題
- **資料驗證**：適應真實資料格式
- **錯誤處理**：改進的日誌和錯誤回應

### ✨ 功能增強
- **可選查詢**：`/tx` 支援可選 `transaction_id`
- **筆數控制**：`limit` 參數 (1-100，預設30)
- **時區顯示**：UTC+8 格式時間字串

### 🏗️ 架構改進
- **HTTP 語義**：統一使用 GET 方法查詢
- **方法分離**：專門化的 API 調用方法
- **參數清理**：移除 `query_type` 污染

## 📊 API 端點總覽

| 端點 | 方法 | 功能 | 狀態 | 版本 |
|------|------|------|------|------|
| `/tx` | GET | 交易查詢 (可選參數) | ⭐ 推薦 | V4.2 |
| `/fail` | GET | 失敗記錄查詢 | ✅ 穩定 | V4.0+ |
| `/sns` | GET | SNS 查詢 | ✅ 穩定 | V4.1+ |
| `/query/transaction` | POST | 交易查詢 (Legacy) | ⚠️ 棄用 | V4.0+ |
| `/query/fail` | POST | 失敗查詢 (Legacy) | ⚠️ 棄用 | V4.0+ |
| `/query/sns` | POST | SNS 查詢 (Legacy) | ⚠️ 棄用 | V4.1+ |

## 🔍 問題排除

如果遇到問題，請按以下順序檢查：

1. **API 問題**: [API 文檔 V4.2](api/api-changes-v4.2.md)
2. **環境設定**: [環境設定指南](deployment/environment-setup.md)
3. **測試執行**: [驗證指南](testing/VERIFICATION_GUIDE.md)
4. **腳本工具**: [Scripts 目錄](../scripts/README.md)

### 常見問題修復

#### 時間戳錯誤
```bash
# V4.2 已修復時間戳處理問題
# 如仍遇到問題，請檢查資料格式
```

#### 資料驗證失敗
```bash
# V4.2 已放寬驗證限制
# platform 欄位現在是可選的
# status 欄位接受所有字串值
```

#### 查詢結果為空
```bash
# 檢查 V4.2 的新參數支援
curl "https://your-api.com/tx?limit=10"
```

## 📞 支援

如有問題請：
1. 檢查相關文檔
2. 運行診斷腳本: `./scripts/verification/verify_system.sh`
3. 查看 GitHub Issues
4. 聯絡開發團隊

## 🎯 升級建議

### 從 V4.0/4.1 升級到 V4.2
- ✅ **無需程式碼變更** - 完全向後相容
- ✅ **立即獲得穩定性修復**
- ✅ **開始使用新的時區功能**
- ✅ **逐步遷移到 GET 方法**

### 遷移路徑
1. **立即行動** - 部署 V4.2（無風險）
2. **短期** - 開始使用 GET 端點
3. **長期** - 準備 V5.0 的 breaking changes

---

**當前版本**: V4.2
**發布狀態**: ✅ 生產就緒
**下次更新**: V5.0 (移除 deprecated 功能)
