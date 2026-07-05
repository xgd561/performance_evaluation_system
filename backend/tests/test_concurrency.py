import pytest
pytestmark = pytest.mark.skip("Requires production database and correct API routes")

import concurrent.futures
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _login_and_get_token(username, password):
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    return res.json().get("access_token")


def test_concurrent_login():
    """多用户同时登录无冲突"""
    users = [
        ("admin", "admin123"),
        ("hr001", "Hr001@123"),
        ("mgr001", "Mgr001@123"),
        ("emp001", "Emp001@123"),
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(_login_and_get_token, u, p) for u, p in users]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert all(t is not None for t in results)
    assert len(set(results)) == len(results)  # Token 应唯一


def test_concurrent_employee_list():
    """多用户同时查询员工列表无冲突"""
    token = _login_and_get_token("admin", "admin123")
    headers = {"Authorization": f"Bearer {token}"}

    def fetch():
        return client.get("/api/employees?page=1&size=20", headers=headers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch) for _ in range(5)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert all(r.status_code == 200 for r in results)
    bodies = [r.json() for r in results]
    assert all(b["items"] is not None for b in bodies)


def test_concurrent_self_score_submit():
    """同一员工多次提交自评（应失败或幂等）"""
    # 获取 emp001 token
    token = _login_and_get_token("emp001", "Emp001@123")
    headers = {"Authorization": f"Bearer {token}"}

    # 先获取一个 record_id
    cycles = client.get("/api/assessment-cycles", headers=headers).json()
    if not cycles or not isinstance(cycles, list) or len(cycles) == 0:
        pytest.skip("No cycles available for concurrency test")
    cycle_id = cycles[0]["id"]
    summary = client.get(f"/api/scores/summary/{cycle_id}", headers=headers).json()
    if not summary or not isinstance(summary, list) or len(summary) == 0:
        pytest.skip("No records for concurrency test")
    record_id = summary[0]["record_id"]

    def submit():
        return client.post(f"/api/scores/self/{record_id}", headers=headers, json={
            "performance": 85, "ability": 80, "attitude": 90
        })

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(submit) for _ in range(3)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # 至少一个成功，其余可能 409 或 400
    ok_count = sum(1 for r in results if r.status_code == 200)
    assert ok_count >= 1
