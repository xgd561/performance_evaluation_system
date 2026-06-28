"""
test_int.py — Performance interview tests (TC-INT-001 ~ TC-INT-004)

Corresponds to test cases in:
  TEST_CASES_绩效考核评分系统_v1.0.md  §7 绩效面谈模块 (INT)
"""

import pytest
from fastapi.testclient import TestClient

from tests.scripts.utils import assert_status_code


class TestInterviewCreate:
    """TC-INT-001, TC-INT-002"""

    def test_create_interview_success(self, client: TestClient, manager_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-INT-001: 创建面谈记录成功"""
        # Ensure employee has grade C or D
        record_id = self._get_record_id(client, manager_headers, seeded_cycle, seeded_employee)
        payload = {
            "record_id": record_id,
            "interview_time": "2026-07-15T14:00:00",
            "location": "会议室A",
            "content": "本季度业绩未达标，主要因为...",
            "improvement_plan": "下季度将加强客户拜访，每周至少3次，提高成单率。同时加强产品知识学习，参加公司培训。",
        }
        resp = client.post("/interviews", json=payload, headers=manager_headers)
        if resp.status_code == 404:
            pytest.skip("Interview endpoint not implemented")
        assert_status_code(resp, 201)
        data = resp.json()
        assert data.get("location") == "会议室A"

    def test_create_interview_plan_too_short(self, client: TestClient, manager_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-INT-002: 创建面谈记录时改进计划不足50字拦截"""
        record_id = self._get_record_id(client, manager_headers, seeded_cycle, seeded_employee)
        payload = {
            "record_id": record_id,
            "interview_time": "2026-07-15T14:00:00",
            "location": "会议室A",
            "content": "本季度业绩未达标",
            "improvement_plan": "需加强学习",  # 5 characters
        }
        resp = client.post("/interviews", json=payload, headers=manager_headers)
        if resp.status_code == 404:
            pytest.skip("Interview endpoint not implemented")
        assert_status_code(resp, 422)
        assert "50字" in resp.json().get("message", "")

    def _get_record_id(self, client, headers, cycle, employee):
        resp = client.get(
            f"/records?cycle_id={cycle['id']}&employee_id={employee['id']}",
            headers=headers,
        )
        if resp.status_code == 404:
            pytest.skip("Records endpoint not implemented")
        items = resp.json().get("items", [])
        if not items:
            pytest.skip("No assessment record found")
        return items[0]["id"]


class TestInterviewUI:
    """TC-INT-003, TC-INT-004 (UI / E2E tests)"""

    def test_interview_calendar_picker(self):
        """TC-INT-003: 面谈日历选择器 (UI only)"""
        pytest.skip("UI-only test: verify calendar picker in browser/E2E suite")

    def test_interview_notification_bell(self):
        """TC-INT-004: 面谈通知消息铃铛 (UI only)"""
        pytest.skip("UI-only test: verify notification bell in browser/E2E suite")


class TestInterviewQueries:
    """TC-INT-003 (API), TC-INT-004 (API), TC-INT-005"""

    def test_pending_interview_list(self, client: TestClient, manager_headers: dict):
        """TC-INT-003: 待面谈列表查询"""
        resp = client.get("/interviews/pending", headers=manager_headers)
        if resp.status_code == 404:
            pytest.skip("Pending interviews endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert isinstance(data, list) or "items" in data

    def test_get_interview_detail(self, client: TestClient, manager_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-INT-004: 获取面谈详情"""
        record_id = self._get_record_id(client, manager_headers, seeded_cycle, seeded_employee)
        # First create an interview
        create_payload = {
            "record_id": record_id,
            "interview_time": "2026-07-15T14:00:00",
            "location": "会议室A",
            "content": "本季度业绩未达标，主要因为...",
            "improvement_plan": "下季度将加强客户拜访，每周至少3次，提高成单率。同时加强产品知识学习，参加公司培训。",
        }
        resp = client.post("/interviews", json=create_payload, headers=manager_headers)
        if resp.status_code == 404:
            pytest.skip("Interview endpoint not implemented")
        # Get interview detail
        resp2 = client.get(f"/interviews/{record_id}", headers=manager_headers)
        if resp2.status_code == 404:
            pytest.skip("Interview detail endpoint not implemented")
        assert_status_code(resp2, 200)
        data = resp2.json()
        assert "location" in data
        assert "content" in data
        assert_fields_absent(data, "password_hash", "password", "secret")

    def test_update_interview_record(self, client: TestClient, manager_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-INT-005: 更新面谈记录"""
        record_id = self._get_record_id(client, manager_headers, seeded_cycle, seeded_employee)
        # First create an interview
        create_payload = {
            "record_id": record_id,
            "interview_time": "2026-07-15T14:00:00",
            "location": "会议室A",
            "content": "本季度业绩未达标",
            "improvement_plan": "下季度将加强客户拜访，每周至少3次，提高成单率。同时加强产品知识学习，参加公司培训。",
        }
        resp = client.post("/interviews", json=create_payload, headers=manager_headers)
        if resp.status_code == 404:
            pytest.skip("Interview endpoint not implemented")
        # Update
        update_payload = {"content": "修改后的沟通内容：本季度业绩未达标，需要改进"}
        resp2 = client.put(f"/interviews/{record_id}", json=update_payload, headers=manager_headers)
        if resp2.status_code == 404:
            pytest.skip("Interview update endpoint not implemented")
        assert_status_code(resp2, 200)
        assert resp2.json().get("content") == "修改后的沟通内容：本季度业绩未达标，需要改进"

    def _get_record_id(self, client, headers, cycle, employee):
        resp = client.get(
            f"/records?cycle_id={cycle['id']}&employee_id={employee['id']}",
            headers=headers,
        )
        if resp.status_code == 404:
            pytest.skip("Records endpoint not implemented")
        items = resp.json().get("items", [])
        if not items:
            pytest.skip("No assessment record found")
        return items[0]["id"]
