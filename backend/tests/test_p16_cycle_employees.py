import pytest
from fastapi.testclient import TestClient
from app.models import AssessmentCycle, Employee, Department, Position, CycleEmployee
from datetime import date, timedelta


class TestCycleEmployeesList:
    """Tests for P1-16: GET /assessment-cycles/{cycle_id}/employees"""

    def test_list_cycle_employees_success(self, client: TestClient, admin_token, db_session):
        """Admin should be able to list employees in a cycle"""
        cycle = AssessmentCycle(
            name="参与人员测试周期", type="monthly",
            start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status="pending_self"
        )
        db_session.add(cycle)
        db_session.flush()

        dept = Department(name="测试部", code="TEST")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()

        emp1 = Employee(employee_no="CE001", name="员工甲", department_id=dept.id, position_id=pos.id)
        emp2 = Employee(employee_no="CE002", name="员工乙", department_id=dept.id, position_id=pos.id)
        db_session.add(emp1)
        db_session.add(emp2)
        db_session.flush()

        ce1 = CycleEmployee(cycle_id=cycle.id, employee_id=emp1.id, status="pending")
        ce2 = CycleEmployee(cycle_id=cycle.id, employee_id=emp2.id, status="completed")
        db_session.add(ce1)
        db_session.add(ce2)
        db_session.commit()

        resp = client.get(f"/assessment-cycles/{cycle.id}/employees", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

        # Verify fields for first employee
        emp_data = next(e for e in data if e["employee_id"] == emp1.id)
        assert emp_data["employee_no"] == "CE001"
        assert emp_data["name"] == "员工甲"
        assert emp_data["department_name"] == "测试部"
        assert emp_data["position_name"] == "测试岗"
        assert emp_data["status"] == "pending"
        assert emp_data["cycle_id"] == cycle.id
        assert "added_at" in emp_data

        # Verify second employee
        emp2_data = next(e for e in data if e["employee_id"] == emp2.id)
        assert emp2_data["status"] == "completed"

    def test_list_cycle_employees_hr_can_access(self, client: TestClient, hr_token, db_session):
        """HR should be able to list employees in a cycle"""
        cycle = AssessmentCycle(
            name="HR查询周期", type="quarterly",
            start_date=date.today(), end_date=date.today() + timedelta(days=90),
            status="pending_self"
        )
        db_session.add(cycle)
        db_session.flush()

        dept = Department(name="HR部", code="HRDEPT")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="HR岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()

        emp = Employee(employee_no="HRCE001", name="HR员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()

        ce = CycleEmployee(cycle_id=cycle.id, employee_id=emp.id, status="pending")
        db_session.add(ce)
        db_session.commit()

        resp = client.get(f"/assessment-cycles/{cycle.id}/employees", headers={"Authorization": f"Bearer {hr_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "HR员工"

    def test_list_cycle_employees_not_found(self, client: TestClient, admin_token):
        """Should return 404 when cycle does not exist"""
        resp = client.get("/assessment-cycles/99999/employees", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404
        assert resp.json()["message"] == "考核周期不存在"

    def test_list_cycle_employees_employee_forbidden(self, client: TestClient, employee_token, db_session):
        """Employee should not be able to list cycle employees"""
        cycle = AssessmentCycle(
            name="员工无权查询", type="monthly",
            start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status="pending_self"
        )
        db_session.add(cycle)
        db_session.commit()

        resp = client.get(f"/assessment-cycles/{cycle.id}/employees", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403

    def test_list_cycle_employees_empty(self, client: TestClient, admin_token, db_session):
        """Should return empty list when cycle has no employees"""
        cycle = AssessmentCycle(
            name="空周期", type="monthly",
            start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status="not_started"
        )
        db_session.add(cycle)
        db_session.commit()

        resp = client.get(f"/assessment-cycles/{cycle.id}/employees", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data == []
