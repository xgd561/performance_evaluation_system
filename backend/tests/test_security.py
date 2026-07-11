import pytest
from datetime import datetime, date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import (
    Employee, Department, Position, AssessmentRecord, AssessmentCycle, InterviewRecord, ScoreDetail
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _create_cycle_and_record(db_session: Session, employee: Employee):
    cycle = AssessmentCycle(
        name="测试周期",
        type="annual",
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow(),
        status="published",
    )
    db_session.add(cycle)
    db_session.commit()
    db_session.refresh(cycle)

    record = AssessmentRecord(
        cycle_id=cycle.id,
        employee_id=employee.id,
        department_id=employee.department_id,
        position_id=employee.position_id,
        status="published",
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


def _create_interview(db_session: Session, record_id: int, interviewer_id: int):
    interview = InterviewRecord(
        record_id=record_id,
        interviewer_id=interviewer_id,
        interview_time=datetime.utcnow(),
        content="test content",
        improvement_plan="test plan",
    )
    db_session.add(interview)
    db_session.commit()
    db_session.refresh(interview)
    return interview


# ---------------------------------------------------------------------------
# ① 员工 A 访问员工 B 的评分/绩效/审批详情 → 返回 403
# ---------------------------------------------------------------------------
class TestCrossEmployeeAccessForbidden:
    """P7-04-1: Cross-employee data access must be rejected with 403."""

    # --- employee accessing manager's data ---

    def test_employee_cannot_view_manager_employee_detail(self, client: TestClient, employee_token, manager_user):
        resp = client.get(
            f"/employees/{manager_user.employee_id}",
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_employee_cannot_view_manager_trend_report(self, client: TestClient, employee_token, manager_user):
        resp = client.get(
            f"/reports/employee/{manager_user.employee_id}/trend",
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_employee_cannot_view_manager_interview_history(self, client: TestClient, employee_token, manager_user, db_session):
        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        _create_cycle_and_record(db_session, mgr)
        resp = client.get(
            f"/interviews/employee/{mgr.id}",
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_employee_cannot_view_manager_interview_detail(self, client: TestClient, employee_token, manager_user, db_session):
        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        record = _create_cycle_and_record(db_session, mgr)
        _create_interview(db_session, record.id, mgr.id)
        resp = client.get(
            f"/interviews/{record.id}",
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_employee_cannot_view_manager_assessment_record_detail(self, client: TestClient, employee_token, manager_user, db_session):
        dept = db_session.query(Department).filter(Department.code == "TECH").first()
        if not dept:
            dept = Department(name="技术部", code="TECH")
            db_session.add(dept)
            db_session.flush()

        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        cycle = AssessmentCycle(name="测试周期", type="季度", start_date=date(2026,1,1), end_date=date(2026,3,31), status="published")
        db_session.add(cycle)
        db_session.flush()
        record = AssessmentRecord(
            cycle_id=cycle.id, employee_id=mgr.id, department_id=dept.id, status="published"
        )
        db_session.add(record)
        db_session.commit()
        resp = client.get(
            f"/scores/records/{record.id}/detail",
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    # --- peer accessing employee's data ---

    def test_peer_cannot_view_employee_employee_detail(self, client: TestClient, peer_token, employee_user):
        resp = client.get(
            f"/employees/{employee_user.employee_id}",
            headers={"Authorization": f"Bearer {peer_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_peer_cannot_view_employee_trend_report(self, client: TestClient, peer_token, employee_user):
        resp = client.get(
            f"/reports/employee/{employee_user.employee_id}/trend",
            headers={"Authorization": f"Bearer {peer_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_peer_cannot_view_employee_interview_history(self, client: TestClient, peer_token, employee_user, db_session):
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        _create_cycle_and_record(db_session, emp)
        resp = client.get(
            f"/interviews/employee/{emp.id}",
            headers={"Authorization": f"Bearer {peer_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


# ---------------------------------------------------------------------------
# ② 经理访问非下属记录 → 返回 403
# ---------------------------------------------------------------------------
class TestManagerNonSubordinateAccessForbidden:
    """P7-04-2: Manager accessing non-subordinate records must be rejected with 403."""

    def test_manager_cannot_view_hr_employee_detail(self, client: TestClient, manager_token, hr_user):
        resp = client.get(
            f"/employees/{hr_user.employee_id}",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_manager_cannot_view_hr_trend_report(self, client: TestClient, manager_token, hr_user):
        resp = client.get(
            f"/reports/employee/{hr_user.employee_id}/trend",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_manager_cannot_view_hr_interview_history(self, client: TestClient, manager_token, hr_user, db_session):
        hr = db_session.query(Employee).filter(Employee.id == hr_user.employee_id).first()
        _create_cycle_and_record(db_session, hr)
        resp = client.get(
            f"/interviews/employee/{hr.id}",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_manager_cannot_view_hr_interview_detail(self, client: TestClient, manager_token, hr_user, db_session):
        hr = db_session.query(Employee).filter(Employee.id == hr_user.employee_id).first()
        record = _create_cycle_and_record(db_session, hr)
        _create_interview(db_session, record.id, hr.id)
        resp = client.get(
            f"/interviews/{record.id}",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_manager_cannot_view_non_subordinate_assessment_detail(self, client: TestClient, manager_token, hr_user, db_session):
        dept = db_session.query(Department).filter(Department.code == "HR").first()
        if not dept:
            dept = Department(name="人事部", code="HR")
            db_session.add(dept)
            db_session.flush()

        hr = db_session.query(Employee).filter(Employee.id == hr_user.employee_id).first()
        cycle = AssessmentCycle(name="测试周期", type="季度", start_date=date(2026,1,1), end_date=date(2026,3,31), status="published")
        db_session.add(cycle)
        db_session.flush()
        record = AssessmentRecord(
            cycle_id=cycle.id, employee_id=hr.id, department_id=dept.id, status="published"
        )
        db_session.add(record)
        db_session.commit()
        resp = client.get(
            f"/scores/records/{record.id}/detail",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


# ---------------------------------------------------------------------------
# ③ 非 executive 访问高管仪表盘 → 返回 403
# ---------------------------------------------------------------------------
class TestNonExecutiveDashboardForbidden:
    """P7-04-3: Non-executive roles accessing executive dashboard must be rejected with 403."""

    def test_admin_cannot_access_executive_dashboard(self, client: TestClient, admin_token):
        resp = client.get(
            "/dashboard/executive",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_hr_cannot_access_executive_dashboard(self, client: TestClient, hr_token):
        resp = client.get(
            "/dashboard/executive",
            headers={"Authorization": f"Bearer {hr_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_manager_cannot_access_executive_dashboard(self, client: TestClient, manager_token):
        resp = client.get(
            "/dashboard/executive",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_employee_cannot_access_executive_dashboard(self, client: TestClient, employee_token):
        resp = client.get(
            "/dashboard/executive",
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_peer_cannot_access_executive_dashboard(self, client: TestClient, peer_token):
        resp = client.get(
            "/dashboard/executive",
            headers={"Authorization": f"Bearer {peer_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


# ---------------------------------------------------------------------------
# ④ 未登录访问任意 API → 返回 401
# ---------------------------------------------------------------------------
class TestUnauthenticatedAccessForbidden:
    """P7-04-4: Unauthenticated access to protected APIs must be rejected with 401."""

    def test_unauthenticated_get_employee_detail(self, client: TestClient):
        resp = client.get("/employees/1")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    def test_unauthenticated_get_my_assessment(self, client: TestClient):
        resp = client.get("/scores/my-assessment")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    def test_unauthenticated_get_executive_dashboard(self, client: TestClient):
        resp = client.get("/dashboard/executive")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    def test_unauthenticated_get_interview(self, client: TestClient):
        resp = client.get("/interviews/1")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    def test_unauthenticated_get_approvals_pending(self, client: TestClient):
        resp = client.get("/approvals/pending")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    def test_unauthenticated_get_trend_report(self, client: TestClient):
        resp = client.get("/reports/employee/1/trend")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    def test_unauthenticated_post_score_draft(self, client: TestClient):
        resp = client.post("/scores/records/1/draft", json={})
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    def test_unauthenticated_get_appeals(self, client: TestClient):
        resp = client.get("/appeals")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    def test_unauthenticated_get_manager_score_list(self, client: TestClient):
        resp = client.get("/scores/manager/score-list")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    def test_unauthenticated_get_approval_detail(self, client: TestClient):
        resp = client.get("/approvals/1")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
