# 🔔 AWS CQRS + 六邊形架構通知系統

[![CI/CD Pipeline](https://github.com/yonger0718/aws-cqrs-test/actions/workflows/ci.yml/badge.svg)](https://github.com/yonger0718/aws-cqrs-test/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/yonger0718/aws-cqrs-test/graph/badge.svg?token=JH9SFXB4YR)](https://codecov.io/gh/yonger0718/aws-cqrs-test)
[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Architecture](https://img.shields.io/badge/architecture-CQRS+Hexagonal-purple.svg)](docs/architecture/cqrs-hexagonal-design.md)

> **六邊形架構 + CQRS 模式** 的企業級推播通知系統，使用 LocalStack 模擬 AWS 環境

## 🎯 專案概述

本專案展示了現代微服務架構的最佳實踐，實現了完整的企業級解決方案：

- **🏗️ 六邊形架構 (Hexagonal Architecture)**: Domain-Driven Design 的清晰領域分離
- **📊 CQRS 模式 (Command Query Responsibility Segregation)**: 完整的讀寫分離實現
- **🔄 事件驅動架構**: DynamoDB Stream 驅動的異步資料同步
- **🐳 容器化部署**: Docker Compose 一鍵啟動完整環境
- **🧪 完整測試覆蓋**: 高代碼覆蓋率 + 整合測試 + 端到端測試
- **🔍 依賴注入**: FastAPI 原生依賴注入系統
- **📝 API 文檔**: 自動生成的 OpenAPI/Swagger 文檔
- **📦 Poetry 依賴管理**: 現代化的 Python 依賴管理工具

## 🏗️ 系統架構

### CQRS + 六邊形架構全貌

```txt
┌─────────────────────────────────────────────────────────────────┐
│                    六邊形架構 + CQRS                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐ │
│  │   Command Side  │───▶│  DynamoDB    │───▶│   Query Side    │ │
│  │   (Write Path)  │    │   Stream     │    │   (Read Path)   │ │
│  └─────────────────┘    └──────────────┘    └─────────────────┘ │
│           │                      │                      │       │
│           ▼                      ▼                      ▼       │
│    ┌─────────────┐      ┌─────────────┐      ┌─────────────┐    │
│    │ command-    │      │   Stream    │      │notification-│    │
│    │ records     │      │ Processor   │      │ records     │    │
│    │ (Write DB)  │      │  Lambda     │      │ (Read DB)   │    │
│    └─────────────┘      └─────────────┘      └─────────────┘    │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                FastAPI Query Service (六邊形架構)               │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                 Web Layer (Presentation)                   │ │
│  │        FastAPI Routes + Request/Response Models            │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │               Application Layer (Use Cases)                 │ │
│  │            QueryService + 依賴注入 + 業務邏輯               │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                 Domain Layer (Business)                    │ │
│  │        NotificationRecord + QueryResult + Enums            │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │            Infrastructure Layer (Adapters)                 │ │
│  │             LambdaAdapter + Port Interfaces                │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 核心特色 ��

- **🔧 領域模型重構**: 強類型的業務實體和價值對象
- **📮 端口與適配器**: 清晰的接口分離和依賴反轉
- **🧪 測試能力提升**: Mock 友好的依賴注入架構
- **📊 結構化響應**: 統一的查詢結果模型
- **🔍 API 文檔自動化**: Pydantic 模型驅動的 OpenAPI 規範

## 📁 專案結構

```txt
📦 aws-cqrs-test/
├── 📚 docs/                          # 📖 專案文檔
│   ├── 🧪 testing/                   # 測試指南
│   ├── 📖 guides/                    # 使用說明
│   ├── 🏗️ architecture/              # 六邊形架構設計文檔
│   │   ├── cqrs-hexagonal-design.md  # CQRS + 六邊形設計詳解
│   │   └── ecs-migration-guide.md    # ECS 遷移指南
│   ├── 🚀 deployment/                # 部署文檔
│   │   └── ecs-deployment.md         # ECS 部署指南
│   ├── 📡 api/                       # API 文檔
│   │   └── api-changes-v3.md         # V3 API 變更說明
│   └── 📊 project/                   # 專案總結
├── 🔧 scripts/                       # 🛠️ 腳本工具
│   ├── 🧪 testing/                   # 測試腳本
│   ├── 🔍 queries/                   # 查詢工具
│   ├── ✅ verification/              # 驗證腳本
│   └── 🛠️ development/               # 開發工具
├── 📦 pyproject.toml                 # Poetry 依賴管理配置
└── 🚀 query-service/                 # 🎯 主要服務
    ├── eks_handler/                  # 📡 FastAPI 六邊形架構服務 (ECS 容器)
    │   ├── main.py                   # 六邊形架構實現
    │   ├── Dockerfile                # ECS 容器配置
    │   └── __init__.py               # 領域模型導出
    ├── lambdas/                      # ⚡ AWS Lambda 函數
    │   ├── query_lambda/             # API Gateway 入口
    │   ├── query_result_lambda/      # 查詢處理邏輯
    │   └── stream_processor_lambda/  # CQRS 事件處理器
    │       └── app.py                # 領域驅動的 Stream 處理
    ├── tests/                        # 🧪 測試套件
    ├── infra/                        # 🏗️ 基礎設施
    │   ├── localstack/               # LocalStack 設定
    │   └── terraform/                # Terraform 部署配置 (ECS)
    └── docker-compose.yml            # 本地開發環境
```

## 🚀 快速開始

### ✅ **步驟一: 環境準備**

```bash
# 確保已安裝 Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 安裝專案依賴
poetry install

# 檢查系統環境和依賴
./scripts/verification/verify_system.sh
```

### 🐳 **步驟二: 啟動服務**

#### 🌟 **Docker 化部署（推薦）**

```bash
# 使用新的 Docker 化 Lambda 部署
cd query-service
./deploy_docker.sh start    # 一鍵啟動完整環境
./deploy_docker.sh deploy   # 部署 Docker 化的 Lambda 函數
./deploy_docker.sh test     # 執行集成測試
```

#### 🔧 **傳統部署方式**

```bash
# 重啟並初始化服務
./scripts/restart_services.sh
```

### ⚙️ **步驟三: 修復 API Gateway (如需要)**

```bash
# 修復 API Gateway 配置
./scripts/fix_api_gateway.sh
```

### 🧪 **步驟四: 執行測試**

```bash
# 使用 Poetry 執行 Python 測試
poetry run pytest

# 快速系統驗證
./scripts/testing/quick_test.sh

# 完整流程測試
./scripts/testing/test_full_flow.sh
```

### 🔍 **步驟五: 查詢測試**

```bash
# 查詢測試工具
./scripts/queries/test_query.sh

# 簡化查詢工具
./scripts/queries/simple_query.sh --all
```

### 📖 **步驟六: API 文檔查看**

```bash
# 啟動服務後訪問 API 文檔
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

## 📋 推薦測試驗證順序

### 🎯 **完整驗證流程 (新環境/重大更改後)**

```bash
# 1. 環境準備
poetry install
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
poetry run pytest tests/ -v --cov
```

### ⚡ **快速驗證 (日常開發)**

```bash
# 快速健康檢查
./scripts/testing/quick_test.sh

# 查詢功能確認
./scripts/queries/simple_query.sh --all

# Python 測試
poetry run pytest tests/ -v
```

**📖 詳細說明：** [測試驗證指南](./docs/testing/VERIFICATION_GUIDE.md)

## 📋 核心功能

### 🎯 **CQRS 實作**

- ✅ **命令側**: `command-records` 表 + DynamoDB Stream
- ✅ **查詢側**: `notification-records` 表 + GSI 索引
- ✅ **事件驅動**: Stream Processor 自動同步資料
- ✅ **資料轉換**: 針對查詢最佳化的資料結構

### 🏗️ **六邊形架構實作**

- ✅ **領域層 (Domain)**: 純業務邏輯，無外部依賴
- ✅ **應用層 (Application)**: 用例協調，依賴注入
- ✅ **端口 (Ports)**: 抽象接口定義
- ✅ **適配器 (Adapters)**: 外部系統整合實現

### 🔍 **查詢功能**

- 👤 **用戶查詢**: 根據 `user_id` 查詢個人推播記錄
- 📢 **活動查詢**: 根據 `marketing_id` 查詢活動推播統計
- ❌ **失敗查詢**: 根據 `transaction_id` 查詢失敗記錄 (端點: `/query/fail`)

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
🏗️ 架構驗證:   ✅ 六邊形架構完整實現
📡 API 文檔:    ✅ OpenAPI 3.0 自動生成
```

## 🛠️ 技術棧

### 🖥️ **後端技術**

- **Python 3.12**: 主要開發語言 + 現代類型提示
- **FastAPI**: 高效能 Web 框架 + 依賴注入
- **Pydantic v2**: 數據驗證和序列化
- **AWS Lambda**: 無伺服器函數
- **DynamoDB**: NoSQL 資料庫 + Stream
- **LocalStack**: AWS 本地模擬環境

### 🏗️ **架構模式**

- **CQRS**: 讀寫分離模式
- **六邊形架構**: 端口與適配器模式
- **領域驅動設計**: 業務邏輯為核心
- **事件驅動**: Stream 事件處理
- **依賴注入**: 松耦合設計

### 🧪 **測試技術**

- **pytest**: 測試框架
- **coverage**: 覆蓋率測試
- **unittest.mock**: 模擬測試
- **TestClient**: API 測試
- **Hypothesis**: 屬性測試

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
