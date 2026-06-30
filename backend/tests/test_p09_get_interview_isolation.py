import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from app.models import Employee, Department, Position, AssessmentRecord, InterviewRecord, AssessmentCycle


def _create_cycle_and_record(db_session, employee):
    """Helper to create an AssessmentCycle and AssessmentRecord for an employee."""
    cycle = AssessmentCycle(
        name="测试周期",
        type="annual",
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow(),
        status="active",
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


def _create_interview(db_session, record_id, interviewer_id):
    """Helper to create an InterviewRecord for a record."""
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


class TestGetInterviewIsolation:
    """P0-9: GET /interviews/{record_id} data isolation."""

    def test_employee_can_view_self(self, client: TestClient, employee_token, employee_user, db_session):
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        record = _create_cycle_and_record(db_session, emp)
        _create_interview(db_session, record.id, emp.id)
        resp = client.get(
            f"/interviews/{record.id}",
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_employee_cannot_view_other(self, client: TestClient, employee_token, manager_user, db_session):
        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        record = _create_cycle_and_record(db_session, mgr)
        _create_interview(db_session, record.id, mgr.id)
        resp = client.get(
            f"/interviews/{record.id}",
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_manager_can_view_self(self, client: TestClient, manager_token, manager_user, db_session):
        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        record = _create_cycle_and_record(db_session, mgr)
        _create_interview(db_session, record.id, mgr.id)
        resp = client.get(
            f"/interviews/{record.id}",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_manager_can_view_direct_subordinate(self, client: TestClient, manager_token, manager_user, employee_user, db_session):
        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        emp.manager_id = mgr.id
        db_session.commit()
        record = _create_cycle_and_record(db_session, emp)
        _create_interview(db_session, record.id, mgr.id)
        resp = client.get(
            f"/interviews/{record.id}",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_manager_can_view_indirect_subordinate(self, client: TestClient, manager_token, manager_user, employee_user, db_session):
        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        emp.manager_id = mgr.id
        db_session.commit()

        dept = db_session.query(Department).filter(Department.id == emp.department_id).first()
        pos = db_session.query(Position).filter(Position.department_id == dept.id).first()
        indirect = Employee(
            employee_no="EMP002",
            name="间接下属",
            department_id=dept.id,
            position_id=pos.id,
            manager_id=emp.id,
        )
        db_session.add(indirect)
        db_session.commit()
        db_session.refresh(indirect)

        record = _create_cycle_and_record(db_session, indirect)
        _create_interview(db_session, record.id, mgr.id)
        resp = client.get(
            f"/interviews/{record.id}",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_manager_cannot_view_same_department_non_subordinate(self, client: TestClient, manager_token, manager_user, employee_user, db_session):
        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        # same department but no chain relationship
        record = _create_cycle_and_record(db_session, emp)
        _create_interview(db_session, record.id, mgr.id)
        resp = client.get(
            f"/interviews/{record.id}",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_manager_cannot_view_other_department(self, client: TestClient, manager_token, manager_user, hr_user, db_session):
        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        hr = db_session.query(Employee).filter(Employee.id == hr_user.employee_id).first()
        record = _create_cycle_and_record(db_session, hr)
        _create_interview(db_session, record.id, hr.id)
        resp = client.get(
            f"/interviews/{record.id}",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_admin_can_view_any(self, client: TestClient, admin_token, employee_user, db_session):
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        record = _create_cycle_and_record(db_session, emp)
        _create_interview(db_session, record.id, emp.id)
        resp = client.get(
            f"/interviews/{record.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_hr_can_view_any(self, client: TestClient, hr_token, employee_user, db_session):
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        record = _create_cycle_and_record(db_session, emp)
        _create_interview(db_session, record.id, emp.id)
        resp = client.get(
            f"/interviews/{record.id}",
            headers={"Authorization": f"Bearer {hr_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_executive_can_view_any(self, client: TestClient, executive_token, employee_user, db_session):
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        record = _create_cycle_and_record(db_session, emp)
        _create_interview(db_session, record.id, emp.id)
        resp = client.get(
            f"/interviews/{record.id}",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
