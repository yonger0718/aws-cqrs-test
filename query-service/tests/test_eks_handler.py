"""
EKS Handler 單元測試
測試 FastAPI 應用程式的所有端點和功能
"""

import os
import sys
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# 根據執行目錄調整導入路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
query_service_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(query_service_dir)

# 如果從根目錄執行，添加 query-service 目錄到路徑
if "query-service" in current_dir:
    # 從 query-service 目錄執行
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(
        0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "eks_handler")
    )
else:
    # 從根目錄執行
    sys.path.insert(0, os.path.join(project_root, "query-service"))
    sys.path.insert(0, os.path.join(project_root, "query-service", "eks_handler"))

# 必須在設置 sys.path 後導入
from eks_handler.main import app  # noqa: E402

# 建立測試客戶端
client = TestClient(app)


class TestHealthCheck:
    """健康檢查端點測試"""

    def test_health_endpoint(self) -> None:
        """測試 /health 端點返回正確的狀態"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        # 檢查必要的字段存在
        assert data["status"] == "healthy"
        assert data["service"] == "query-service-eks-handler"
        # 檢查額外字段也存在
        assert "architecture" in data
        assert "timestamp" in data
        assert data["architecture"] == "CQRS + Hexagonal"


class TestRootEndpoint:
    """根端點測試"""

    def test_root_endpoint(self) -> None:
        """測試根端點返回服務資訊"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Query Service EKS Handler"
        assert data["version"] == "2.0.0"
        assert data["architecture"] == "CQRS + Hexagonal Architecture"
        # 檢查端點存在
        endpoints = data["endpoints"]
        assert "/query/user" in endpoints.values()
        assert "/query/marketing" in endpoints.values()
        assert "/query/failures" in endpoints.values()
        assert "/health" in endpoints.values()


class TestUserQuery:
    """用戶查詢端點測試"""

    @patch("eks_handler.main.LambdaAdapter")
    def test_query_user_success(self, mock_lambda_adapter_class: Any) -> None:
        """測試成功查詢用戶推播記錄"""
        # 設置 LambdaAdapter 的 mock
        mock_lambda_adapter = mock_lambda_adapter_class.return_value
        mock_lambda_adapter.invoke_lambda = AsyncMock(
            return_value={
                "success": True,
                "items": [
                    {
                        "user_id": "user-001",
                        "transaction_id": "txn-123",
                        "created_at": 1640995200,
                        "notification_title": "測試通知",
                        "status": "SENT",
                        "platform": "IOS",
                    }
                ],
            }
        )

        # 發送請求
        response = client.post("/query/user", json={"user_id": "user-001"})

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["user_id"] == "user-001"
        assert data["total_count"] == 1

    @patch("eks_handler.main.LambdaAdapter")
    def test_query_user_lambda_error(self, mock_lambda_adapter_class: Any) -> None:
        """測試 Lambda 調用失敗的情況"""
        # 設置 LambdaAdapter 的 mock 拋出異常
        mock_lambda_adapter = mock_lambda_adapter_class.return_value
        mock_lambda_adapter.invoke_lambda = AsyncMock(
            side_effect=Exception("Lambda connection failed")
        )

        # 發送請求
        response = client.post("/query/user", json={"user_id": "user-001"})

        # 驗證錯誤處理
        assert response.status_code == 500
        assert "Lambda connection failed" in response.json()["detail"]


class TestMarketingQuery:
    """行銷活動查詢端點測試"""

    @patch("eks_handler.main.LambdaAdapter")
    def test_query_marketing_success(self, mock_lambda_adapter_class: Any) -> None:
        """測試成功查詢行銷活動推播記錄"""
        # 設置 LambdaAdapter 的 mock
        mock_lambda_adapter = mock_lambda_adapter_class.return_value
        mock_lambda_adapter.invoke_lambda = AsyncMock(
            return_value={
                "success": True,
                "items": [
                    {
                        "user_id": "user-002",
                        "transaction_id": "txn-456",
                        "created_at": 1640995300,
                        "marketing_id": "campaign-001",
                        "notification_title": "促銷活動",
                        "status": "DELIVERED",
                        "platform": "ANDROID",
                    }
                ],
            }
        )

        # 發送請求
        response = client.post("/query/marketing", json={"marketing_id": "campaign-001"})

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["marketing_id"] == "campaign-001"
        assert data["total_count"] == 1


class TestFailuresQuery:
    """失敗查詢端點測試"""

    @patch("eks_handler.main.LambdaAdapter")
    def test_query_failures_success(self, mock_lambda_adapter_class: Any) -> None:
        """測試成功查詢失敗的推播記錄"""
        # 設置 LambdaAdapter 的 mock
        mock_lambda_adapter = mock_lambda_adapter_class.return_value
        mock_lambda_adapter.invoke_lambda = AsyncMock(
            return_value={
                "success": True,
                "items": [
                    {
                        "user_id": "user-003",
                        "transaction_id": "txn-789",
                        "created_at": 1640995400,
                        "notification_title": "失敗通知",
                        "status": "FAILED",
                        "platform": "IOS",
                        "error_msg": "Network timeout",
                    }
                ],
            }
        )

        # 發送請求
        response = client.post("/query/failures", json={"transaction_id": "txn-789"})

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["transaction_id"] == "txn-789"
        assert data["data"][0]["status"] == "FAILED"
        assert data["total_count"] == 1


