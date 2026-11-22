import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import OperationLog, AssessmentRecord, AssessmentCycle, Employee, Department
from datetime import date


class TestOperationLogs:
    """Tests for operation logging across key actions"""

    def test_approval_creates_log(self, client: TestClient, manager_user, employee_user, db_session: Session):
        """Approving a record should create an operation log"""
        mgr_emp = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        emp.manager_id = mgr_emp.id
        emp.department_id = mgr_emp.department_id
        db_session.commit()

        cycle = AssessmentCycle(
            name="测试周期", type="季度",
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            status="pending_approval",
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id, employee_id=emp.id,
            status="pending_approval",
        )
        db_session.add(record)
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "mgr001", "password": "Mgr001@123"})
        token = resp.json()["access_token"]

        # Count logs before
        log_count_before = db_session.query(OperationLog).count()

        resp = client.post(
            f"/approvals/{record.id}/approve",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200

        # Verify log created
        log_count_after = db_session.query(OperationLog).count()
        assert log_count_after == log_count_before + 1

        log = db_session.query(OperationLog).order_by(OperationLog.id.desc()).first()
        assert log.action == "approve"
        assert log.target_type == "assessment_record"
        assert log.target_id == record.id
        assert log.user_id == manager_user.id

    def test_self_score_submit_creates_log(self, client: TestClient, employee_user, db_session: Session):
        """Self score submission should create an operation log"""
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        cycle = AssessmentCycle(
            name="测试周期", type="季度",
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            status="pending_self",
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id, employee_id=emp.id,
            status="pending_self",
        )
        db_session.add(record)
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "emp001", "password": "Emp001@123"})
        token = resp.json()["access_token"]

        log_count_before = db_session.query(OperationLog).count()

        resp = client.post(
            f"/scores/self/{record.id}",
            json={"performance": 80, "ability": 85, "attitude": 90},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200

        log_count_after = db_session.query(OperationLog).count()
        assert log_count_after == log_count_before + 1

        log = db_session.query(OperationLog).order_by(OperationLog.id.desc()).first()
        assert log.action == "self_score_submit"
        assert log.target_type == "assessment_record"

    def test_launch_cycle_creates_log(self, client: TestClient, admin_user, employee_user, db_session: Session):
        """Launching a cycle should create an operation log"""
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        cycle = AssessmentCycle(
            name="测试周期", type="季度",
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            status="not_started",
        )
        db_session.add(cycle)
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
        token = resp.json()["access_token"]

        log_count_before = db_session.query(OperationLog).count()

        resp = client.post(
            "/assessment-cycles/launch",
            json={"cycle_id": cycle.id, "employee_ids": [emp.id]},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200

        log_count_after = db_session.query(OperationLog).count()
        assert log_count_after == log_count_before + 1

        log = db_session.query(OperationLog).order_by(OperationLog.id.desc()).first()
        assert log.action == "launch_cycle"
        assert log.target_type == "assessment_cycle"
