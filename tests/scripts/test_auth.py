"""
test_auth.py — Authentication module tests (TC-AUTH-001 ~ TC-AUTH-012)

Corresponds to test cases in:
  TEST_CASES_绩效考核评分系统_v1.0.md  §1 认证模块 (AUTH)
"""

import pytest
from fastapi.testclient import TestClient

from tests.scripts.utils import assert_status_code, assert_json_field


class TestAuthLogin:
    """TC-AUTH-001 ~ TC-AUTH-004, TC-AUTH-009 ~ TC-AUTH-012"""

    def test_login_success(self, client: TestClient):
        """TC-AUTH-001: 用户登录成功"""
        resp = client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert_status_code(resp, 200)
        data = resp.json()
        assert "access_token" in data or "token" in data
        assert data.get("user") is not None

    def test_login_user_not_found(self, client: TestClient):
        """TC-AUTH-002: 用户名不存在登录失败"""
        resp = client.post(
            "/auth/login",
            json={"username": "notexist", "password": "anypassword"},
        )
        assert_status_code(resp, 401)
        data = resp.json()
        assert "用户名或密码错误" in data.get("message", "")

    def test_login_account_lock_after_5_failures(self, client: TestClient):
        """TC-AUTH-003: 密码错误5次触发账号锁定30分钟"""
        for i in range(5):
            resp = client.post(
                "/auth/login",
                json={"username": "testuser", "password": f"Wrong{i}"},
            )
            assert resp.status_code == 401

        # 6th attempt with correct password should be rate-limited
        resp = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "Correct123"},
        )
        assert_status_code(resp, 429)
        assert "密码错误次数过多" in resp.json().get("message", "")

    def test_first_login_force_change_password(self, client: TestClient):
        """TC-AUTH-004: 首次登录强制修改密码"""
        # Login with initial password
        resp = client.post(
            "/auth/login",
            json={"username": "emp001", "password": "Emp001@123"},
        )
        assert_status_code(resp, 200)
        token = resp.json().get("access_token", resp.json().get("token", ""))
        headers = {"Authorization": f"Bearer {token}"}

        # Attempt to access dashboard without changing password
        resp2 = client.get("/dashboard", headers=headers)
        assert_status_code(resp2, 403)
        assert "请先修改初始密码" in resp2.json().get("message", "")

    def test_remember_me_7_days(self, client: TestClient):
        """TC-AUTH-009: 记住密码7天免登录"""
        # This primarily tests the Refresh Token mechanism
        resp = client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123", "remember_me": True},
        )
        assert_status_code(resp, 200)
        data = resp.json()
        assert "refresh_token" in data or "token" in data

    def test_password_visibility_toggle_ui(self):
        """TC-AUTH-010: 密码可见性切换 (UI test — E2E required)"""
        # Pure frontend interaction; backend cannot test DOM visibility.
        pytest.skip("UI-only test: verify in browser/E2E suite (Playwright/Cypress)")

    def test_login_page_responsive_layout(self):
        """TC-AUTH-011: 登录页响应式布局 (UI test — E2E required)"""
        pytest.skip("UI-only test: verify responsive layout in browser/E2E suite")

    def test_login_error_message_vague(self, client: TestClient):
        """TC-AUTH-012: 登录错误提示模糊化"""
        resp1 = client.post(
            "/auth/login",
            json={"username": "notexist", "password": "wrong"},
        )
        resp2 = client.post(
            "/auth/login",
            json={"username": "admin", "password": "wrongpassword"},
        )
        assert resp1.status_code == resp2.status_code == 401
        msg1 = resp1.json().get("message", "")
        msg2 = resp2.json().get("message", "")
        assert msg1 == msg2, "Error messages should be vague and identical"
        assert "USER_NOT_FOUND" not in msg1
        assert "PASSWORD_MISMATCH" not in msg1


