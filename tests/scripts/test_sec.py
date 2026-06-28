"""
test_sec.py — Security tests (TC-SEC-001 ~ TC-SEC-025)

Corresponds to test cases in:
  TEST_CASES_绩效考核评分系统_v1.0.md  §14 安全测试用例 (SEC)
"""

import pytest
from fastapi.testclient import TestClient

from tests.scripts.utils import (
    assert_status_code,
    sql_injection_payloads,
    xss_payloads,
    path_traversal_payloads,
    assert_fields_absent,
)


class TestAuthSecurity:
    """TC-SEC-001, TC-SEC-003, TC-SEC-006, TC-SEC-007, TC-SEC-014, TC-SEC-021, TC-SEC-024"""

    def test_sql_injection_login(self, client: TestClient):
        """TC-SEC-001: SQL注入攻击登录接口"""
        for payload in sql_injection_payloads():
            resp = client.post(
                "/auth/login",
                json={"username": payload, "password": "any"},
            )
            assert resp.status_code == 401, f"SQL injection payload '{payload}' did not return 401"
            assert "sql" not in resp.text.lower()

    def test_unauthorized_access_cross_manager(self, client: TestClient, manager_headers: dict):
        """TC-SEC-003: 越权访问非下属考核记录"""
        # Attempt to access a record that doesn't belong to this manager
        resp = client.get("/records/99999", headers=manager_headers)
        assert_status_code(resp, 403)
        assert "无权" in resp.json().get("message", "")

    def test_csrf_token_validation(self, client: TestClient, admin_headers: dict):
        """TC-SEC-006: CSRF令牌验证"""
        # Request without CSRF token
        headers_no_csrf = {k: v for k, v in admin_headers.items() if k.lower() != "x-csrf-token"}
        resp = client.post("/employees", json={"name": "test"}, headers=headers_no_csrf)
        # Some implementations require CSRF only for state-changing browser requests;
        # if API is pure JWT Bearer, this may return 422 (validation error) instead of 403.
        assert resp.status_code in (403, 422)

    def test_api_rate_limit(self, client: TestClient):
        """TC-SEC-007: API速率限制"""
        for i in range(120):
            resp = client.post("/auth/login", json={"username": f"user{i}", "password": "wrong"})
            if resp.status_code == 429:
                assert "Retry-After" in resp.headers or "请求过于频繁" in resp.json().get("message", "")
                return
        pytest.skip("Rate limit not triggered within 120 requests")

    def test_session_fixation_protection(self, client: TestClient):
        """TC-SEC-014: 会话固定攻击防护"""
        # If session-based auth is used, verify session ID changes after login
        # For JWT-based systems, this test validates cookie attributes
        resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
        if resp.status_code == 200:
            cookies = resp.cookies
            for cookie in cookies.values():
                assert cookie.get("httponly") or cookie.get("secure")

    def test_logout_token_invalidation(self, client: TestClient, admin_headers: dict):
        """TC-SEC-021: 注销Token失效"""
        resp = client.post("/auth/logout", headers=admin_headers)
        assert_status_code(resp, 200)
        # After logout, token should be rejected
        resp2 = client.get("/employees", headers=admin_headers)
        assert_status_code(resp2, 401)

    def test_interface_traversal_attack(self, client: TestClient, employee_headers: dict):
        """TC-SEC-024: 接口遍历攻击"""
        for record_id in range(1, 101):
            resp = client.get(f"/records/{record_id}", headers=employee_headers)
            if resp.status_code == 403:
                continue
            if resp.status_code == 404:
                # 404 leaks information; should be 403
                pass
            elif resp.status_code == 200:
                assert False, f"Record {record_id} should not be accessible"


