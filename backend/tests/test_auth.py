import pytest
from fastapi.testclient import TestClient


class TestAuthLogin:
    """Tests for POST /auth/login"""

    def test_login_success(self, client: TestClient, admin_user):
        resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["role"] == "admin"
        assert data["user"]["username"] == "admin"
        assert isinstance(data["access_token"], str) and len(data["access_token"]) > 10
        assert isinstance(data["refresh_token"], str) and len(data["refresh_token"]) > 10
        assert "id" in data["user"]
        assert "employee_id" in data["user"], "login 返回必须包含 employee_id，前端 my-performance 依赖此字段"
        assert "is_first_login" in data["user"], "login 返回必须包含 is_first_login，前端首次登录弹窗依赖此字段"
        assert data["user"]["is_first_login"] is False

    def test_login_invalid_password(self, client: TestClient, admin_user):
        resp = client.post("/auth/login", json={"username": "admin", "password": "wrongpassword"})
        assert resp.status_code == 401
        assert resp.json()["message"] == "用户名或密码错误"

    def test_login_nonexistent_user(self, client: TestClient):
        resp = client.post("/auth/login", json={"username": "nonexistent", "password": "password"})
        assert resp.status_code == 401
        assert resp.json()["message"] == "用户名或密码错误"

    def test_login_rate_limiting(self, client: TestClient, admin_user):
        # 5 failed attempts should trigger rate limit
        for i in range(5):
            client.post("/auth/login", json={"username": "testuser", "password": "wrong"})
        # 6th attempt should be rate limited
        resp = client.post("/auth/login", json={"username": "testuser", "password": "wrong"})
        assert resp.status_code == 429
        assert "30分钟" in resp.json()["message"]

    def test_login_missing_fields(self, client: TestClient):
        resp = client.post("/auth/login", json={"username": ""})
        assert resp.status_code == 422

    def test_login_first_login_user(self, client: TestClient, employee_user):
        resp = client.post("/auth/login", json={"username": "emp001", "password": "Emp001@123"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["is_first_login"] is True
        assert data["user"]["role"] == "employee"
        assert data["user"]["name"] == "王员工"

    def test_login_remember_me(self, client: TestClient, admin_user):
        resp = client.post("/auth/login", json={"username": "admin", "password": "admin123", "remember_me": True})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"


class TestAuthRefresh:
    """Tests for POST /auth/refresh"""

    def test_refresh_success(self, client: TestClient, admin_user):
        login_resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
        refresh_token = login_resp.json()["refresh_token"]
        resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str) and len(data["access_token"]) > 10

    def test_refresh_invalid_token(self, client: TestClient):
        resp = client.post("/auth/refresh", json={"refresh_token": "invalid_token"})
        assert resp.status_code == 401
        assert resp.json()["message"] == "Refresh token已过期或无效"

    def test_refresh_missing_token(self, client: TestClient):
        resp = client.post("/auth/refresh", json={})
        assert resp.status_code == 422


class TestAuthMe:
    """Tests for GET /auth/me"""

    def test_get_me_success(self, client: TestClient, admin_token):
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"
        assert "id" in data
        assert "name" in data
        assert "employee_id" in data

    def test_get_me_no_auth(self, client: TestClient):
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_get_me_invalid_token(self, client: TestClient):
        resp = client.get("/auth/me", headers={"Authorization": "Bearer invalid_token"})
        assert resp.status_code == 401


class TestAuthChangePassword:
    """Tests for PUT /auth/password and POST /auth/change-password"""

    def test_change_password_success(self, client: TestClient, admin_token):
        payload = {"old_password": "admin123", "new_password": "NewPass123"}
        resp = client.put("/auth/password", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert resp.json()["message"] == "密码修改成功"

        # Login with new password
        resp = client.post("/auth/login", json={"username": "admin", "password": "NewPass123"})
        assert resp.status_code == 200

    def test_change_password_wrong_old(self, client: TestClient, admin_token):
        payload = {"old_password": "wrongold", "new_password": "NewPass123"}
        resp = client.put("/auth/password", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 400
        assert resp.json()["message"] == "旧密码错误"

    def test_change_password_same_as_old(self, client: TestClient, admin_token):
        payload = {"old_password": "admin123", "new_password": "admin123"}
        resp = client.put("/auth/password", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 400
        assert resp.json()["message"] == "新密码不能与旧密码相同"

    def test_change_password_too_short(self, client: TestClient, admin_token):
        payload = {"old_password": "admin123", "new_password": "123"}
        resp = client.put("/auth/password", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "密码长度过短" in resp.json()["message"]

    def test_change_password_weak(self, client: TestClient, admin_token):
        payload = {"old_password": "admin123", "new_password": "12345678"}
        resp = client.put("/auth/password", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "密码复杂度不足" in resp.json()["message"]

    def test_change_password_post_success(self, client: TestClient, admin_token):
        payload = {"old_password": "admin123", "new_password": "NewPass123"}
        resp = client.post("/auth/change-password", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert resp.json()["message"] == "密码修改成功"

    def test_change_password_no_auth(self, client: TestClient):
        payload = {"old_password": "admin123", "new_password": "NewPass123"}
        resp = client.put("/auth/password", json=payload)
        assert resp.status_code == 401


class TestAuthLogout:
    """Tests for POST /auth/logout"""

    def test_logout_success(self, client: TestClient, admin_token):
        resp = client.post("/auth/logout", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert resp.json()["message"] == "退出成功"

    def test_logout_no_auth(self, client: TestClient):
        resp = client.post("/auth/logout")
        assert resp.status_code == 401
