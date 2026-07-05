import pytest
from fastapi.testclient import TestClient
from app.models import AssessmentCycle, Employee, Department, Position, ApprovalRecord, AppealRecord, AssessmentRecord
from datetime import date, timedelta


class TestDashboardMain:
    """Tests for GET /dashboard"""

    def test_dashboard_success(self, client: TestClient, admin_token, db_session):
        cycle = AssessmentCycle(
            name="仪表盘周期", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30)
        )
        db_session.add(cycle)
        db_session.commit()

        resp = client.get("/dashboard", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "stats" in data
        assert "recent_cycles" in data
        assert "pending_tasks" in data
        assert isinstance(data["stats"], dict)
        assert "total_cycles" in data["stats"]
        assert "total_employees" in data["stats"]
        assert "pending_approvals" in data["stats"]
        assert "pending_appeals" in data["stats"]
        assert data["stats"]["total_cycles"] >= 1
        assert isinstance(data["recent_cycles"], list)
        if data["recent_cycles"]:
            assert "name" in data["recent_cycles"][0]
            assert "status" in data["recent_cycles"][0]
        assert isinstance(data["pending_tasks"], list)

    def test_dashboard_first_login_redirect(self, client: TestClient, employee_token, db_session):
        # The employee_token fixture creates a user with is_first_login=True
        resp = client.get("/dashboard", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403
        assert "请先修改初始密码" in resp.json()["message"]

    def test_dashboard_no_auth(self, client: TestClient):
        resp = client.get("/dashboard")
        assert resp.status_code == 401


    def test_dashboard_hr_returns_expected_fields(self, client: TestClient, hr_token, db_session):
        """HR 仪表盘应返回 cycle_count、to_summary、to_approve、to_archive、pending_appeals、force_distribution_exceeded"""
        from app.models import AssessmentRecord, AppealRecord
        cycle = AssessmentCycle(
            name="HR仪表盘周期", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30)
        )
        db_session.add(cycle)
        db_session.commit()

        resp = client.get("/dashboard", headers={"Authorization": f"Bearer {hr_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "stats" in data
        stats = data["stats"]
        assert "cycle_count" in stats
        assert "to_summary" in stats
        assert "to_approve" in stats
        assert "to_archive" in stats
        assert "pending_appeals" in stats
        assert "force_distribution_exceeded" in stats


class TestDashboardCycles:
    """Tests for GET /dashboard/cycles"""

    def test_dashboard_cycles_success(self, client: TestClient, admin_token, db_session):
        cycle = AssessmentCycle(
            name="周期统计", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30)
        )
        db_session.add(cycle)
        db_session.commit()

        resp = client.get("/dashboard/cycles", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "by_status" in data

    def test_dashboard_cycles_unauthorized(self, client: TestClient, employee_token):
        resp = client.get("/dashboard/cycles", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403


class TestDashboardApprovals:
    """Tests for GET /dashboard/approvals"""

    def test_dashboard_approvals_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="审批部", code="APP")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="审批岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="APP001", name="审批人", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
        cycle = AssessmentCycle(
            name="审批周期", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30)
        )
        db_session.add(cycle)
        db_session.flush()
        record = AssessmentRecord(cycle_id=cycle.id, employee_id=emp.id, status="pending_approval")
        db_session.add(record)
        db_session.flush()
        app = ApprovalRecord(record_id=record.id, approver_id=emp.id, step_index=1)
        db_session.add(app)
        db_session.commit()

        resp = client.get("/dashboard/approvals", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "pending" in data

    def test_dashboard_approvals_manager_role(self, client: TestClient, manager_token):
        resp = client.get("/dashboard/approvals", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "pending" in data
        assert isinstance(data["pending"], int)


class TestDashboardScores:
    """Tests for GET /dashboard/scores"""

    def test_dashboard_scores_success(self, client: TestClient, admin_token, db_session):
        resp = client.get("/dashboard/scores", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "completed" in data
        assert "in_progress" in data
        assert isinstance(data["total"], int)
        assert isinstance(data["completed"], int)
        assert isinstance(data["in_progress"], int)
        assert data["completed"] + data["in_progress"] == data["total"]

    def test_dashboard_scores_unauthorized(self, client: TestClient, employee_token):
        resp = client.get("/dashboard/scores", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403