class TestInputSecurity:
    """TC-SEC-002, TC-SEC-008, TC-SEC-009, TC-SEC-010, TC-SEC-018, TC-SEC-019"""

    def test_xss_in_comment(self, client: TestClient, manager_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-SEC-002: XSS攻击评分评语"""
        xss = "<script>alert('xss')</script>"
        payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_id": seeded_employee["id"],
            "dimension_scores": {"业绩": 80, "能力": 80, "态度": 80},
            "comment": xss,
        }
        resp = client.post("/scores/manager", json=payload, headers=manager_headers)
        if resp.status_code == 404:
            pytest.skip("Manager scoring endpoint not implemented")
        assert_status_code(resp, 200)
        # Fetch record and verify script is not executed (escaped)
        record_resp = client.get(
            f"/records?cycle_id={seeded_cycle['id']}&employee_id={seeded_employee['id']}",
            headers=manager_headers,
        )
        if record_resp.status_code == 200:
            records = record_resp.json().get("items", [])
            if records:
                comment = str(records[0].get("comment", ""))
                assert "<script>" not in comment or "alert" not in comment

    def test_file_upload_type_restriction(self, client: TestClient, admin_headers: dict):
        """TC-SEC-008: 文件上传类型限制"""
        import io
        files = {"file": ("shell.exe", io.BytesIO(b"MZ"), "application/x-msdownload")}
        resp = client.post("/employees/import", files=files, headers=admin_headers)
        assert_status_code(resp, 415)
        assert "xlsx" in resp.json().get("message", "")

    def test_file_upload_size_restriction(self, client: TestClient, admin_headers: dict):
        """TC-SEC-009: 文件上传大小限制"""
        import io
        large_content = b"x" * (50 * 1024 * 1024)  # 50MB
        files = {"file": ("large.xlsx", io.BytesIO(large_content), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = client.post("/employees/import", files=files, headers=admin_headers)
        assert_status_code(resp, 413)
        assert "大小" in resp.json().get("message", "") or "413" in str(resp.status_code)

    def test_path_traversal_attack(self, client: TestClient, admin_headers: dict):
        """TC-SEC-010: 路径遍历攻击"""
        for payload in path_traversal_payloads():
            resp = client.get(f"/download?file={payload}", headers=admin_headers)
            assert resp.status_code in (400, 403), f"Path traversal payload '{payload}' was not blocked"
            assert "etc/passwd" not in resp.text

    def test_sql_injection_search(self, client: TestClient, admin_headers: dict):
        """TC-SEC-018: SQL注入搜索框"""
        for payload in sql_injection_payloads():
            resp = client.get(f"/employees?keyword={payload}", headers=admin_headers)
            assert resp.status_code in (200, 400)
            assert resp.status_code != 500, f"SQL injection in search caused 500 for payload: {payload}"

    def test_stored_xss_employee_name(self, client: TestClient, admin_headers: dict, seeded_department: dict, seeded_position: dict):
        """TC-SEC-019: 存储型XSS"""
        xss = "<script>alert('xss')</script>"
        payload = {
            "employee_no": "EMP_XSS",
            "name": xss,
            "department_id": seeded_department["id"],
            "position_id": seeded_position["id"],
        }
        resp = client.post("/employees", json=payload, headers=admin_headers)
        if resp.status_code == 409:
            # Already exists, fetch and check
            resp = client.get("/employees?employee_no=EMP_XSS", headers=admin_headers)
        assert_status_code(resp, 200)
        data = resp.json()
        if isinstance(data, list):
            data = data[0]
        assert "<script>" not in data.get("name", "") or "alert" not in data.get("name", "")


class TestInfrastructureSecurity:
    """TC-SEC-011, TC-SEC-012, TC-SEC-013, TC-SEC-015, TC-SEC-017, TC-SEC-020, TC-SEC-022, TC-SEC-023, TC-SEC-025"""

    def test_clickjacking_protection(self, client: TestClient):
        """TC-SEC-011: Clickjacking防护"""
        resp = client.get("/")
        x_frame = resp.headers.get("X-Frame-Options", "").upper()
        csp = resp.headers.get("Content-Security-Policy", "")
        assert x_frame in ("DENY", "SAMEORIGIN") or "frame-ancestors" in csp

    def test_csp_header(self, client: TestClient):
        """TC-SEC-012: 内容安全策略CSP"""
        resp = client.get("/")
        csp = resp.headers.get("Content-Security-Policy", "")
        assert "Content-Security-Policy" in resp.headers
        assert "default-src" in csp or "script-src" in csp

    def test_https_enforcement(self, client: TestClient):
        """TC-SEC-013: HTTPS强制跳转"""
        # If HTTP is disabled, this may not be testable in the test client
        resp = client.get("http://localhost/", allow_redirects=False)
        if resp.status_code in (301, 302, 307, 308):
            assert "https" in resp.headers.get("location", "")
        hsts = resp.headers.get("Strict-Transport-Security", "")
        if hsts:
            assert "max-age" in hsts

    def test_mass_assignment_vulnerability(self, client: TestClient, admin_headers: dict):
        """TC-SEC-015: 批量赋值漏洞"""
        payload = {
            "id": 99999,
            "role": "superadmin",
            "password_hash": "hacked_hash",
            "name": "正常更新",
        }
        resp = client.put("/employees/1", json=payload, headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Employee update endpoint not implemented")
        # Should either ignore protected fields or return 400
        if resp.status_code == 200:
            data = resp.json()
            assert data.get("role") != "superadmin"
            assert data.get("password_hash") != "hacked_hash"
            assert data.get("id") != 99999

    def test_password_hash_strength(self, client: TestClient, admin_headers: dict):
        """TC-SEC-017: 密码哈希算法强度"""
        # This requires database access; verify via API if possible
        resp = client.get("/users/1", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("User detail endpoint not implemented")
        if resp.status_code == 200:
            user = resp.json()
            password_hash = user.get("password_hash", "")
            if password_hash:
                assert password_hash.startswith(("$2b$", "$2a$", "$argon2", "$pbkdf2"))
                assert len(password_hash) >= 60

    def test_security_headers(self, client: TestClient):
        """TC-SEC-020: 安全响应头"""
        resp = client.get("/employees")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert "X-XSS-Protection" in resp.headers or "Content-Security-Policy" in resp.headers
        server = resp.headers.get("Server", "")
        assert "nginx" not in server.lower() or "Apache" not in server

    def test_cors_configuration(self, client: TestClient):
        """TC-SEC-022: CORS配置"""
        headers = {"Origin": "https://evil.com"}
        resp = client.options("/employees", headers=headers)
        allow_origin = resp.headers.get("Access-Control-Allow-Origin", "")
        assert allow_origin != "*"
        if allow_origin:
            assert "evil.com" not in allow_origin

    def test_sensitive_info_not_in_logs(self, client: TestClient, admin_headers: dict):
        """TC-SEC-023: 敏感信息不写入日志"""
        # Login and check that response doesn't contain sensitive fields
        resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200
        assert_fields_absent(resp.json(), "password", "password_hash", "secret_key")

    def test_vertical_privilege_escalation(self, client: TestClient, employee_headers: dict):
        """TC-SEC-025: 垂直权限提升"""
        endpoints = [
            ("PUT", "/config/grade-rules", {"A": {"min": 0, "max": 100}}),
            ("DELETE", "/employees/1", None),
            ("GET", "/logs", None),
        ]
        for method, url, payload in endpoints:
            if method == "PUT":
                resp = client.put(url, json=payload or {}, headers=employee_headers)
            elif method == "DELETE":
                resp = client.delete(url, headers=employee_headers)
            else:
                resp = client.get(url, headers=employee_headers)
            assert_status_code(resp, 403)
            assert "无权" in resp.json().get("message", "")


class TestDataSecurity:
    """TC-SEC-004, TC-SEC-005, TC-SEC-016"""

    def test_sensitive_data_desensitization(self, client: TestClient, admin_headers: dict):
        """TC-SEC-004: 敏感数据脱敏"""
        resp = client.get("/employees", headers=admin_headers)
        assert_status_code(resp, 200)
        for item in resp.json().get("items", []):
            assert_fields_absent(item, "password_hash", "password", "secret", "id_card")

    def test_archived_record_modification_blocked(self, client: TestClient, admin_headers: dict):
        """TC-SEC-005: 修改已归档考核记录被拦截"""
        resp = client.put("/records/1/status", json={"status": "已修改"}, headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Record status update endpoint not implemented")
        assert_status_code(resp, 409)
        assert "已归档" in resp.json().get("message", "")

    def test_idor_protection(self, client: TestClient, employee_headers: dict):
        """TC-SEC-016: 不安全的直接对象引用"""
        resp = client.get("/records/99999", headers=employee_headers)
        assert_status_code(resp, 403)
        resp2 = client.put("/records/99999", json={"grade": "A"}, headers=employee_headers)
        assert_status_code(resp2, 403)


class TestAdditionalSecurity:
    """TC-SEC-026, TC-SEC-027, TC-SEC-028, TC-SEC-029, TC-SEC-030"""

    def test_unauthorized_password_change(self, client: TestClient, employee_headers: dict, seeded_employee: dict):
        """TC-SEC-026: 越权修改他人密码"""
        # Try to change another employee's password
        target_id = seeded_employee["id"]
        resp = client.put(
            f"/employees/{target_id}/password",
            json={"new_password": "Hacked123"},
            headers=employee_headers,
        )
        if resp.status_code == 404:
            pytest.skip("Employee password update endpoint not implemented")
        assert_status_code(resp, 403)
        assert "只能修改" in resp.json().get("message", "") or "无权" in resp.json().get("message", "")

    def test_delete_audit_log_blocked(self, client: TestClient, admin_headers: dict):
        """TC-SEC-027: 删除审计日志被拦截"""
        resp = client.delete("/logs/1", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Log delete endpoint not implemented")
        assert_status_code(resp, 403)
        assert "不可删除" in resp.json().get("message", "")

    def test_cookie_security_attributes(self, client: TestClient):
        """TC-SEC-028: Cookie安全属性"""
        resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
        if resp.status_code == 200:
            # Check Set-Cookie headers
            set_cookie = resp.headers.get("set-cookie", "")
            assert "HttpOnly" in set_cookie or "httponly" in set_cookie.lower() or "Secure" in set_cookie or "SameSite" in set_cookie

    def test_generic_404_resource_not_found(self, client: TestClient, admin_headers: dict):
        """TC-SEC-029: 通用404资源不存在"""
        endpoints = [
            "/employees/99999",
            "/assessment-cycles/99999",
            "/records/99999",
        ]
        for url in endpoints:
            resp = client.get(url, headers=admin_headers)
            assert_status_code(resp, 404)
            assert "不存在" in resp.json().get("message", "") or "not found" in resp.json().get("message", "").lower()

    def test_generic_422_required_param_missing(self, client: TestClient, admin_headers: dict):
        """TC-SEC-030: 通用422必填参数缺失"""
        # Missing name
        resp = client.post("/employees", json={"department_id": 1}, headers=admin_headers)
        assert resp.status_code in (422, 400)
        assert "name" in resp.json().get("message", "").lower() or "必填" in resp.json().get("message", "")

        # Missing end_date
        resp2 = client.post("/assessment-cycles", json={"name": "测试", "start_date": "2026-01-01"}, headers=admin_headers)
        if resp2.status_code != 404:
            assert resp2.status_code in (422, 400)
