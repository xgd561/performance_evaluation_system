import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date

from app.models import Employee, Department, Position, AssessmentRecord, AssessmentCycle, User
from app.auth import get_password_hash


class TestDataIsolation:
    """Tests for data isolation across roles"""

    def test_manager_can_only_see_subordinates_in_summary(
        self, client: TestClient, manager_user, employee_user, db_session: Session
    ):
        """Manager should only see subordinates in score summary"""
        # Set up manager-employee relationship
        mgr_emp = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()

        # Create another employee not managed by manager_user
        dept = Department(name="其他部", code="OTHER")
        db_session.add(dept)
        db_session.flush()
        other_emp = Employee(employee_no="OTHER001", name="其他员工", department_id=dept.id)
        db_session.add(other_emp)
        db_session.flush()

        # Make manager_user the manager of employee_user
        emp.manager_id = mgr_emp.id
        emp.department_id = mgr_emp.department_id
        db_session.commit()

        # Create a cycle and records
        cycle = AssessmentCycle(
            name="测试周期",
            type="季度",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            status="pending_summary",
        )
        db_session.add(cycle)
        db_session.flush()

        record1 = AssessmentRecord(cycle_id=cycle.id, employee_id=emp.id, status="pending_summary")
        record2 = AssessmentRecord(cycle_id=cycle.id, employee_id=other_emp.id, status="pending_summary")
        db_session.add_all([record1, record2])
        db_session.commit()

        # Login as manager
        resp = client.post("/auth/login", json={"username": "mgr001", "password": "Mgr001@123"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        # Get summary
        resp = client.get(
            f"/scores/summary/{cycle.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        employee_ids = [r["employee_id"] for r in data]
        assert emp.id in employee_ids
        assert other_emp.id not in employee_ids

    def test_employee_can_only_see_self_in_employees_list(
        self, client: TestClient, employee_user, db_session: Session
    ):
        """Employee should only see themselves in employee list"""
        # Login as employee
        resp = client.post("/auth/login", json={"username": "emp001", "password": "Emp001@123"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        # Get employees list
        resp = client.get(
            "/employees",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", [])
        assert len(items) == 1
        assert items[0]["name"] == employee_user.employee.name

    def test_manager_can_only_see_department_in_employees_list(
        self, client: TestClient, manager_user, db_session: Session
    ):
        """Manager should only see department employees in employee list"""
        # Create another department employee
        other_dept = Department(name="其他部", code="OTHER")
        db_session.add(other_dept)
        db_session.flush()
        other_emp = Employee(employee_no="OTHER001", name="其他员工", department_id=other_dept.id)
        db_session.add(other_emp)
        db_session.commit()

        # Login as manager
        resp = client.post("/auth/login", json={"username": "mgr001", "password": "Mgr001@123"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        # Get employees list
        resp = client.get(
            "/employees",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", [])
        employee_ids = [e["id"] for e in items]
        # Manager's own employee should be visible
        assert manager_user.employee_id in employee_ids
        # Other department employee should NOT be visible
        assert other_emp.id not in employee_ids

    def test_manager_can_only_see_subordinates_in_distribution(
        self, client: TestClient, manager_user, employee_user, db_session: Session
    ):
        """Manager should only see subordinates in distribution report"""
        mgr_emp = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()

        # Create another employee not managed by manager
        other_dept = Department(name="其他部", code="OTHER")
        db_session.add(other_dept)
        db_session.flush()
        other_emp = Employee(employee_no="OTHER001", name="其他员工", department_id=other_dept.id)
        db_session.add(other_emp)
        db_session.flush()

        emp.manager_id = mgr_emp.id
        emp.department_id = mgr_emp.department_id
        db_session.commit()

        cycle = AssessmentCycle(
            name="测试周期",
            type="季度",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            status="pending_summary",
        )
        db_session.add(cycle)
        db_session.flush()

        record1 = AssessmentRecord(
            cycle_id=cycle.id, employee_id=emp.id,
            total_score=85, grade="B", status="pending_summary"
        )
        record2 = AssessmentRecord(
            cycle_id=cycle.id, employee_id=other_emp.id,
            total_score=90, grade="A", status="pending_summary"
        )
        db_session.add_all([record1, record2])
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "mgr001", "password": "Mgr001@123"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        resp = client.get(
            f"/reports/cycle/{cycle.id}/distribution",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        # Only subordinate record should be counted
        assert data["total_records"] == 1
        assert data["overall_distribution"].get("B", 0) == 1
