import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Employee, Department, Position, AssessmentRecord, AssessmentCycle, ApprovalRecord
from datetime import date


class TestApprovalChain:
    """Tests for configurable multi-level approval chain"""

    def test_chain_config_read(self, client: TestClient, admin_user, admin_token):
        """Get default approval chain config"""
        resp = client.get("/approvals/chain-config", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["chain"] == ["direct_manager", "dept_head", "hr_head"]

    def test_chain_config_update(self, client: TestClient, admin_token):
        """Update approval chain config"""
        resp = client.put(
            "/approvals/chain-config",
            json={"chain": ["direct_manager", "hr_head"]},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["chain"] == ["direct_manager", "hr_head"]

    def test_multi_level_approval_flow(self, client: TestClient, manager_user, hr_user, employee_user, db_session: Session):
        """Test full 3-level approval: direct_manager -> dept_head -> hr_head"""
        # Use existing department from fixture or create unique one
        dept = db_session.query(Department).filter(Department.code == "TECH").first()
        if not dept:
            dept = Department(name="技术部", code="TECH")
            db_session.add(dept)
            db_session.flush()

        # Make manager the department head
        mgr_emp = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        mgr_emp.department_id = dept.id
        mgr_emp.is_department_head = True

        # Make hr employee also in this department
        hr_emp = db_session.query(Employee).filter(Employee.id == hr_user.employee_id).first()
        hr_emp.department_id = dept.id

        # Set up employee under manager
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        emp.department_id = dept.id
        emp.manager_id = mgr_emp.id
        db_session.commit()

        # Also update department head_id
        dept.head_id = mgr_emp.id
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
            department_id=dept.id, status="pending_approval",
            total_score=85, grade="B",
        )
        db_session.add(record)
        db_session.commit()

        # Step 1: direct_manager (manager) approves
        resp = client.post("/auth/login", json={"username": "mgr001", "password": "Mgr001@123"})
        mgr_token = resp.json()["access_token"]

        resp = client.post(
            f"/approvals/{record.id}/approve",
            params={"comment": "直属上级通过"},
            headers={"Authorization": f"Bearer {mgr_token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending_approval"

        # Step 2: dept_head (same manager, since he is dept head) approves
        resp = client.post(
            f"/approvals/{record.id}/approve",
            params={"comment": "部门负责人通过"},
            headers={"Authorization": f"Bearer {mgr_token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending_approval"

        # Step 3: hr_head approves
        resp = client.post("/auth/login", json={"username": "hr001", "password": "Hr001@123"})
        hr_token = resp.json()["access_token"]

        resp = client.post(
            f"/approvals/{record.id}/approve",
            params={"comment": "HR通过"},
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending_interview"

    def test_pending_approvals_by_role(self, client: TestClient, manager_user, hr_user, employee_user, db_session: Session):
        """Manager sees records at their step; HR sees all pending records"""
        dept = db_session.query(Department).filter(Department.code == "TECH").first()
        if not dept:
            dept = Department(name="技术部", code="TECH")
            db_session.add(dept)
            db_session.flush()

        mgr_emp = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        mgr_emp.department_id = dept.id
        mgr_emp.is_department_head = True
        dept.head_id = mgr_emp.id

        hr_emp = db_session.query(Employee).filter(Employee.id == hr_user.employee_id).first()
        hr_emp.department_id = dept.id

        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        emp.department_id = dept.id
        emp.manager_id = mgr_emp.id
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
            department_id=dept.id, status="pending_approval",
        )
        db_session.add(record)
        db_session.commit()

        # Manager should see it (direct_manager step)
        resp = client.post("/auth/login", json={"username": "mgr001", "password": "Mgr001@123"})
        mgr_token = resp.json()["access_token"]

        resp = client.get("/approvals/pending", headers={"Authorization": f"Bearer {mgr_token}"})
        assert resp.status_code == 200
        items = resp.json()
        assert any(i["record_id"] == record.id for i in items)

        # HR should also see it (HR sees all pending_approval records)
        resp = client.post("/auth/login", json={"username": "hr001", "password": "Hr001@123"})
        hr_token = resp.json()["access_token"]

        resp = client.get("/approvals/pending", headers={"Authorization": f"Bearer {hr_token}"})
        assert resp.status_code == 200
        items = resp.json()
        assert any(i["record_id"] == record.id for i in items)
