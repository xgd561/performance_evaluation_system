"""P0-15: 首次登录强制改密的全局拦截。

产品口径：`is_first_login=True` 的用户只能访问认证白名单接口
（登录/刷新/我的信息/改密/登出），其余所有受保护接口一律返回 403。
"""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestFirstLoginGuard:
    def test_blocks_business_endpoint(
        self, client: TestClient, first_login_token, db_session: Session
    ):
        resp = client.get(
            "/employees?page=1&size=20",
            headers={"Authorization": f"Bearer {first_login_token}"},
        )

        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
        assert "修改初始密码" in resp.json()["message"]

    def test_allows_auth_me(
        self, client: TestClient, first_login_token, first_login_employee
    ):
        resp = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {first_login_token}"},
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.json()["username"] == first_login_employee.username

    def test_allows_logout(self, client: TestClient, first_login_token):
        resp = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {first_login_token}"},
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_change_password_unlocks_business_endpoints(
        self, client: TestClient, first_login_token, first_login_employee, db_session: Session
    ):
        resp = client.put(
            "/auth/password",
            json={"old_password": "Fl001@123", "new_password": "NewPass123"},
            headers={"Authorization": f"Bearer {first_login_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        db_session.refresh(first_login_employee)
        assert first_login_employee.is_first_login is False

        resp = client.get(
            "/employees?page=1&size=20",
            headers={"Authorization": f"Bearer {first_login_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"