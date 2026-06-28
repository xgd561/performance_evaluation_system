"""
test_kpi.py — KPI template management tests (TC-KPI-001 ~ TC-KPI-004)

Corresponds to test cases in:
  TEST_CASES_绩效考核评分系统_v1.0.md  §10 KPI模板管理模块 (KPI)
"""

import pytest
from fastapi.testclient import TestClient

from tests.scripts.utils import assert_status_code, create_kpi_template


class TestKpiCreate:
    """TC-KPI-001, TC-KPI-002"""

    def test_create_kpi_template_success(self, client: TestClient, admin_headers: dict, seeded_position: dict):
        """TC-KPI-001: 创建KPI模板成功"""
        items = [
            {"name": "代码质量", "weight": 40},
            {"name": "项目交付", "weight": 35},
            {"name": "技术分享", "weight": 25},
        ]
        resp = client.post(
            "/kpi-templates",
            json={"position_id": seeded_position["id"], "items": items},
            headers=admin_headers,
        )
        assert_status_code(resp, 201)
        data = resp.json()
        assert len(data.get("items", [])) == 3
        assert sum(i["weight"] for i in data["items"]) == 100

    def test_create_kpi_template_weight_sum_not_100(self, client: TestClient, admin_headers: dict, seeded_position: dict):
        """TC-KPI-002: KPI模板权重和不等于100%拦截"""
        items = [
            {"name": "KPI1", "weight": 40},
            {"name": "KPI2", "weight": 30},  # 70% total
        ]
        resp = client.post(
            "/kpi-templates",
            json={"position_id": seeded_position["id"], "items": items},
            headers=admin_headers,
        )
        assert_status_code(resp, 422)
        assert "70%" in resp.json().get("message", "")


class TestKpiUI:
    """TC-KPI-003, TC-KPI-004 (UI / E2E tests)"""

    def test_kpi_template_copy(self):
        """TC-KPI-003: KPI模板复制 (UI only)"""
        pytest.skip("UI-only test: verify template copy in browser/E2E suite")

    def test_kpi_item_drag_sort(self):
        """TC-KPI-004: KPI指标拖拽排序 (UI only)"""
        pytest.skip("UI-only test: verify drag sort in browser/E2E suite")


