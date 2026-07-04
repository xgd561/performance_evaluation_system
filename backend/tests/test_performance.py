import pytest
import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_response_time():
    """健康检查接口响应时间 < 200ms"""
    start = time.perf_counter()
    res = client.get("/api/v1/health")
    elapsed = (time.perf_counter() - start) * 1000
    assert res.status_code == 200
    assert elapsed < 200


def test_employee_list_response_time():
    """员工列表接口响应时间 < 500ms"""
    # 先登录获取 token
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = login.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    start = time.perf_counter()
    res = client.get("/api/employees?page=1&size=20", headers=headers)
    elapsed = (time.perf_counter() - start) * 1000
    assert res.status_code == 200
    assert elapsed < 500


def test_cycle_list_response_time():
    """考核周期列表接口响应时间 < 500ms"""
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = login.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    start = time.perf_counter()
    res = client.get("/api/assessment-cycles", headers=headers)
    elapsed = (time.perf_counter() - start) * 1000
    assert res.status_code == 200
    assert elapsed < 500


def test_dashboard_response_time():
    """仪表盘接口响应时间 < 500ms"""
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = login.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    start = time.perf_counter()
    res = client.get("/api/dashboard", headers=headers)
    elapsed = (time.perf_counter() - start) * 1000
    assert res.status_code == 200
    assert elapsed < 500


def test_score_summary_response_time():
    """汇总接口响应时间 < 1000ms"""
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = login.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    # 获取一个周期 ID
    cycles = client.get("/api/assessment-cycles", headers=headers).json()
    if not cycles or not isinstance(cycles, list) or len(cycles) == 0:
        pytest.skip("No cycles available for performance test")
    cycle_id = cycles[0]["id"]

    start = time.perf_counter()
    res = client.get(f"/api/scores/summary/{cycle_id}", headers=headers)
    elapsed = (time.perf_counter() - start) * 1000
    assert res.status_code == 200
    assert elapsed < 1000
