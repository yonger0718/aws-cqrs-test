# ECS GUI 部署詳細步驟指南

## 🎯 ECS 服務完整部署流程

### 階段 1: 準備工作

#### 1.1 檢查 ECR 映像

```bash
# 確認映像已存在
aws ecr describe-images --repository-name query-service --region ap-southeast-1
```

#### 1.2 準備 IAM 角色

前往 IAM Console 確認以下角色存在：

- `ecsTaskExecutionRole`
- `ecsTaskRole`

### 階段 2: 創建 ECS 集群

#### 2.1 進入 ECS Console

1. 登入 AWS Console
2. 搜尋並點擊 "Elastic Container Service"
3. 點擊左側導航的 "Clusters"

#### 2.2 創建新集群

1. 點擊 "Create Cluster" 按鈕
2. 選擇 "Networking only (Powered by AWS Fargate)"
3. 配置如下：

```
叢集名稱: query-service-cluster
建立 VPC: 取消勾選 (使用現有 VPC)
CloudWatch Container Insights: 啟用
標籤:
  - Key: Environment, Value: production
  - Key: Service, Value: query-service
```

4. 點擊 "Create" 建立集群

### 階段 3: 創建任務定義

#### 3.1 進入任務定義頁面

1. ECS Console → 左側導航 → "Task Definitions"
2. 點擊 "Create new Task Definition"

#### 3.2 選擇啟動類型

- 選擇 "Fargate"
- 點擊 "Next step"

#### 3.3 配置任務定義

**步驟 3.3.1: 基本設定**

```
任務定義名稱: query-service-task
任務角色: ecsTaskRole
網路模式: awsvpc (預設)
作業系統家族: Linux
```

**步驟 3.3.2: 任務執行 IAM 角色**

```
任務執行角色: ecsTaskExecutionRole
```

**步驟 3.3.3: 任務大小**

```
任務記憶體 (GB): 0.5GB
任務 CPU (vCPU): 0.25 vCPU
```

#### 3.4 新增容器

**步驟 3.4.1: 點擊 "Add container"**

**步驟 3.4.2: 容器基本設定**

```
容器名稱: query-service-container
映像: {您的帳號ID}.dkr.ecr.ap-southeast-1.amazonaws.com/query-service:latest
記憶體限制 (MiB): 軟性限制 512
```

**步驟 3.4.3: 連接埠對應**

```
連接埠對應:
- 容器連接埠: 8000
- 協定: tcp
```

**步驟 3.4.4: 環境變數**
點擊 "Advanced container configuration" → "Environment"

新增以下環境變數：

```
ENVIRONMENT = production
INTERNAL_API_URL = https://your-api-gateway-id.execute-api.ap-southeast-1.amazonaws.com/v1
AWS_DEFAULT_REGION = ap-southeast-1
AWS_REGION = ap-southeast-1
REQUEST_TIMEOUT = 30
```

**步驟 3.4.5: 日誌配置**
在 "Logging" 區段：

```
日誌驅動程式: awslogs
日誌選項:
- awslogs-group: /ecs/query-service
- awslogs-region: ap-southeast-1
- awslogs-stream-prefix: ecs
```

**步驟 3.4.6: 健康檢查**
在 "Health check" 區段：

```
命令: CMD-SHELL,curl -f http://localhost:8000/health || exit 1
間隔: 30
逾時: 5
重試次數: 3
開始期間: 60
```

**步驟 3.4.7: 完成容器設定**

- 點擊 "Add" 新增容器

#### 3.5 完成任務定義

- 檢查所有設定
- 點擊 "Create" 建立任務定義

### 階段 4: 建立 Application Load Balancer

#### 4.1 進入 EC2 Console

1. AWS Console → EC2
2. 左側導航 → "Load Balancers"
3. 點擊 "Create Load Balancer"

#### 4.2 選擇負載均衡器類型

- 選擇 "Application Load Balancer"
- 點擊 "Create"

#### 4.3 基本配置

```
名稱: query-service-alb
配置: internet-facing 或 internal (根據需求)
IP 地址類型: ipv4
```

#### 4.4 網路映射