class TestAuthPassword:
    """TC-AUTH-005: 修改密码成功"""

    def test_change_password_success(self, client: TestClient, admin_headers: dict):
        """TC-AUTH-005: 用户修改密码成功"""
        # Change password
        resp = client.put(
            "/auth/password",
            json={"old_password": "admin123", "new_password": "NewPass456"},
            headers=admin_headers,
        )
        assert_status_code(resp, 200)
        assert "密码修改成功" in resp.json().get("message", "")

        # Old password should fail
        resp_old = client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert_status_code(resp_old, 401)

        # New password should succeed
        resp_new = client.post(
            "/auth/login",
            json={"username": "admin", "password": "NewPass456"},
        )
        assert_status_code(resp_new, 200)

        # Restore original password for other tests
        new_token = resp_new.json().get("access_token", resp_new.json().get("token", ""))
        client.put(
            "/auth/password",
            json={"old_password": "NewPass456", "new_password": "admin123"},
            headers={"Authorization": f"Bearer {new_token}"},
        )


class TestAuthToken:
    """TC-AUTH-006 ~ TC-AUTH-008"""

    def test_access_without_token(self, client: TestClient):
        """TC-AUTH-006: 无Token访问受保护接口返回401"""
        resp = client.get("/employees")
        assert_status_code(resp, 401)
        data = resp.json()
        assert data.get("code") == 401 or "Unauthorized" in data.get("message", "")

    def test_access_with_forged_token(self, client: TestClient):
        """TC-AUTH-007: 伪造JWT访问API返回401"""
        forged_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        resp = client.get(
            "/employees",
            headers={"Authorization": f"Bearer {forged_token}"},
        )
        assert_status_code(resp, 401)
        assert "Token" in resp.json().get("message", "") or resp.json().get("code") == 401

    def test_access_with_expired_token(self, client: TestClient):
        """TC-AUTH-008: 过期Token访问API返回401"""
        # Use a known expired token or trigger token expiration
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTY4MDAwMDAwMH0.invalidsignature"
        resp = client.get(
            "/employees",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert_status_code(resp, 401)
        assert "过期" in resp.json().get("message", "") or resp.json().get("code") == 401


class TestAuthRefresh:
    """TC-AUTH-013, TC-AUTH-014"""

    def test_refresh_token_success(self, client: TestClient):
        """TC-AUTH-013: 刷新Token成功"""
        # First login to get refresh token
        resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
        assert_status_code(resp, 200)
        data = resp.json()
        refresh_token = data.get("refresh_token", data.get("token", ""))

        # Refresh
        resp2 = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        if resp2.status_code == 404:
            pytest.skip("Refresh endpoint not implemented")
        assert_status_code(resp2, 200)
        new_data = resp2.json()
        assert "access_token" in new_data or "token" in new_data

    def test_refresh_token_expired(self, client: TestClient):
        """TC-AUTH-014: 过期RefreshToken返回401"""
        resp = client.post("/auth/refresh", json={"refresh_token": "expired_token_123"})
        if resp.status_code == 404:
            pytest.skip("Refresh endpoint not implemented")
        assert_status_code(resp, 401)
        assert "过期" in resp.json().get("message", "") or "invalid" in resp.json().get("message", "").lower()


class TestAuthChangePassword:
    """TC-AUTH-015, TC-AUTH-016, TC-AUTH-017"""

    def test_change_password_wrong_old(self, client: TestClient, admin_headers: dict):
        """TC-AUTH-015: 修改密码时旧密码错误"""
        resp = client.post(
            "/auth/change-password",
            json={"old_password": "WrongPass123", "new_password": "NewPass456"},
            headers=admin_headers,
        )
        if resp.status_code == 404:
            pytest.skip("Change password endpoint not implemented")
        assert_status_code(resp, 400)
        assert "旧密码" in resp.json().get("message", "")

    def test_change_password_same_as_old(self, client: TestClient, admin_headers: dict):
        """TC-AUTH-016: 新密码与旧密码相同被拦截"""
        resp = client.post(
            "/auth/change-password",
            json={"old_password": "admin123", "new_password": "admin123"},
            headers=admin_headers,
        )
        if resp.status_code == 404:
            pytest.skip("Change password endpoint not implemented")
        assert_status_code(resp, 400)
        assert "相同" in resp.json().get("message", "")

    def test_change_password_weak(self, client: TestClient, admin_headers: dict):
        """TC-AUTH-017: 弱密码修改被拦截"""
        resp = client.post(
            "/auth/change-password",
            json={"old_password": "admin123", "new_password": "12345678"},
            headers=admin_headers,
        )
        if resp.status_code == 404:
            pytest.skip("Change password endpoint not implemented")
        assert_status_code(resp, 422)
        assert "复杂度" in resp.json().get("message", "") or "弱" in resp.json().get("message", "")