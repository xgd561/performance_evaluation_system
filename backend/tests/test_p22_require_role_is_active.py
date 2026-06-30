import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.auth import require_role, get_current_user


# ---------------------------------------------------------------------------
# P1-22: require_role 必须检查 is_active
# ---------------------------------------------------------------------------

class TestRequireRoleIsActiveUnit:
    """Unit tests for require_role is_active check (direct function calls)."""

    def test_require_role_blocks_inactive_user(self):
        """require_role should raise 403 for inactive user even with correct role."""
        inactive_user = MagicMock()
        inactive_user.role = "admin"
        inactive_user.is_active = False

        role_checker = require_role("admin")

        with pytest.raises(HTTPException) as exc_info:
            role_checker(inactive_user)

        assert exc_info.value.status_code == 403
        assert "禁用" in exc_info.value.detail

    def test_require_role_allows_active_user(self):
        """require_role should return user for active user with correct role."""
        active_user = MagicMock()
        active_user.role = "admin"
        active_user.is_active = True

        role_checker = require_role("admin")
        result = role_checker(active_user)

        assert result == active_user

    def test_require_role_blocks_wrong_role(self):
        """require_role should still raise 403 for wrong role (existing behavior)."""
        user = MagicMock()
        user.role = "employee"
        user.is_active = True

        role_checker = require_role("admin")

        with pytest.raises(HTTPException) as exc_info:
            role_checker(user)

        assert exc_info.value.status_code == 403
        assert "权限不足" in exc_info.value.detail

    def test_require_role_blocks_inactive_before_role_check(self):
        """Inactive user should be blocked with '禁用' message, not '权限不足'."""
        user = MagicMock()
        user.role = "employee"
        user.is_active = False

        role_checker = require_role("admin")

        with pytest.raises(HTTPException) as exc_info:
            role_checker(user)

        assert exc_info.value.status_code == 403
        assert "禁用" in exc_info.value.detail


class TestRequireRoleIsActiveIntegration:
    """Integration tests: inactive users must be blocked from protected endpoints."""

    def test_inactive_admin_blocked_from_admin_endpoint(self, client: TestClient, admin_user, db_session: Session):
        """Inactive admin should be blocked from admin endpoints."""
        resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        admin_user.is_active = False
        db_session.commit()

        # /dashboard/cycles uses require_role("admin", "hr", "executive")
        resp = client.get("/dashboard/cycles", headers={"Authorization": f"Bearer {token}"})
        # get_current_user runs first and returns 401, so this is the expected behavior
        assert resp.status_code == 401
        assert "禁用" in resp.json()["message"]

    def test_inactive_hr_blocked_from_hr_endpoint(self, client: TestClient, hr_user, db_session: Session):
        """Inactive HR should be blocked from HR endpoints."""
        resp = client.post("/auth/login", json={"username": "hr001", "password": "Hr001@123"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        hr_user.is_active = False
        db_session.commit()

        resp = client.get("/dashboard/cycles", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "禁用" in resp.json()["message"]

    def test_inactive_manager_blocked_from_manager_endpoint(self, client: TestClient, manager_user, db_session: Session):
        """Inactive manager should be blocked from manager endpoints."""
        resp = client.post("/auth/login", json={"username": "mgr001", "password": "Mgr001@123"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        manager_user.is_active = False
        db_session.commit()

        # /dashboard/approvals uses require_role("admin", "hr", "manager")
        resp = client.get("/dashboard/approvals", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "禁用" in resp.json()["message"]

    def test_inactive_employee_blocked_from_employee_endpoint(self, client: TestClient, employee_user, db_session: Session):
        """Inactive employee should be blocked from employee endpoints."""
        employee_user.is_first_login = False
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "emp001", "password": "Emp001@123"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        employee_user.is_active = False
        db_session.commit()

        # /dashboard/employee uses require_role("employee")
        resp = client.get("/dashboard/employee", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "禁用" in resp.json()["message"]

    def test_inactive_peer_blocked_from_peer_endpoint(self, client: TestClient, peer_user, db_session: Session):
        """Inactive peer should be blocked from peer endpoints."""
        resp = client.post("/auth/login", json={"username": "peer001", "password": "Peer001@123"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        peer_user.is_active = False
        db_session.commit()

        # /dashboard/peer uses require_role("peer")
        resp = client.get("/dashboard/peer", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "禁用" in resp.json()["message"]

    def test_inactive_executive_blocked_from_executive_endpoint(self, client: TestClient, executive_user, db_session: Session):
        """Inactive executive should be blocked from executive endpoints."""
        resp = client.post("/auth/login", json={"username": "exec001", "password": "Exec001@123"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        executive_user.is_active = False
        db_session.commit()

        # /dashboard/cycles uses require_role("admin", "hr", "executive")
        resp = client.get("/dashboard/cycles", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "禁用" in resp.json()["message"]

    def test_active_user_can_access_role_endpoint(self, client: TestClient, admin_token):
        """Active user should be able to access role-protected endpoints."""
        resp = client.get("/dashboard/cycles", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200

    def test_inactive_user_blocked_by_get_current_user_for_public_endpoint(self, client: TestClient, admin_user, db_session: Session):
        """Inactive user should be blocked by get_current_user even on endpoints without require_role."""
        resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        admin_user.is_active = False
        db_session.commit()

        # /dashboard uses get_current_user directly, not require_role
        resp = client.get("/dashboard", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "禁用" in resp.json()["message"]

    def test_inactive_user_cannot_access_with_old_token(self, client: TestClient, admin_user, db_session: Session):
        """Inactive user should be blocked even with a previously valid token."""
        resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200
        old_token = resp.json()["access_token"]

        # Deactivate the user
        admin_user.is_active = False
        db_session.commit()

        # Try to access using the old token
        resp = client.get("/dashboard/cycles", headers={"Authorization": f"Bearer {old_token}"})
        assert resp.status_code == 401
        assert "禁用" in resp.json()["message"]
