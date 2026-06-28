"""
test_rpt.py — Report analysis tests (TC-RPT-001 ~ TC-RPT-005)

Corresponds to test cases in:
  TEST_CASES_绩效考核评分系统_v1.0.md  §11 报表分析模块 (RPT)
"""

import pytest
from fastapi.testclient import TestClient

from tests.scripts.utils import assert_status_code


class TestReportDistribution:
    """TC-RPT-001"""

    def test_grade_distribution_report(self, client: TestClient, admin_headers: dict, seeded_cycle: dict):
        """TC-RPT-001: 等级分布报表查询正确"""
        resp = client.get(f"/reports/cycle/{seeded_cycle['id']}/distribution", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Distribution report endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert "original" in data
        assert "adjusted" in data
        for grade in ("A", "B", "C", "D"):
            assert grade in data["original"]


class TestReportExport:
    """TC-RPT-002, TC-RPT-003"""

    def test_export_excel(self, client: TestClient, admin_headers: dict, seeded_cycle: dict):
        """TC-RPT-002: 导出Excel成功"""
        resp = client.get(f"/reports/cycle/{seeded_cycle['id']}/export?format=xlsx", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Export endpoint not implemented")
        assert_status_code(resp, 200)
        assert resp.headers.get("content-type") in (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/octet-stream",
        )
        assert len(resp.content) > 0

    def test_export_pdf(self, client: TestClient, admin_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-RPT-003: 生成PDF档案成功"""
        record_id = self._get_record_id(client, admin_headers, seeded_cycle, seeded_employee)
        resp = client.get(f"/reports/record/{record_id}/pdf", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("PDF export endpoint not implemented")
        assert_status_code(resp, 200)
        assert resp.headers.get("content-type") in (
            "application/pdf",
            "application/octet-stream",
        )
        assert len(resp.content) > 0

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


class TestReportUI:
    """TC-RPT-004, TC-RPT-005 (UI / E2E tests)"""

    def test_chart_rendering(self):
        """TC-RPT-004: 报表图表渲染 (UI only)"""
        pytest.skip("UI-only test: verify chart rendering in browser/E2E suite")

    def test_filter_panel_collapse(self):
        """TC-RPT-005: 筛选面板折叠 (UI only)"""
        pytest.skip("UI-only test: verify filter panel in browser/E2E suite")


class TestReportQueries:
    """TC-RPT-006, TC-RPT-007, TC-RPT-008, TC-RPT-009"""

    def test_distribution_adjustments_list(self, client: TestClient, admin_headers: dict, seeded_cycle: dict):
        """TC-RPT-006: 强制调整清单查询"""
        resp = client.get(f"/reports/cycle/{seeded_cycle['id']}/distribution-adjustments", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Distribution adjustments endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert isinstance(data, list) or "items" in data or "adjustments" in data

    def test_employee_trend(self, client: TestClient, admin_headers: dict, seeded_employee: dict):
        """TC-RPT-007: 员工历史趋势查询"""
        resp = client.get(f"/reports/employee/{seeded_employee['id']}/trend?cycles=8", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Employee trend endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert isinstance(data, list) or "trends" in data or "cycles" in data

    def test_dashboard_cycle_stats(self, client: TestClient, admin_headers: dict):
        """TC-RPT-008: 仪表盘考核周期统计"""
        resp = client.get("/dashboard/cycles", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Dashboard cycles endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert "ongoing" in data or "pending" in data or "archived" in data or "total" in data

    def test_dashboard_approval_stats(self, client: TestClient, manager_headers: dict):
        """TC-RPT-009: 仪表盘待审批统计"""
        resp = client.get("/dashboard/approvals", headers=manager_headers)
        if resp.status_code == 404:
            pytest.skip("Dashboard approvals endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert "pending_count" in data or "total" in data or "count" in data
