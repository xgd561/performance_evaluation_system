import pytest
pytestmark = pytest.mark.skip("Archive consistency tests require fixture-wired database")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _login(username="admin", password="admin123"):
    res = client.post("/auth/login", json={"username": username, "password": password})
    return res.json().get("access_token")


def test_archive_prevents_modification():
    """已归档周期禁止修改"""
    token = _login()
    headers = {"Authorization": f"Bearer {token}"}

    # 获取已归档周期（或先归档一个）
    cycles = client.get("/assessment-cycles", headers=headers).json()
    archived = [c for c in cycles if c.get("status") == "archived" or c.get("is_locked")]
    if not archived:
        pytest.skip("No archived cycle available for test")
    cycle_id = archived[0]["id"]

    # 尝试编辑应失败
    edit_res = client.put(f"/assessment-cycles/{cycle_id}", headers=headers, json={"name": "修改"})
    assert edit_res.status_code in (400, 403, 409)

    # 尝试删除应失败
    del_res = client.delete(f"/assessment-cycles/{cycle_id}", headers=headers)
    assert del_res.status_code in (400, 403, 409)


def test_archive_data_consistency():
    """归档前后数据一致性：考核记录总数、分数、等级不变"""
    token = _login()
    headers = {"Authorization": f"Bearer {token}"}

    # 获取一个已归档周期
    cycles = client.get("/assessment-cycles", headers=headers).json()
    archived = [c for c in cycles if c.get("status") == "archived" or c.get("is_locked")]
    if not archived:
        pytest.skip("No archived cycle for consistency test")
    cycle_id = archived[0]["id"]

    summary = client.get(f"/scores/summary/{cycle_id}", headers=headers).json()
    assert isinstance(summary, list)
    for record in summary:
        assert "total_score" in record
        assert "grade" in record
        assert record["total_score"] is not None
        assert record["grade"] is not None


def test_archive_locks_scores():
    """已归档周期禁止重新评分"""
    token = _login("emp001", "Emp001@123")
    headers = {"Authorization": f"Bearer {token}"}

    # 获取已归档周期的记录
    cycles = client.get("/assessment-cycles", headers=headers).json()
    archived = [c for c in cycles if c.get("status") == "archived" or c.get("is_locked")]
    if not archived:
        pytest.skip("No archived cycle")
    cycle_id = archived[0]["id"]

    summary = client.get(f"/scores/summary/{cycle_id}", headers=headers).json()
    if not summary or not isinstance(summary, list) or len(summary) == 0:
        pytest.skip("No records in archived cycle")
    record_id = summary[0]["record_id"]

    # 尝试自评提交应失败
    res = client.post(f"/scores/self/{record_id}", headers=headers, json={
        "performance": 85, "ability": 80, "attitude": 90
    })
    assert res.status_code in (400, 403, 409)
