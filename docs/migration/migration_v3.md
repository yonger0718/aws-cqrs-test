# 遷移至新架構的步驟

1. **建立 ECS Fargate 容器服務**：在 AWS 上創建新的 ECS Fargate 叢集與服務，部署原查詢服務容器（FastAPI 應用）替代 EKS Handler。

   * 建立 ECS **叢集**並使用 Fargate 執行模式。準備查詢服務的 Docker **映像**（Python 3.12），上傳至 ECR 映像庫。
   * 創建 ECS **任務定義**（Task Definition）：設定容器映像、CPU/記憶體配額，環境變數（如運行環境、Internal API URL 等），以及 IAM 執行角色（允許訪問 DynamoDB 或調用 Lambda 的權限）。
   * 部署 ECS **服務**：在相同 VPC 中啟動 Fargate 任務執行個體，設定所屬子網和安全組，確保容器可透過內網訪問 Internal API Gateway 和 DynamoDB。 （例如，開放必要的出站 HTTP/HTTPS 存取權限給內部 API 網關網域）

2. **設定內部 API Gateway（Private)**：建立新的 AWS API Gateway 作為內部服務介面，供 ECS 容器調用 Lambda 查詢資料。

   * 建立**私有 API Gateway**並配置 **VPC 介接**（Interface Endpoint），使其僅供內部網路存取。新增路由，例如 `/query/result`，並將其整合 (Integration) 到現有的 **查詢結果 Lambda** 函數。該 Lambda 負責從 DynamoDB 擷取查詢資料。
   * 使用 **Lambda Proxy 統合**方式，使 ECS 發送的 HTTP 請求內容作為 Lambda 輸入。設定請求與回應的轉換，確保 Lambda 的回傳 JSON 可直接作為 API 回應正文。
   * 設定完成後，記錄 Internal API Gateway 的 **專用網址**（Invoke URL），並將此網址提供給 ECS 容器使用（透過環境變數傳入）。測試 Internal API Gateway，確認在內網中呼叫該 URL 能成功觸發 Lambda 並取得 DynamoDB 查詢結果。

3. **調整查詢服務應用程式碼**：修改原 EKS Handler 程式碼以適應新架構與環境。開發人員需重構部分邏輯：

   * **改用 Internal API 呼叫**：原 EKS Handler 透過 `LambdaAdapter.invoke_lambda(...)` 呼叫 `query_result_lambda` 取得資料。現需改為發送 HTTP 請求至 Internal API Gateway 的路由，以觸發相同的 Lambda 邏輯。可實作新的 HTTP 客戶端適配器（例如使用 `requests` 發送 POST 請求），將查詢參數 (`user_id` 等) 作為 JSON 請求正文傳遞。確保請求路徑和參數與原 Lambda 輸入格式相容，以取得正確回應。
   * **環境變數設定**：在 ECS 環境中新增 Internal API Gateway 的 URL，例如通過環境變數 `INTERNAL_API_URL` 提供給應用使用。並將應用程式的 `ENVIRONMENT` 環境變數設為 `"production"`（原程式碼會據此判斷是否使用 LocalStack 等本地設定）。同時，調整原 Query Lambda 的目標服務位址：更新其環境變數 `EKS_HANDLER_URL` 指向新的 ECS 服務 URL（例如內部負載均衡 DNS）。這可確保 API Gateway 入口的 Lambda 會呼叫到正確的 ECS 查詢服務實例。
   * **請求/回應格式校調**：保持前後端通訊介面的資料格式一致。外部 API Gateway + Query Lambda 的輸入輸出格式應與 ECS 上 FastAPI 服務相符，確保最終使用者請求與回應內容不變。由於仍採用 FastAPI 定義的結構，請確認 Internal API Gateway 回傳的 JSON 結構可被 ECS 容器中的程式正確解析（例如直接取得 Lambda 回傳的 `body` 部分）。必要時，在應用程式中調整對 Lambda 回傳結果的解析邏輯，以符合 HTTP 回應格式。

4. **移除行銷活動查詢功能**：關閉或移除原有與 Marketing 行銷活動相關的查詢端點及處理邏輯。

   * **註解 API 端點**：在查詢服務 FastAPI 應用中註解掉 `/query/marketing` 相關的路由及方法，不再對外提供行銷活動ID的查詢服務。保留該段程式碼以備將來參考，但禁止在新版本中啟用。前端或客戶端如呼叫該端點應收到適當的錯誤或提示。
   * **停用相關處理**：如查詢 Lambda 或查詢結果 Lambda 中有根據 `marketing_id` 查詢的邏輯，亦可一併註解或移除，避免不必要的執行。對應的 DynamoDB GSI（如 `marketing_id-index`）可保留但不再使用，或日後視需要從基礎設施中移除以簡化結構。

5. **部署與文件準備**：在完成以上變更後，進行部署及驗證，同時編寫相關說明文件備查。

   * **部署新架構**：由詠哥手動將更新後的查詢服務部署至 AWS 環境。包括：部署新的 ECS Fargate Service（載入新映像與環境變數）、部署 Internal API Gateway 並確認其與 Lambda 的串接、更新並部署調整後的 Lambda 程式碼（Query Lambda 入口及 QueryResult Lambda 若有修改）。部署過程中請逐一驗證各組件是否正常啟動，並透過模擬請求測試完整查詢流程，確保 API Gateway -> Lambda -> ECS -> Internal API -> Lambda -> DynamoDB 資料流通順無誤。
   * **流量切換與監控**：當新架構部署就緒且通過測試後，將外部 API Gateway 的流量切換至新的 ECS 查詢服務（確保 Query Lambda 指向的新位址生效）。監控日誌與指標，確定查詢請求均成功由新架構處理並符合預期。完成切換後，關閉並清除舊的 EKS 上相關資源（如舊的 Handler 部署與服務），避免資源浪費。
   * **撰寫遷移文件**：最後，整理以上遷移步驟與設定變更細節，記錄在專案文件中（例如新增 `README.md` 或 `migration.md`）。文件中應說明新的架構圖、各元件的配置變更、部署步驟，以及資料表結構更新事項（特別是 `ap_id` 欄位的用途）等。透過完整的文件紀錄，確保團隊其他成員日後能瞭解此次架構調整的內容，並為未來維護提供依據。

**Sources:** 原始專案架構與程式碼展示了本次改造所依據的基礎。上述步驟按照開發實務進行規劃，確保從建置基礎設施、調整程式碼到資料庫與文件更新，每個環節都完整覆蓋，順利將查詢服務由 EKS 遷移至 ECS Fargate 新架構。
