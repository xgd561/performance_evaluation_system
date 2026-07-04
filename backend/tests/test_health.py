import pytest
from fastapi.testclient import TestClient


class TestHealthCheck:
    """Tests for GET /api/v1/health"""

    def test_health_check_success(self, client: TestClient):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert "data" in data
        assert data["data"]["db"] == "ok"
        assert data["data"]["version"] == "1.0.0"

    def test_health_check_no_auth_required(self, client: TestClient):
        """健康检查接口无需认证即可访问"""
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["code"] == 0
