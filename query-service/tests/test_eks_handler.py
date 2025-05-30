"""
EKS Handler 單元測試
測試 FastAPI 應用程式的所有端點和功能
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# 將上層目錄加入 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 從 eks-handler 目錄導入 main 模組
sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "eks-handler"),
)

# 必須在設置 sys.path 後導入
from main import app  # noqa: E402

# 建立測試客戶端
client = TestClient(app)


class TestHealthCheck:
    """健康檢查端點測試"""

    def test_health_endpoint(self):
        """測試 /health 端點返回正確的狀態"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "healthy",
            "service": "query-service-eks-handler",
        }


class TestRootEndpoint:
    """根端點測試"""

    def test_root_endpoint(self):
        """測試根端點返回服務資訊"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Query Service EKS Handler"
        assert data["version"] == "1.0.0"
        assert "/query/user" in data["endpoints"]
        assert "/query/marketing" in data["endpoints"]
        assert "/query/failures" in data["endpoints"]


class TestUserQuery:
    """用戶查詢端點測試"""

    @patch("main.lambda_client")
    def test_query_user_success(self, mock_lambda_client):
        """測試成功查詢用戶推播記錄"""
        # 模擬 Lambda 響應
        mock_response = {"Payload": MagicMock()}
        mock_response["Payload"].read.return_value = json.dumps(
            {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "notifications": [
                            {
                                "notification_id": "notif-123",
                                "user_id": "user-001",
                                "title": "測試通知",
                                "status": "sent",
                            }
                        ]
                    }
                ),
            }
        )
        mock_lambda_client.invoke.return_value = mock_response

        # 發送請求
        response = client.post("/query/user", json={"user_id": "user-001"})

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert len(data["notifications"]) == 1
        assert data["notifications"][0]["user_id"] == "user-001"

        # 驗證 Lambda 被正確調用
        mock_lambda_client.invoke.assert_called_once()
        call_args = mock_lambda_client.invoke.call_args
        assert call_args[1]["FunctionName"] == "query_result_lambda"
        payload = json.loads(call_args[1]["Payload"])
        assert payload["query_type"] == "user"
        assert payload["user_id"] == "user-001"

    @patch("main.lambda_client")
    def test_query_user_lambda_error(self, mock_lambda_client):
        """測試 Lambda 調用失敗的情況"""
        # 模擬 Lambda 錯誤
        mock_lambda_client.invoke.side_effect = Exception("Lambda connection failed")

        # 發送請求
        response = client.post("/query/user", json={"user_id": "user-001"})

        # 驗證錯誤處理
        assert response.status_code == 500
        assert "Lambda connection failed" in response.json()["detail"]


class TestMarketingQuery:
    """行銷活動查詢端點測試"""

    @patch("main.lambda_client")
    def test_query_marketing_success(self, mock_lambda_client):
        """測試成功查詢行銷活動推播記錄"""
        # 模擬 Lambda 響應
        mock_response = {"Payload": MagicMock()}
        mock_response["Payload"].read.return_value = json.dumps(
            {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "notifications": [
                            {
                                "notification_id": "notif-456",
                                "marketing_id": "campaign-001",
                                "title": "促銷活動",
                                "sent_count": 100,
                            }
                        ]
                    }
                ),
            }
        )
        mock_lambda_client.invoke.return_value = mock_response

        # 發送請求
        response = client.post("/query/marketing", json={"marketing_id": "campaign-001"})

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert data["notifications"][0]["marketing_id"] == "campaign-001"


class TestFailuresQuery:
    """失敗查詢端點測試"""

    @patch("main.lambda_client")
    def test_query_failures_success(self, mock_lambda_client):
        """測試成功查詢失敗的推播記錄"""
        # 模擬 Lambda 響應
        mock_response = {"Payload": MagicMock()}
        mock_response["Payload"].read.return_value = json.dumps(
            {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "failures": [
                            {
                                "transaction_id": "txn-789",
                                "error": "Network timeout",
                                "retry_count": 3,
                            }
                        ]
                    }
                ),
            }
        )
        mock_lambda_client.invoke.return_value = mock_response

        # 發送請求
        response = client.post("/query/failures", json={"transaction_id": "txn-789"})

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert "failures" in data
        assert data["failures"][0]["transaction_id"] == "txn-789"


class TestEdgeCases:
    """邊界情況測試"""

    def test_invalid_json_payload(self):
        """測試無效的 JSON 載荷"""
        response = client.post(
            "/query/user",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_missing_required_field(self):
        """測試缺少必要欄位"""
        response = client.post("/query/user", json={})
        assert response.status_code == 422

    def test_invalid_endpoint(self):
        """測試不存在的端點"""
        response = client.get("/invalid/endpoint")
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
