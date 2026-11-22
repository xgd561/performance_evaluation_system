import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# 后端禁止创建开始日期早于今天的周期，这里用相对今天推算的日期
_CYCLE_START = (date.today() + timedelta(days=30)).isoformat()
_CYCLE_END = (date.today() + timedelta(days=60)).isoformat()


def _login(username="admin", password="admin123"):
    res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    return res.json().get("access_token")


def test_notification_after_cycle_launch():
    """启动考核后员工应收到通知（通过操作日志或状态变化验证）"""
    token = _login()
    headers = {"Authorization": f"Bearer {token}"}

    # 创建周期
    cycle_res = client.post("/api/v1/assessment-cycles", headers=headers, json={
        "name": "通知测试周期",
        "type": "monthly",
        "start_date": _CYCLE_START,
        "end_date": _CYCLE_END,
        "weights": {"self": 30, "manager": 50, "peer": 20},
        "grade_rules": {"A": 90, "B": 80, "C": 60, "D": 0}
    })
    assert cycle_res.status_code in (200, 201), cycle_res.text
    cycle_id = cycle_res.json()["id"]
    emps = client.get("/api/v1/employees?page=1&size=100", headers=headers).json()
    emp_ids = [e["id"] for e in emps["items"][:2]]

    # 启动
    launch_res = client.post("/api/v1/assessment-cycles/launch", headers=headers, json={
        "cycle_id": cycle_id, "employee_ids": emp_ids
    })
    assert launch_res.status_code == 200

    # 验证操作日志中有 launch 记录
    logs = client.get("/api/v1/logs", headers=headers).json()
    assert any("launch" in str(log.get("action", "")).lower() or "发起" in str(log.get("action", "")) for log in logs.get("items", []) if isinstance(log, dict))


def test_notification_after_self_submit():
    """员工自评提交后经理应收到通知（通过操作日志验证）"""
    # 获取员工 token
    emp_token = _login("emp001", "Emp001@123")
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # 获取一个 pending_self 的记录
    cycles = client.get("/api/v1/assessment-cycles", headers=emp_headers).json()
    if not cycles or not isinstance(cycles, list) or len(cycles) == 0:
        pytest.skip("No cycles for notification test")
    cycle_id = cycles[0]["id"]

    summary = client.get(f"/api/v1/scores/summary/{cycle_id}", headers=emp_headers).json()
    if not summary or not isinstance(summary, list) or len(summary) == 0:
        pytest.skip("No records for notification test")
    record_id = summary[0]["record_id"]

    # 提交自评
    res = client.post(f"/api/v1/scores/self/{record_id}", headers=emp_headers, json={
        "performance": 85, "ability": 80, "attitude": 90
    })
    if res.status_code == 200:
        # 验证操作日志
        admin_token = _login()
        logs = client.get("/api/v1/logs", headers={"Authorization": f"Bearer {admin_token}"}).json()
        assert any("self" in str(log.get("action", "")).lower() or "自评" in str(log.get("action", "")) for log in logs.get("items", []) if isinstance(log, dict))


def test_notification_after_appeal():
    """申诉提交后 HR 应收到通知（通过操作日志验证）"""
    emp_token = _login("emp001", "Emp001@123")
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    cycles = client.get("/api/v1/assessment-cycles", headers=emp_headers).json()
    if not cycles or not isinstance(cycles, list) or len(cycles) == 0:
        pytest.skip("No cycles")
    cycle_id = cycles[0]["id"]

    summary = client.get(f"/api/v1/scores/summary/{cycle_id}", headers=emp_headers).json()
    if not summary or not isinstance(summary, list) or len(summary) == 0:
        pytest.skip("No records")
    record_id = summary[0]["record_id"]

    res = client.post("/api/v1/appeals", headers=emp_headers, json={
        "record_id": record_id,
        "reason": "对评分结果有异议",
        "detail": "测试申诉通知"
    })
    if res.status_code in (200, 201):
        admin_token = _login()
        logs = client.get("/api/v1/logs", headers={"Authorization": f"Bearer {admin_token}"}).json()
        assert any("appeal" in str(log.get("action", "")).lower() or "申诉" in str(log.get("action", "")) for log in logs.get("items", []) if isinstance(log, dict))