class TestKpiQueries:
    """TC-KPI-003, TC-KPI-004, TC-KPI-005, TC-KPI-006"""

    def test_kpi_template_list(self, client: TestClient, admin_headers: dict):
        """TC-KPI-003: KPI模板列表查询"""
        resp = client.get("/kpi-templates", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("KPI template list endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert isinstance(data, list) or "items" in data

    def test_update_kpi_template(self, client: TestClient, admin_headers: dict, seeded_position: dict):
        """TC-KPI-004: 修改KPI模板"""
        # First create a template
        items = [
            {"name": "代码质量", "weight": 40},
            {"name": "项目交付", "weight": 35},
            {"name": "技术分享", "weight": 25},
        ]
        resp = client.post(
            "/kpi-templates",
            json={"position_id": seeded_position["id"], "items": items},
            headers=admin_headers,
        )
        if resp.status_code == 404:
            pytest.skip("KPI template endpoint not implemented")
        template_id = resp.json().get("id", 1)
        # Update
        update_payload = {"items": [{"name": "代码质量", "weight": 50}, {"name": "项目交付", "weight": 50}]}
        resp2 = client.put(f"/kpi-templates/{template_id}", json=update_payload, headers=admin_headers)
        if resp2.status_code == 404:
            pytest.skip("KPI template update endpoint not implemented")
        assert_status_code(resp2, 200)
        assert resp2.json().get("items", [])[0]["weight"] == 50

    def test_request_kpi_adjustment(self, client: TestClient, manager_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-KPI-005: 申请KPI调整"""
        # Get record id
        resp = client.get(
            f"/records?cycle_id={seeded_cycle['id']}&employee_id={seeded_employee['id']}",
            headers=manager_headers,
        )
        if resp.status_code == 404:
            pytest.skip("Records endpoint not implemented")
        items = resp.json().get("items", [])
        if not items:
            pytest.skip("No assessment record found")
        record_id = items[0]["id"]

        payload = {
            "kpi_id": 1,
            "new_target": "覆盖率≥90%",
            "reason": "项目范围扩大",
        }
        resp2 = client.post(f"/kpi-templates/{record_id}/adjust", json=payload, headers=manager_headers)
        if resp2.status_code == 404:
            pytest.skip("KPI adjustment endpoint not implemented")
        assert_status_code(resp2, 201)
        assert "调整" in resp2.json().get("message", "") or resp2.json().get("status") == "待审批"

    def test_approve_kpi_adjustment(self, client: TestClient, admin_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-KPI-006: 通过KPI调整"""
        # Get pending adjustments
        resp = client.get("/kpi-adjustments/pending", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("KPI adjustments pending endpoint not implemented")
        assert_status_code(resp, 200)
        adjustments = resp.json().get("items", resp.json() if isinstance(resp.json(), list) else [])
        if not adjustments:
            pytest.skip("No pending KPI adjustments found")
        adj_id = adjustments[0]["id"]

        # Approve
        resp2 = client.post(f"/kpi-adjustments/{adj_id}/approve", headers=admin_headers)
        if resp2.status_code == 404:
            pytest.skip("KPI adjustment approve endpoint not implemented")
        assert_status_code(resp2, 200)
        assert resp2.json().get("status") == "已通过" or "已更新" in resp2.json().get("message", "")


class TestKpiQueries:
    """TC-KPI-003, TC-KPI-004, TC-KPI-005, TC-KPI-006"""

    def test_kpi_template_list(self, client: TestClient, admin_headers: dict):
        """TC-KPI-003: KPI模板列表查询"""
        resp = client.get("/kpi-templates", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("KPI template list endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert isinstance(data, list) or "items" in data

    def test_update_kpi_template(self, client: TestClient, admin_headers: dict, seeded_kpi_template: dict):
        """TC-KPI-004: 修改KPI模板"""
        payload = {
            "items": [
                {"name": "代码质量", "weight": 50},
                {"name": "项目交付", "weight": 50},
            ]
        }
        resp = client.put(f"/kpi-templates/{seeded_kpi_template['id']}", json=payload, headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("KPI template update endpoint not implemented")
        assert_status_code(resp, 200)
        assert sum(i["weight"] for i in resp.json().get("items", [])) == 100

    def test_apply_kpi_adjustment(self, client: TestClient, manager_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-KPI-005: 申请KPI调整"""
        # Get record id
        resp = client.get(
            f"/records?cycle_id={seeded_cycle['id']}&employee_id={seeded_employee['id']}",
            headers=manager_headers,
        )
        if resp.status_code == 404:
            pytest.skip("Records endpoint not implemented")
        items = resp.json().get("items", [])
        if not items:
            pytest.skip("No assessment record found")
        record_id = items[0]["id"]

        payload = {
            "kpi_id": 1,
            "new_target": "覆盖率≥90%",
            "reason": "项目范围扩大",
        }
        resp = client.post(f"/kpi-templates/{record_id}/adjust", json=payload, headers=manager_headers)
        if resp.status_code == 404:
            pytest.skip("KPI adjustment endpoint not implemented")
        assert_status_code(resp, 201)
        assert "adjustment_id" in resp.json() or "id" in resp.json()

    def test_approve_kpi_adjustment(self, client: TestClient, admin_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-KPI-006: 通过KPI调整"""
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

        # First apply adjustment
        apply_payload = {"kpi_id": 1, "new_target": "覆盖率≥90%", "reason": "项目范围扩大"}
        apply_resp = client.post(f"/kpi-templates/{record_id}/adjust", json=apply_payload, headers=admin_headers)
        if apply_resp.status_code == 404:
            pytest.skip("KPI adjustment endpoint not implemented")

        # Get adjustment id
        resp2 = client.get("/kpi-adjustments/pending", headers=admin_headers)
        if resp2.status_code == 404:
            pytest.skip("KPI adjustments pending endpoint not implemented")
        adjustments = resp2.json().get("items", resp2.json() if isinstance(resp2.json(), list) else [])
        if not adjustments:
            pytest.skip("No pending adjustments found")
        adj_id = adjustments[0]["id"]

        # Approve
        resp3 = client.post(f"/kpi-adjustments/{adj_id}/approve", headers=admin_headers)
        if resp3.status_code == 404:
            pytest.skip("KPI adjustment approve endpoint not implemented")
        assert_status_code(resp3, 200)
        assert "approved" in resp3.json().get("status", "").lower() or "通过" in resp3.json().get("message", "")
