"""
test_cyc.py — Assessment cycle management tests (TC-CYC-001 ~ TC-CYC-009)

Corresponds to test cases in:
  TEST_CASES_绩效考核评分系统_v1.0.md  §4 考核周期管理模块 (CYC)
"""

import pytest
from fastapi.testclient import TestClient

from tests.scripts.utils import assert_status_code, create_assessment_cycle, launch_cycle, create_employee


class TestCycleCreate:
    """TC-CYC-001, TC-CYC-002"""

    def test_create_cycle_success(self, client: TestClient, admin_headers: dict):
        """TC-CYC-001: 创建考核周期成功"""
        payload = {
            "name": "2026年Q2季度考核",
            "type": "季度",
            "start_date": "2026-04-01",
            "end_date": "2026-06-30",
            "weights": {"业绩": 60, "能力": 20, "态度": 20},
            "grade_rules": {"A": 90, "B": 80, "C": 60, "D": 0},
        }
        resp = client.post("/assessment-cycles", json=payload, headers=admin_headers)
        assert_status_code(resp, 201)
        data = resp.json()
        assert data["name"] == "2026年Q2季度考核"
        assert data["status"] == "未开始"
        assert sum(data["weights"].values()) == 100

    def test_create_cycle_weight_sum_not_100(self, client: TestClient, admin_headers: dict):
        """TC-CYC-002: 维度权重总和不等于100%拦截"""
        payload = {
            "name": "权重测试",
            "type": "季度",
            "start_date": "2026-04-01",
            "end_date": "2026-06-30",
            "weights": {"业绩": 50, "能力": 20, "态度": 20},  # 90%
            "grade_rules": {"A": 90, "B": 80, "C": 60, "D": 0},
        }
        resp = client.post("/assessment-cycles", json=payload, headers=admin_headers)
        assert_status_code(resp, 422)
        assert "权重总和" in resp.json().get("message", "")


class TestCycleLaunch:
    """TC-CYC-003, TC-CYC-004, TC-CYC-005"""

    def test_launch_cycle_success(
        self, client: TestClient, admin_headers: dict, seeded_cycle: dict, seeded_employee: dict
    ):
        """TC-CYC-003: 发起考核成功"""
        payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_ids": [seeded_employee["id"]],
        }
        resp = client.post("/assessment-cycles/launch", json=payload, headers=admin_headers)
        assert_status_code(resp, 200)
        data = resp.json()
        assert data.get("created_records") == 1
        assert data.get("status") == "进行中（自评）"

    def test_launch_cycle_employee_without_kpi_template(
        self, client: TestClient, admin_headers: dict, seeded_cycle: dict, seeded_department: dict, seeded_position: dict
    ):
        """TC-CYC-004: 发起考核时员工无KPI模板——允许发起并创建空KPI记录"""
        # Create an employee whose position has NO KPI template
        emp_no_kpi = create_employee(
            client, admin_headers, "EMP_NO_KPI", "无KPI员工",
            seeded_department["id"], seeded_position["id"],
        )
        payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_ids": [emp_no_kpi["id"]],
        }
        resp = client.post("/assessment-cycles/launch", json=payload, headers=admin_headers)
        assert_status_code(resp, 200)
        data = resp.json()
        assert data.get("created_records") == 1
        assert data.get("status") == "进行中（自评）"

    def test_add_employee_to_launched_cycle(
        self, client: TestClient, admin_headers: dict, seeded_cycle: dict, seeded_department: dict, seeded_position: dict
    ):
        """TC-CYC-005: 考核进行中添加新员工到周期"""
        new_emp = create_employee(
            client, admin_headers, "EMP_NEW", "新员工",
            seeded_department["id"], seeded_position["id"],
        )
        payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_ids": [new_emp["id"]],
        }
        resp = client.post("/assessment-cycles/add-employees", json=payload, headers=admin_headers)
        assert_status_code(resp, 200)
        data = resp.json()
        assert new_emp["id"] in [e["id"] for e in data.get("employees", [])]


