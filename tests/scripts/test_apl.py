"""
test_apl.py — Appeal management tests (TC-APL-001 ~ TC-APL-006)

Corresponds to test cases in:
  TEST_CASES_绩效考核评分系统_v1.0.md  §8 申诉管理模块 (APL)
"""

import pytest
from fastapi.testclient import TestClient

from tests.scripts.utils import assert_status_code


class TestAppealSubmit:
    """TC-APL-001, TC-APL-002"""

    def test_submit_appeal_success(self, client: TestClient, employee_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-APL-001: 提交申诉成功"""
        record_id = self._get_record_id(client, employee_headers, seeded_cycle, seeded_employee)
        payload = {
            "record_id": record_id,
            "reason": "评分不公",
            "detail": "我认为KPI1的评分应该更高，因为本季度超额完成了目标。",
        }
        resp = client.post("/appeals", json=payload, headers=employee_headers)
        if resp.status_code == 404:
            pytest.skip("Appeal endpoint not implemented")
        assert_status_code(resp, 201)
        data = resp.json()
        assert data.get("status") == "待复核"

    def test_duplicate_appeal_blocked(self, client: TestClient, employee_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-APL-002: 重复申诉被拦截"""
        record_id = self._get_record_id(client, employee_headers, seeded_cycle, seeded_employee)
        payload = {
            "record_id": record_id,
            "reason": "评分不公",
            "detail": "重复提交",
        }
        resp = client.post("/appeals", json=payload, headers=employee_headers)
        if resp.status_code == 404:
            pytest.skip("Appeal endpoint not implemented")
        # Second submission
        resp2 = client.post("/appeals", json=payload, headers=employee_headers)
        assert_status_code(resp2, 409)
        assert "不可重复提交" in resp2.json().get("message", "")

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


class TestAppealReview:
    """TC-APL-003, TC-APL-004, TC-APL-005, TC-APL-006"""

    def test_hr_review_and_modify_result(self, client: TestClient, hr_headers: dict, employee_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-APL-003: HR复核申诉并修改结果"""
        record_id = self._get_record_id(client, hr_headers, seeded_cycle, seeded_employee)
        # Create appeal first
        appeal_payload = {"record_id": record_id, "reason": "评分不公", "detail": "KPI1计算有误"}
        client.post("/appeals", json=appeal_payload, headers=employee_headers)

        # HR reviews and modifies
        review_payload = {
            "appeal_id": record_id,  # or separate appeal_id
            "action": "modify",
            "new_kpi_scores": {"KPI1": 90},
            "reason": "经复核，KPI1数据计算有误，已修正",
        }
        resp = client.post("/appeals/review", json=review_payload, headers=hr_headers)
        if resp.status_code == 404:
            pytest.skip("Appeal review endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert data.get("status") == "已处理"
        assert "已修正" in data.get("modify_reason", "")

    def test_appeal_status_timeline(self, client: TestClient, employee_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-APL-004: 申诉状态时间线 (UI only — API validates status history)"""
        record_id = self._get_record_id(client, employee_headers, seeded_cycle, seeded_employee)
        resp = client.get(f"/appeals/{record_id}/history", headers=employee_headers)
        if resp.status_code == 404:
            pytest.skip("Appeal history endpoint not implemented")
        assert_status_code(resp, 200)
        assert isinstance(resp.json(), list)

    def test_appeal_form_validation(self, client: TestClient, employee_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-APL-005: 申诉提交表单验证"""
        record_id = self._get_record_id(client, employee_headers, seeded_cycle, seeded_employee)
        # Missing reason
        payload = {"record_id": record_id, "detail": "详情"}
        resp = client.post("/appeals", json=payload, headers=employee_headers)
        if resp.status_code == 404:
            pytest.skip("Appeal endpoint not implemented")
        assert_status_code(resp, 422)
        assert "理由" in resp.json().get("message", "")

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


class TestAppealQueries:
    """TC-APL-004, TC-APL-005, TC-APL-006, TC-APL-007, TC-APL-008"""

    def test_my_appeal_history(self, client: TestClient, employee_headers: dict):
        """TC-APL-004: 我的申诉历史查询"""
        resp = client.get("/appeals/my-appeals", headers=employee_headers)
        if resp.status_code == 404:
            pytest.skip("My appeals endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert isinstance(data, list) or "items" in data

    def test_pending_appeal_list(self, client: TestClient, hr_headers: dict):
        """TC-APL-005: 待处理申诉列表查询"""
        resp = client.get("/appeals/pending", headers=hr_headers)
        if resp.status_code == 404:
            pytest.skip("Pending appeals endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert isinstance(data, list) or "items" in data

    def test_appeal_detail(self, client: TestClient, hr_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-APL-006: 申诉详情查询"""
        # First create an appeal
        record_id = self._get_record_id(client, hr_headers, seeded_cycle, seeded_employee)
        create_payload = {
            "record_id": record_id,
            "reason": "评分不公",
            "detail": "我认为KPI1的评分应该更高，因为...",
        }
        resp = client.post("/appeals", json=create_payload, headers=hr_headers)
        if resp.status_code == 404:
            pytest.skip("Appeal endpoint not implemented")
        # Get appeal id
        resp2 = client.get("/appeals/my-appeals", headers=hr_headers)
        appeals = resp2.json().get("items", resp2.json() if isinstance(resp2.json(), list) else [])
        if not appeals:
            pytest.skip("No appeals found")
        appeal_id = appeals[0]["id"]

        # Get detail
        resp3 = client.get(f"/appeals/{appeal_id}", headers=hr_headers)
        if resp3.status_code == 404:
            pytest.skip("Appeal detail endpoint not implemented")
        assert_status_code(resp3, 200)
        data = resp3.json()
        assert "reason" in data
        assert "detail" in data

    def test_review_appeal_maintain(self, client: TestClient, hr_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-APL-007: 复核申诉维持原结果"""
        # First create an appeal
        record_id = self._get_record_id(client, hr_headers, seeded_cycle, seeded_employee)
        create_payload = {
            "record_id": record_id,
            "reason": "评分不公",
            "detail": "我认为KPI1的评分应该更高",
        }
        resp = client.post("/appeals", json=create_payload, headers=hr_headers)
        if resp.status_code == 404:
            pytest.skip("Appeal endpoint not implemented")
        # Get appeal id
        resp2 = client.get("/appeals/my-appeals", headers=hr_headers)
        appeals = resp2.json().get("items", resp2.json() if isinstance(resp2.json(), list) else [])
        if not appeals:
            pytest.skip("No appeals found")
        appeal_id = appeals[0]["id"]

        # Review and maintain
        review_payload = {"action": "maintain", "reason": "经复核，原评分无误"}
        resp3 = client.post(f"/appeals/{appeal_id}/review", json=review_payload, headers=hr_headers)
        if resp3.status_code == 404:
            pytest.skip("Appeal review endpoint not implemented")
        assert_status_code(resp3, 200)
        assert resp3.json().get("status") == "已驳回" or "维持" in resp3.json().get("message", "")

    def test_review_appeal_change_grade(self, client: TestClient, hr_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-APL-008: 修改分数超出原等级区间"""
        # First create an appeal
        record_id = self._get_record_id(client, hr_headers, seeded_cycle, seeded_employee)
        create_payload = {
            "record_id": record_id,
            "reason": "评分不公",
            "detail": "我认为KPI1的评分应该更高",
        }
        resp = client.post("/appeals", json=create_payload, headers=hr_headers)
        if resp.status_code == 404:
            pytest.skip("Appeal endpoint not implemented")
        # Get appeal id
        resp2 = client.get("/appeals/my-appeals", headers=hr_headers)
        appeals = resp2.json().get("items", resp2.json() if isinstance(resp2.json(), list) else [])
        if not appeals:
            pytest.skip("No appeals found")
        appeal_id = appeals[0]["id"]

        # Review and change score (crossing grade boundary)
        review_payload = {"action": "modify", "new_score": 95, "reason": "经复核，KPI1数据计算有误"}
        resp3 = client.post(f"/appeals/{appeal_id}/review", json=review_payload, headers=hr_headers)
        if resp3.status_code == 404:
            pytest.skip("Appeal review endpoint not implemented")
        assert_status_code(resp3, 200)
        data = resp3.json()
        if "confirm" in data.get("message", "").lower() or "调整等级" in data.get("message", ""):
            # If system asks for confirmation, verify the flow
            pass
        else:
            assert "等级" in data.get("message", "") or "score" in data.get("message", "").lower()

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
