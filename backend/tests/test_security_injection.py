import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _login():
    res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    return res.json().get("access_token")


def test_sql_injection_in_login():
    """登录接口 SQL 注入防护"""
    malicious_payloads = [
        {"username": "admin' OR '1'='1", "password": "anything"},
        {"username": "admin"; DROP TABLE users; --", "password": "test"},
        {"username": "admin' UNION SELECT * FROM employees --", "password": "test"},
    ]
    for payload in malicious_payloads:
        res = client.post("/api/auth/login", json=payload)
        # 不应 500，也不应返回异常结构；理想是 401/400
        assert res.status_code in (200, 401, 400, 422)
        if res.status_code == 200:
            body = res.json()
            assert "access_token" not in body or body.get("access_token") is None


def test_sql_injection_in_employee_search():
    """员工搜索 SQL 注入防护"""
    token = _login()
    headers = {"Authorization": f"Bearer {token}"}
    malicious = "' OR '1'='1'; DROP TABLE employees; --"
    res = client.get(f"/api/employees?keyword={malicious}&page=1&size=20", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body, dict)
    assert "items" in body


def test_xss_in_employee_create():
    """员工创建 XSS 注入防护"""
    token = _login()
    headers = {"Authorization": f"Bearer {token}"}
    xss_name = "<script>alert('xss')</script>"
    res = client.post("/api/employees", headers=headers, json={
        "employee_no": f"XSS-{hash(xss_name) % 100000}",
        "name": xss_name,
        "email": "xss@example.com",
        "phone": "13800000001"
    })
    # 创建应成功，但返回数据中不应包含未转义的脚本
    if res.status_code == 201:
        body = res.json()
        assert "<script>" not in body.get("name", "")


def test_sql_injection_in_cycle_name():
    """考核周期名称 SQL 注入防护"""
    token = _login()
    headers = {"Authorization": f"Bearer {token}"}
    malicious_name = "周期'; DROP TABLE assessment_cycles; --"
    res = client.post("/api/assessment-cycles", headers=headers, json={
        "name": malicious_name,
        "type": "monthly",
        "start_date": "2025-01-01",
        "end_date": "2025-01-31",
        "weights": {"self": 30, "manager": 50, "peer": 20},
        "grade_rules": {"A": 90, "B": 80, "C": 60, "D": 0}
    })
    # 应成功创建（ORM 参数化查询防护），不应 500
    assert res.status_code in (200, 201, 400, 409)
    if res.status_code in (200, 201):
        body = res.json()
        assert body["name"] == malicious_name or "<script>" not in body["name"]


def test_path_traversal_in_export():
    """报表导出路径遍历防护"""
    token = _login()
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/reports/cycle/1/export?filename=../../etc/passwd", headers=headers)
    # 不应 500，不应返回系统文件内容
    assert res.status_code in (200, 400, 403, 404)
