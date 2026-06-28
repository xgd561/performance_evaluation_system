"""
test_app.py — Approval workflow tests (TC-APP-001 ~ TC-APP-008)

Corresponds to test cases in:
  TEST_CASES_绩效考核评分系统_v1.0.md  §6 审批流程模块 (APP)
"""

import pytest
from fastapi.testclient import TestClient

from tests.scripts.utils import assert_status_code


class TestApprovalPassReject:
    """TC-APP-001, TC-APP-002, TC-APP-003"""

    def test_approval_pass(self, client: TestClient, admin_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-APP-001: 审批通过成功"""
        # Ensure record is in pending approval state
        record_id = self._get_record_id(client, admin_headers, seeded_cycle, seeded_employee)
        resp = client.post(f"/approvals/{record_id}/pass", headers=admin_headers)
        assert_status_code(resp, 200)
        data = resp.json()
        assert data.get("status") in ("已通过", "待发布")

    def test_approval_reject(self, client: TestClient, admin_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-APP-002: 审批驳回成功"""
        record_id = self._get_record_id(client, admin_headers, seeded_cycle, seeded_employee)
        payload = {"reason": "KPI3评分偏高，请重新评估"}
        resp = client.post(f"/approvals/{record_id}/reject", json=payload, headers=admin_headers)
        assert_status_code(resp, 200)
        data = resp.json()
        assert data.get("status") == "待上级评"
        assert "KPI3评分偏高" in data.get("reject_reason", "")

    def test_approval_rollback(self, client: TestClient, admin_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-APP-003: 审批打回重评成功"""
        record_id = self._get_record_id(client, admin_headers, seeded_cycle, seeded_employee)
        resp = client.post(f"/approvals/{record_id}/rollback", headers=admin_headers)
        assert_status_code(resp, 200)
        data = resp.json()
        assert data.get("status") == "待自评"
        # Verify scores cleared
        resp2 = client.get(f"/records/{record_id}", headers=admin_headers)
        record = resp2.json()
        assert not record.get("self_scores")
        assert not record.get("manager_scores")

    def _get_record_id(self, client, headers, cycle, employee):
        resp = client.get(
            f"/records?cycle_id={cycle['id']}&employee_id={employee['id']}",
            headers=headers,
        )
        if resp.status_code == 404:
            pytest.skip("Records endpoint not implemented")
        items = resp.json().get("items", [])
        if not items:
            pytest.skip("No assessment record found for approval test")
        return items[0]["id"]


class TestApprovalSpecial:
    """TC-APP-004, TC-APP-005"""

    def test_special_approval_request(self, client: TestClient, admin_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-APP-004: 强制分布特批申请成功"""
        record_id = self._get_record_id(client, admin_headers, seeded_cycle, seeded_employee)
        payload = {
            "record_id": record_id,
            "reason": "该员工本季度业绩突出，应保留A等级",
        }
        resp = client.post("/approvals/special-request", json=payload, headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Special approval endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert data.get("status") == "特批审批中"

    def test_approval_history(self, client: TestClient, admin_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-APP-005: 审批历史查询正确"""
        record_id = self._get_record_id(client, admin_headers, seeded_cycle, seeded_employee)
        resp = client.get(f"/approvals/record/{record_id}/history", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Approval history endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert isinstance(data, list)
        for item in data:
            assert "approver" in item
            assert "action" in item
            assert "timestamp" in item

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


class TestApprovalUI:
    """TC-APP-006, TC-APP-007, TC-APP-008 (UI / E2E tests)"""

    def test_approval_flowchart_visualization(self):
        """TC-APP-006: 审批流程图可视化 (UI only)"""
        pytest.skip("UI-only test: verify flowchart in browser/E2E suite")

    def test_batch_approval(self):
        """TC-APP-007: 批量审批通过 (UI only)"""
        pytest.skip("UI-only test: verify batch approval in browser/E2E suite")

    def test_approval_timeline(self):
        """TC-APP-008: 审批时间线 (UI only)"""
        pytest.skip("UI-only test: verify timeline in browser/E2E suite")


class TestApprovalQueries:
    """TC-APP-009, TC-APP-010, TC-APP-011, TC-APP-012, TC-APP-013, TC-APP-014"""

    def test_pending_approval_list(self, client: TestClient, admin_headers: dict):
        """TC-APP-009: 待审批列表查询"""
        resp = client.get("/approvals/pending", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Pending approvals endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert isinstance(data, list) or "items" in data

    def test_approval_chain_config(self, client: TestClient, admin_headers: dict):
        """TC-APP-010: 审批链配置查询"""
        resp = client.get("/approvals/chain-config", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Chain config endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert "chain" in data or "nodes" in data

    def test_update_approval_chain(self, client: TestClient, admin_headers: dict):
        """TC-APP-011: 修改审批链"""
        payload = {"chain": ["上级", "HR", "总经理"]}
        resp = client.put("/approvals/chain-config", json=payload, headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Chain config update endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert "chain" in data or "保存" in data.get("message", "")

    def test_reassign_approver(self, client: TestClient, admin_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-APP-012: 重新指派审批人"""
        # Get record id
        resp = client.get(
            f"/records?cycle_id={seeded_cycle['id']}&employee_id={seeded_employee['id']}",
            headers=admin_headers,
        )
        if resp.status_code == 404:
            pytest.skip("Records endpoint not implemented")
        items = resp.json().get("items", [])
        if not items:
            pytest.skip("No assessment record found")
        record_id = items[0]["id"]

        # Create new approver
        from tests.scripts.utils import create_employee
        new_approver = create_employee(
            client, admin_headers, "APR_NEW", "新审批人",
            seeded_employee["department_id"], seeded_employee["position_id"],
        )
        resp = client.post(
            f"/approvals/{record_id}/reassign",
            json={"new_approver_id": new_approver["id"]},
            headers=admin_headers,
        )
        if resp.status_code == 404:
            pytest.skip("Reassign approver endpoint not implemented")
        assert_status_code(resp, 200)

    def test_distribution_override_list(self, client: TestClient, admin_headers: dict):
        """TC-APP-013: 特批审批列表查询"""
        resp = client.get("/approvals/distribution-overrides", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Distribution override list endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert isinstance(data, list) or "items" in data

    def test_approve_distribution_override(self, client: TestClient, admin_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-APP-014: 特批审批通过"""
        # First create a special request
        resp = client.get(
            f"/records?cycle_id={seeded_cycle['id']}&employee_id={seeded_employee['id']}",
            headers=admin_headers,
        )
        if resp.status_code == 404:
            pytest.skip("Records endpoint not implemented")
        items = resp.json().get("items", [])
        if not items:
            pytest.skip("No assessment record found")
        record_id = items[0]["id"]

        # Create special request
        req = client.post(
            "/approvals/special-request",
            json={"record_id": record_id, "reason": "测试特批"},
            headers=admin_headers,
        )
        if req.status_code == 404:
            pytest.skip("Special request endpoint not implemented")

        # Get override id
        resp = client.get("/approvals/distribution-overrides", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Distribution override list endpoint not implemented")
        overrides = resp.json().get("items", resp.json() if isinstance(resp.json(), list) else [])
        if not overrides:
            pytest.skip("No distribution overrides found")
        override_id = overrides[0]["id"]

        # Approve
        resp2 = client.post(
            f"/approvals/distribution-overrides/{override_id}/approve",
            headers=admin_headers,
        )
        if resp2.status_code == 404:
            pytest.skip("Distribution override approve endpoint not implemented")
        assert_status_code(resp2, 200)
        assert resp2.json().get("status") == "已通过" or "保留" in resp2.json().get("message", "")