```
VPC: 選擇您的 VPC
可用性區域: 選擇至少 2 個子網 (私有子網)
```

#### 4.5 安全群組

1. 選擇現有安全群組或建立新的
2. 規則應包含：
   - Type: HTTP, Port: 80, Source: 根據需求
   - Type: HTTPS, Port: 443, Source: 根據需求

#### 4.6 目標群組

1. 建立新目標群組：

```
目標類型: IP addresses
協定: HTTP
連接埠: 8000
VPC: 選擇相同的 VPC
健康檢查路徑: /health
```

### 階段 5: 建立 ECS 服務

#### 5.1 回到 ECS Console

1. Clusters → query-service-cluster
2. "Services" 標籤 → "Create"

#### 5.2 服務配置

**步驟 5.2.1: 基本設定**

```
啟動類型: Fargate
作業系統家族: Linux
任務定義: query-service-task
修訂: 1 (最新)
平台版本: LATEST
叢集: query-service-cluster
服務名稱: query-service
服務類型: REPLICA
所需數量: 1
```

**步驟 5.2.2: 部署配置**

```
部署類型: Rolling update
最小健康百分比: 50
最大百分比: 200
```

#### 5.3 網路配置

**步驟 5.3.1: VPC 和安全群組**

```
叢集 VPC: 選擇您的 VPC
子網路: 選擇私有子網
安全群組: 建立新的或選擇現有
- 規則: 允許來自 ALB 安全群組的 8000 連接埠入站流量
自動指派公用 IP: DISABLED
```

#### 5.4 負載均衡

**步驟 5.4.1: 負載均衡器配置**

```
負載均衡器類型: Application Load Balancer
負載均衡器名稱: query-service-alb
```

**步驟 5.4.2: 容器負載均衡**

```
容器名稱 : 連接埠: query-service-container:8000:HTTP
目標群組名稱: 選擇先前建立的目標群組
```

#### 5.5 服務發現 (可選)

```
啟用服務發現整合: 勾選
命名空間: 建立新的或選擇現有
服務名稱: query-service
```

#### 5.6 自動擴展 (可選)

```
服務自動擴展: 不要調整所需數量 (或根據需求配置)
```

#### 5.7 建立服務

- 檢查所有設定
- 點擊 "Create Service"

### 階段 6: 驗證部署

#### 6.1 檢查服務狀態

1. ECS Console → Clusters → query-service-cluster → Services
2. 檢查服務狀態為 "ACTIVE"
3. 檢查任務狀態為 "RUNNING"

#### 6.2 檢查健康檢查

1. EC2 Console → 目標群組
2. 檢查目標健康狀態為 "healthy"

#### 6.3 測試服務

```bash
# 透過 ALB DNS 名稱測試
curl http://your-alb-dns-name/health

# 預期回應
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:00:00Z",
  "service": "query-service"
}
```

## 🔧 常見設定問題和解決方案

### 問題 1: 任務無法啟動

**症狀**: 任務狀態顯示 "STOPPED"
**解決方案**:

1. 檢查 CloudWatch 日誌群組 `/ecs/query-service`
2. 確認 ECR 映像存在且可存取
3. 檢查 IAM 角色權限

### 問題 2: 健康檢查失敗

**症狀**: 目標群組中目標顯示 "unhealthy"
**解決方案**:

1. 檢查容器是否正在監聽 8000 連接埠
2. 確認健康檢查路徑 `/health` 可存取
3. 檢查安全群組規則

### 問題 3: 無法拉取映像

**症狀**: 任務失敗，錯誤提到 "CannotPullContainerError"
**解決方案**:

1. 確認 `ecsTaskExecutionRole` 具有 ECR 權限
2. 檢查映像 URI 是否正確
3. 確認映像存在於指定區域

## 📋 部署後檢查清單

- [ ] ECS 集群狀態為 ACTIVE
- [ ] 任務定義版本正確
- [ ] ECS 服務狀態為 ACTIVE
- [ ] 任務狀態為 RUNNING
- [ ] ALB 目標群組健康檢查通過
- [ ] CloudWatch 日誌正常輸出
- [ ] 服務回應健康檢查端點
- [ ] 環境變數配置正確
- [ ] 安全群組規則適當
