# 🔔 AWS Hexagon 通知測試專案

[![CI/CD Pipeline](https://github.com/yonger0718/aws-cqrs-test/actions/workflows/ci.yml/badge.svg)](https://github.com/yonger0718/aws-cqrs-test/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/yonger0718/aws-cqrs-test/graph/badge.svg?token=JH9SFXB4YR)](https://codecov.io/gh/yonger0718/aws-cqrs-test)
[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> **六邊形架構 + CQRS 模式** 的推播通知系統實作，使用 LocalStack 模擬 AWS 環境

## 🎯 專案概述

本專案展示了現代微服務架構的最佳實踐，實現了：

- **六邊形架構 (Hexagonal Architecture)**: 清晰的領域分離
- **CQRS 模式 (Command Query Responsibility Segregation)**: 讀寫分離
- **事件驅動架構**: DynamoDB Stream 驅動的資料同步
- **容器化部署**: Docker Compose 一鍵啟動
- **完整測試覆蓋**: 單元測試 + 整合測試

## 🏗️ 系統架構

```txt
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Command Side  │───▶│  DynamoDB    │───▶│   Query Side    │
│   (Write Path)  │    │   Stream     │    │   (Read Path)   │
└─────────────────┘    └──────────────┘    └─────────────────┘
         │                      │                      │
         ▼                      ▼                      ▼
  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
  │ command-    │      │   Stream    │      │notification-│
  │ records     │      │ Processor   │      │ records     │
  │ (Write DB)  │      │  Lambda     │      │ (Read DB)   │
  └─────────────┘      └─────────────┘      └─────────────┘
```

## 📁 專案結構

```txt
📦 aws-hexagon-notify-test/
├── 📚 docs/                          # 專案文檔
│   ├── 🧪 testing/                   # 測試指南
│   ├── 📖 guides/                    # 使用說明
│   ├── 🏗️ architecture/              # 架構文檔
│   └── 📊 project/                   # 專案總結
├── 🔧 scripts/                       # 腳本工具
│   ├── 🧪 testing/                   # 測試腳本
│   ├── 🔍 queries/                   # 查詢工具
│   ├── ✅ verification/              # 驗證腳本
│   └── 🛠️ development/               # 開發工具
└── 🚀 query-service/                 # 主要服務
    ├── eks_handler/                  # FastAPI 服務
    ├── lambdas/                      # AWS Lambda
    ├── tests/                        # 測試套件
    └── infra/                        # 基礎設施
```

## 🚀 快速開始

### ✅ **步驟一: 系統環境驗證**

```bash
# 檢查系統環境和依賴
./scripts/verification/verify_system.sh
```

### 🐳 **步驟二: 啟動服務**

```bash
# 重啟並初始化服務
./scripts/restart_services.sh
```

### ⚙️ **步驟三: 修復 API Gateway**

```bash
# 修復 API Gateway 配置 (如果需要)
./scripts/fix_api_gateway.sh
```

### 🧪 **步驟四: 執行測試**

```bash
# 快速驗證
./scripts/testing/quick_test.sh

# 完整流程測試
./scripts/testing/test_full_flow.sh
```

### 🔍 **步驟五: 查詢測試**

```bash
# 查詢測試工具
./scripts/queries/test_query.sh

# 簡化查詢工具
./scripts/queries/simple_query.sh
```

## 📋 推薦測試驗證順序

### 🎯 **完整驗證流程 (新環境/重大更改後)**

```bash
# 1. 環境準備
./scripts/verification/verify_system.sh

# 2. 服務管理
./scripts/restart_services.sh
./scripts/fix_api_gateway.sh

# 3. 基本功能驗證
./scripts/testing/quick_test.sh

# 4. 查詢功能測試
./scripts/queries/simple_query.sh --all

# 5. CQRS 流程驗證
./scripts/testing/test_full_flow.sh

# 6. Python 單元與整合測試
cd query-service
pytest tests/test_eks_handler.py -v
pytest tests/test_integration.py -v
```

### ⚡ **快速驗證 (日常開發)**

```bash
# 快速健康檢查
./scripts/testing/quick_test.sh

# 查詢功能確認
./scripts/queries/simple_query.sh --all

# Python 測試
cd query-service && pytest tests/ -v
```

**📖 詳細說明：** [測試驗證指南](./docs/testing/VERIFICATION_GUIDE.md)

## 📋 核心功能

### 🎯 **CQRS 實作**

- ✅ **命令側**: `command-records` 表 + DynamoDB Stream
- ✅ **查詢側**: `notification-records` 表 + GSI 索引
- ✅ **事件驅動**: Stream Processor 自動同步資料
- ✅ **資料轉換**: 針對查詢最佳化的資料結構

### 🔍 **查詢功能**

- 👤 **用戶查詢**: 根據 `user_id` 查詢個人推播記錄
- 📢 **活動查詢**: 根據 `marketing_id` 查詢活動推播統計
- ❌ **失敗查詢**: 根據 `transaction_id` 查詢失敗記錄

### 🧪 **測試覆蓋**

- ✅ **單元測試**: 76% 代碼覆蓋率 (9/9 通過)
- ✅ **整合測試**: 100% 通過率 (8/8 通過)
- ✅ **效能測試**: API 響應時間 < 10ms
- ✅ **並發測試**: 支援 10+ 並發請求

## 📊 測試結果

### 最新測試狀態 ✅

```txt
🧪 單元測試:    ✅ 9/9 通過 (100%)   ⏱️ 1.45s   📊 76% 覆蓋率
🔗 整合測試:    ✅ 8/8 通過 (100%)   ⏱️ 11.2s
⚡ 效能測試:    ✅ 響應時間 9.72ms
🔄 CQRS 同步:   ✅ 69.2% 同步率 (9/13)
```

## 🛠️ 技術棧

### 🖥️ **後端技術**

- **Python 3.12**: 主要開發語言 (升級自 3.9)
- **FastAPI**: 高效能 Web 框架
- **AWS Lambda**: 無伺服器函數
- **DynamoDB**: NoSQL 資料庫
- **LocalStack**: AWS 本地模擬環境

### 🧪 **測試技術**

- **pytest**: 測試框架
- **coverage**: 覆蓋率測試
- **unittest.mock**: 模擬測試
- **TestClient**: API 測試

### 🐳 **DevOps 工具**

- **Docker Compose**: 容器編排
- **Bash/Shell**: 自動化腳本
- **GitHub Actions**: CI/CD 流水線
- **pre-commit**: 代碼品質檢查

## 📚 文檔導覽

### 🎯 **新手入門**

1. 📖 [最終使用指南](./docs/guides/FINAL_USAGE_GUIDE.md) - 完整的使用說明
2. 🧪 [快速測試指南](./docs/testing/QUICK_TEST_GUIDE.md) - 5 分鐘快速驗證

### 🏗️ **架構理解**

1. 🏗️ [CQRS 成功實作](./docs/architecture/CQRS_SUCCESS.md) - 架構設計詳解
2. 📋 [查詢服務需求](./docs/architecture/query_service_requirements_v2.md) - 需求規格

### 🔧 **開發參考**

1. 🧪 [測試指南](./docs/testing/TESTING_GUIDE.md) - 完整測試說明
2. 🔍 [手動查詢指南](./docs/guides/MANUAL_QUERY_GUIDE.md) - 查詢工具使用

### 📊 **專案總結**

1. 📊 [專案開發總結](./docs/project/PROJECT_SUMMARY.md) - 開發歷程回顧
2. 🎉 [成功實作總結](./docs/project/SUCCESS_SUMMARY.md) - 成果展示

## 🔧 腳本工具

### 🧪 **測試工具**

```bash
./scripts/testing/quick_test.sh       # 快速測試
./scripts/testing/test_full_flow.sh   # 完整流程測試
./scripts/testing/test_coverage.sh    # 測試覆蓋率報告 ⭐ 新增
```

### 🔍 **查詢工具**

```bash
./scripts/queries/test_query.sh       # 查詢測試工具
./scripts/queries/simple_query.sh     # 簡化查詢工具
```

### ✅ **驗證工具**

```bash
./scripts/verification/verify_system.sh  # 系統驗證
```

### 🛠️ **開發工具**

```bash
./scripts/restart_services.sh        # 服務重啟
./scripts/fix_api_gateway.sh         # API Gateway 修復
python scripts/development/simulate_writes.py  # 資料模擬
```

### 🧪 **Python 測試 (在 query-service 目錄)**

```bash
pytest tests/test_eks_handler.py -v     # 單元測試
pytest tests/test_integration.py -v -s  # 整合測試
pytest tests/ --cov=. --cov-report=html # 覆蓋率測試
```

## 🎉 專案成果

### ✅ **技術成就**

- 🏗️ 成功實作六邊形架構 + CQRS 模式
- 📈 Python 3.9 → 3.12 升級 (10-15% 效能提升)
- 🧪 建立完整的測試基礎設施
- 🔄 實現事件驅動的資料同步
- 📊 達到 76% 的測試覆蓋率

### 💻 **開發成果**

- 🔧 建立 15+ 個自動化腳本
- 📚 撰寫 12+ 份技術文檔
- 🔄 設置 CI/CD 流水線
- 🐳 容器化部署方案

### 📈 **效能指標**

- ⚡ API 響應時間: < 10ms
- 🔄 CQRS 同步率: 69.2%
- 🧪 測試通過率: 100%
- 📊 代碼覆蓋率: 76%

## 🔗 相關連結

- 📚 [完整文檔](./docs/) - 所有專案文檔
- 🔧 [腳本工具](./scripts/) - 自動化工具集
- 🚀 [主要服務](./query-service/) - 核心程式碼
- 🏗️ [架構圖解](./docs/architecture/CQRS_SUCCESS.md) - 視覺化架構說明

---

## 📞 支援

如有問題或建議，請參考：

1. 📋 [故障排除指南](./docs/testing/VERIFICATION_GUIDE.md)
2. 🔧 [腳本使用說明](./scripts/README.md)
3. 📚 [完整文檔索引](./docs/README.md)

**享受探索現代微服務架構的旅程！** 🚀