class TestEdgeCases:
    """邊界情況測試"""

    def test_invalid_json_payload(self) -> None:
        """測試無效的 JSON 載荷"""
        response = client.post(
            "/query/user",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_missing_required_field(self) -> None:
        """測試缺少必要欄位"""
        response = client.post("/query/user", json={})
        assert response.status_code == 422

    def test_invalid_endpoint(self) -> None:
        """測試不存在的端點"""
        response = client.get("/invalid/endpoint")
        assert response.status_code == 404

    @patch("eks_handler.main.LambdaAdapter")
    def test_query_user_lambda_failure_response(self, mock_lambda_adapter_class: Any) -> None:
        """測試 Lambda 返回失敗響應"""
        mock_lambda_adapter = mock_lambda_adapter_class.return_value
        mock_lambda_adapter.invoke_lambda = AsyncMock(
            return_value={"success": False, "message": "Query failed due to database error"}
        )

        response = client.post("/query/user", json={"user_id": "user-001"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Query failed due to database error" in data["message"]
        assert data["total_count"] == 0

    @patch("eks_handler.main.LambdaAdapter")
    def test_query_service_exception_handling(self, mock_lambda_adapter_class: Any) -> None:
        """測試查詢服務的異常處理"""
        mock_lambda_adapter = mock_lambda_adapter_class.return_value
        mock_lambda_adapter.invoke_lambda = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        response = client.post("/query/user", json={"user_id": "user-001"})

        assert response.status_code == 500
        assert "Failed to query user notifications" in response.json()["detail"]

    @patch("eks_handler.main.LambdaAdapter")
    def test_invalid_notification_record_parsing(self, mock_lambda_adapter_class: Any) -> None:
        """測試無效的通知記錄解析處理"""
        mock_lambda_adapter = mock_lambda_adapter_class.return_value
        mock_lambda_adapter.invoke_lambda = AsyncMock(
            return_value={
                "success": True,
                "items": [
                    {
                        "user_id": "user-001",
                        "transaction_id": "txn-123",
                        "created_at": 1640995200,
                        "notification_title": "有效通知",
                        "status": "SENT",
                        "platform": "IOS",
                    },
                    {
                        # 無效記錄 - 缺少必要字段
                        "user_id": "user-002",
                        "invalid_field": "invalid_value",
                    },
                ],
            }
        )

        response = client.post("/query/user", json={"user_id": "user-001"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # 只有一個有效記錄被解析
        assert len(data["data"]) == 1
        assert data["data"][0]["user_id"] == "user-001"
        assert data["total_count"] == 1

    @patch("eks_handler.main.LambdaAdapter")
    def test_query_marketing_exception_handling(self, mock_lambda_adapter_class: Any) -> None:
        """測試行銷查詢的異常處理"""
        mock_lambda_adapter = mock_lambda_adapter_class.return_value
        mock_lambda_adapter.invoke_lambda = AsyncMock(
            side_effect=RuntimeError("Service unavailable")
        )

        response = client.post("/query/marketing", json={"marketing_id": "campaign-001"})

        assert response.status_code == 500
        assert "Failed to query marketing notifications" in response.json()["detail"]

    @patch("eks_handler.main.LambdaAdapter")
    def test_query_failures_exception_handling(self, mock_lambda_adapter_class: Any) -> None:
        """測試失敗查詢的異常處理"""
        mock_lambda_adapter = mock_lambda_adapter_class.return_value
        mock_lambda_adapter.invoke_lambda = AsyncMock(
            side_effect=ValueError("Invalid transaction ID")
        )

        response = client.post("/query/failures", json={"transaction_id": "txn-789"})

        assert response.status_code == 500
        assert "Failed to query failed notifications" in response.json()["detail"]

    @patch("eks_handler.main.LambdaAdapter")
    def test_query_service_http_exception_re_raise(self, mock_lambda_adapter_class: Any) -> None:
        """測試查詢服務重新拋出HTTPException"""
        from fastapi import HTTPException

        mock_lambda_adapter = mock_lambda_adapter_class.return_value
        mock_lambda_adapter.invoke_lambda = AsyncMock(
            side_effect=HTTPException(status_code=502, detail="Bad Gateway")
        )

        response = client.post("/query/user", json={"user_id": "user-001"})

        assert response.status_code == 502
        assert "Bad Gateway" in response.json()["detail"]

    @patch("eks_handler.main.LambdaAdapter")
    def test_alternative_response_format(self, mock_lambda_adapter_class: Any) -> None:
        """測試替代響應格式處理"""
        mock_lambda_adapter = mock_lambda_adapter_class.return_value
        mock_lambda_adapter.invoke_lambda = AsyncMock(
            return_value={
                "success": True,
                "data": [  # 使用 'data' 而不是 'items'
                    {
                        "user_id": "user-001",
                        "transaction_id": "txn-123",
                        "created_at": 1640995200,
                        "notification_title": "測試通知",
                        "status": "SENT",
                        "platform": "IOS",
                    }
                ],
            }
        )

        response = client.post("/query/user", json={"user_id": "user-001"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["total_count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