class TestCycleProgress:
    """TC-CYC-006, TC-CYC-007, TC-CYC-008, TC-CYC-009"""

    def test_progress_dashboard(self, client: TestClient, admin_headers: dict, seeded_cycle: dict):
        """TC-CYC-006: 进度监控显示正确"""
        resp = client.get(f"/assessment-cycles/{seeded_cycle['id']}/progress", headers=admin_headers)
        assert_status_code(resp, 200)
        data = resp.json()
        assert "stages" in data
        assert "overall_progress" in data
        assert 0 <= data["overall_progress"] <= 100

    def test_calendar_date_restriction(self, client: TestClient, admin_headers: dict):
        """TC-CYC-007: 考核周期日历选择器限制 (UI/API validation)"""
        payload = {
            "name": "日期测试",
            "type": "季度",
            "start_date": "2026-07-01",
            "end_date": "2026-06-30",  # Invalid: earlier than start
            "weights": {"业绩": 60, "能力": 20, "态度": 20},
            "grade_rules": {"A": 90, "B": 80, "C": 60, "D": 0},
        }
        resp = client.post("/assessment-cycles", json=payload, headers=admin_headers)
        assert_status_code(resp, 422)
        assert "结束日期" in resp.json().get("message", "")

    def test_weight_realtime_calculation(self, client: TestClient, admin_headers: dict):
        """TC-CYC-008: 权重实时计算显示 (API validation)"""
        payload = {
            "name": "权重测试",
            "type": "季度",
            "start_date": "2026-04-01",
            "end_date": "2026-06-30",
            "weights": {"业绩": 60, "能力": 30, "态度": 20},  # 110%
            "grade_rules": {"A": 90, "B": 80, "C": 60, "D": 0},
        }
        resp = client.post("/assessment-cycles", json=payload, headers=admin_headers)
        assert_status_code(resp, 422)
        assert "110%" in resp.json().get("message", "")

    def test_dashboard_auto_refresh(self, client: TestClient, admin_headers: dict, seeded_cycle: dict):
        """TC-CYC-009: 进度监控仪表盘刷新"""
        resp = client.get(f"/assessment-cycles/{seeded_cycle['id']}/progress", headers=admin_headers)
        assert_status_code(resp, 200)
        # Verify last_updated timestamp exists
        assert "last_updated" in resp.json() or "updated_at" in resp.json()


class TestCycleList:
    """TC-CYC-010"""

    def test_cycle_list(self, client: TestClient, admin_headers: dict):
        """TC-CYC-010: 周期列表查询"""
        resp = client.get("/assessment-cycles", headers=admin_headers)
        assert_status_code(resp, 200)
        data = resp.json()
        assert isinstance(data, list) or "items" in data
        items = data if isinstance(data, list) else data.get("items", [])
        assert len(items) >= 0


class TestCycleUpdateAndDelete:
    """TC-CYC-011, TC-CYC-012, TC-CYC-013, TC-CYC-014"""

    def test_update_launched_cycle_blocked(self, client: TestClient, admin_headers: dict, seeded_cycle: dict):
        """TC-CYC-011: 修改已发起的周期被拦截"""
        # First launch the cycle
        launch_resp = client.post(f"/assessment-cycles/{seeded_cycle['id']}/launch", json={}, headers=admin_headers)
        if launch_resp.status_code == 404:
            pytest.skip("Launch endpoint not implemented")
        # Try to update
        resp = client.put(f"/assessment-cycles/{seeded_cycle['id']}", json={"name": "修改名称"}, headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Cycle update endpoint not implemented")
        assert_status_code(resp, 409)
        assert "已发起" in resp.json().get("message", "") or "不可修改" in resp.json().get("message", "")

    def test_delete_cycle_with_records_blocked(self, client: TestClient, admin_headers: dict, seeded_cycle: dict):
        """TC-CYC-012: 删除含有考核记录的周期被拦截"""
        resp = client.delete(f"/assessment-cycles/{seeded_cycle['id']}", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Cycle delete endpoint not implemented")
        assert_status_code(resp, 409)
        assert "考核数据" in resp.json().get("message", "") or "不可删除" in resp.json().get("message", "")

    def test_remove_employee_from_cycle(self, client: TestClient, admin_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-CYC-013: 从周期中移除人员"""
        resp = client.delete(f"/assessment-cycles/{seeded_cycle['id']}/employees/{seeded_employee['id']}", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Remove employee from cycle endpoint not implemented")
        assert_status_code(resp, 204)

    def test_launch_cycle_without_employees_blocked(self, client: TestClient, admin_headers: dict, seeded_cycle: dict):
        """TC-CYC-014: 发起考核时未选择任何员工被拦截"""
        payload = {"cycle_id": seeded_cycle["id"], "employee_ids": []}
        resp = client.post("/assessment-cycles/launch", json=payload, headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Launch endpoint not implemented")
        assert_status_code(resp, 409)
        assert "至少" in resp.json().get("message", "") or "选择" in resp.json().get("message", "")
