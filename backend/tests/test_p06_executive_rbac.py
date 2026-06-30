import pytest
from fastapi.testclient import TestClient


class TestExecutiveWriteForbidden:
    """P0-6: executive should be forbidden from all write endpoints."""

    def test_exec_cannot_create_department(self, client: TestClient, executive_token):
        resp = client.post(
            "/departments",
            json={"name": "TestDept", "code": "TEST"},
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_exec_cannot_update_department(self, client: TestClient, executive_token):
        resp = client.put(
            "/departments/1",
            json={"name": "Updated"},
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_exec_cannot_delete_department(self, client: TestClient, executive_token):
        resp = client.delete(
            "/departments/1",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_exec_cannot_create_position(self, client: TestClient, executive_token):
        resp = client.post(
            "/positions",
            json={"name": "TestPos", "department_id": 1},
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_exec_cannot_launch_cycle(self, client: TestClient, executive_token):
        resp = client.post(
            "/assessment-cycles/launch",
            json={"cycle_id": 1, "employee_ids": [1]},
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_exec_cannot_cancel_cycle(self, client: TestClient, executive_token):
        resp = client.post(
            "/assessment-cycles/1/cancel",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_exec_cannot_archive_cycle(self, client: TestClient, executive_token):
        resp = client.post(
            "/assessment-cycles/1/archive",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_exec_cannot_publish_cycle(self, client: TestClient, executive_token):
        resp = client.post(
            "/assessment-cycles/1/publish",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_exec_cannot_add_employees_to_cycle(self, client: TestClient, executive_token):
        resp = client.post(
            "/assessment-cycles/add-employees",
            json={"cycle_id": 1, "employee_ids": [1]},
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_exec_cannot_remove_employee_from_cycle(self, client: TestClient, executive_token):
        resp = client.delete(
            "/assessment-cycles/1/employees/1",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_exec_cannot_create_employee(self, client: TestClient, executive_token):
        resp = client.post(
            "/employees",
            json={"employee_no": "E999", "name": "Test"},
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_exec_cannot_update_employee(self, client: TestClient, executive_token):
        resp = client.put(
            "/employees/1",
            json={"name": "Updated"},
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_exec_cannot_delete_employee(self, client: TestClient, executive_token):
        resp = client.delete(
            "/employees/1",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_exec_cannot_import_employees(self, client: TestClient, executive_token):
        # We can send an empty file-like request; 403 should come before parsing.
        resp = client.post(
            "/employees/import",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_exec_cannot_assign_peer_reviewer(self, client: TestClient, executive_token):
        resp = client.post(
            "/peer-reviewers",
            json={"cycle_id": 1, "employee_id": 1, "peer_id": 2},
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_exec_cannot_remove_peer_reviewer(self, client: TestClient, executive_token):
        resp = client.delete(
            "/peer-reviewers/1",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_exec_cannot_approve_distribution_override(self, client: TestClient, executive_token):
        resp = client.post(
            "/approvals/distribution-overrides/1/approve",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_exec_cannot_reject_distribution_override(self, client: TestClient, executive_token):
        resp = client.post(
            "/approvals/distribution-overrides/1/reject",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_exec_cannot_review_appeal(self, client: TestClient, executive_token):
        resp = client.post(
            "/appeals/1/review",
            json={"action": "approve"},
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_exec_cannot_calculate_scores(self, client: TestClient, executive_token):
        resp = client.post(
            "/scores/calculate/1",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_exec_cannot_approve_kpi_adjustment(self, client: TestClient, executive_token):
        resp = client.post(
            "/kpi-templates/kpi-adjustments/1/approve",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_exec_cannot_reject_kpi_adjustment(self, client: TestClient, executive_token):
        resp = client.post(
            "/kpi-templates/kpi-adjustments/1/reject",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


class TestExecutiveReadAllowed:
    """P0-6: executive should still be allowed on read/report endpoints."""

    def test_exec_can_read_appeals(self, client: TestClient, executive_token):
        resp = client.get(
            "/appeals",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_exec_can_read_approvals_distribution_overrides(self, client: TestClient, executive_token):
        resp = client.get(
            "/approvals/distribution-overrides",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_exec_can_read_dashboard_cycles(self, client: TestClient, executive_token):
        resp = client.get(
            "/dashboard/cycles",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_exec_can_read_cycle_progress(self, client: TestClient, executive_token):
        # May return 404 if cycle not found, but role check should pass first.
        resp = client.get(
            "/assessment-cycles/1/progress",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        # 404 is acceptable because the cycle doesn't exist; 403 means role is blocked.
        assert resp.status_code in (200, 404), f"Expected 200 or 404, got {resp.status_code}"
        if resp.status_code == 404:
            assert "无权" not in resp.json().get("detail", "") and "Forbidden" not in resp.json().get("detail", "")

    def test_exec_can_read_employees_template(self, client: TestClient, executive_token):
        resp = client.get(
            "/employees/template",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_exec_can_read_peers_cycle(self, client: TestClient, executive_token):
        resp = client.get(
            "/peer-reviewers/cycle/1",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code in (200, 404), f"Expected 200 or 404, got {resp.status_code}"
        if resp.status_code == 404:
            assert "无权" not in resp.json().get("detail", "") and "Forbidden" not in resp.json().get("detail", "")

    def test_exec_can_read_reports_export(self, client: TestClient, executive_token):
        resp = client.get(
            "/reports/cycle/1/export",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code in (200, 404), f"Expected 200 or 404, got {resp.status_code}"
        if resp.status_code == 404:
            assert "无权" not in resp.json().get("detail", "") and "Forbidden" not in resp.json().get("detail", "")

    def test_exec_can_read_kpi_adjustments_pending(self, client: TestClient, executive_token):
        resp = client.get(
            "/kpi-templates/kpi-adjustments/pending",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_exec_can_read_approvals_chain_config(self, client: TestClient, executive_token):
        resp = client.get(
            "/approvals/chain-config",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
