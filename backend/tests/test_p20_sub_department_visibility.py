import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.models import AssessmentRecord, AssessmentCycle, Employee, Department, Position, User, InterviewRecord
from app.auth import get_password_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_cycle(db_session: Session, status: str = "pending_self"):
    cycle = AssessmentCycle(
        name="测试考核周期",
        type="monthly",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        self_due_date=date.today() + timedelta(days=10),
        manager_due_date=date.today() + timedelta(days=20),
        peer_due_date=date.today() + timedelta(days=25),
        status=status,
        dimension_weights='{"performance":0.6,"ability":0.2,"attitude":0.2}',
        reviewer_weights='{"performance":{"self":0.3,"manager":0.7},"ability":{"self":0.2,"manager":0.6,"peer":0.2},"attitude":{"self":0.2,"manager":0.8}}',
        grade_rules='{"A":{"min":90,"max":100,"ratio_limit":0.2},"B":{"min":80,"max":89.9,"ratio_limit":0.5},"C":{"min":60,"max":79.9,"ratio_limit":0.25},"D":{"min":0,"max":59.9,"ratio_limit":0.05}}',
    )
    db_session.add(cycle)
    db_session.commit()
    db_session.refresh(cycle)
    return cycle


def _create_record(db_session: Session, cycle_id: int, employee_id: int, department_id: int = None, status: str = "pending_self", **kwargs):
    record = AssessmentRecord(
        cycle_id=cycle_id,
        employee_id=employee_id,
        department_id=department_id,
        status=status,
        **kwargs,
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


# ---------------------------------------------------------------------------
# P1-20: 部门负责人可查看子部门记录
# ---------------------------------------------------------------------------

class TestSubDepartmentVisibility:
    """Tests for P1-20: managers should see records in sub-departments."""

    def test_list_employees_includes_sub_departments(self, client: TestClient, manager_token, manager_user, db_session: Session):
        """Manager should see employees in sub-departments via list_employees."""
        # Create parent department
        parent_dept = Department(name="技术部", code="TECH_P20_1")
        db_session.add(parent_dept)
        db_session.flush()

        # Create sub-department
        sub_dept = Department(name="前端组", code="FE_P20_1", parent_id=parent_dept.id)
        db_session.add(sub_dept)
        db_session.flush()

        # Assign manager to parent department
        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        mgr.department_id = parent_dept.id
        db_session.commit()

        # Create employee in sub-department
        sub_emp = Employee(
            employee_no="SUB001",
            name="子部门员工",
            department_id=sub_dept.id,
            is_active=True,
        )
        db_session.add(sub_emp)
        db_session.commit()

        resp = client.get("/employees", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        employee_ids = [e["id"] for e in data.get("items", [])]
        assert sub_emp.id in employee_ids, f"Expected sub-department employee {sub_emp.id} in {employee_ids}"

    def test_employee_detail_sub_department_allowed(self, client: TestClient, manager_token, manager_user, db_session: Session):
        """Manager should be able to view employee detail in sub-department."""
        parent_dept = Department(name="技术部", code="TECH_P20_2")
        db_session.add(parent_dept)
        db_session.flush()

        sub_dept = Department(name="前端组", code="FE_P20_2", parent_id=parent_dept.id)
        db_session.add(sub_dept)
        db_session.flush()

        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        mgr.department_id = parent_dept.id
        db_session.commit()

        sub_emp = Employee(
            employee_no="SUB002",
            name="子部门员工2",
            department_id=sub_dept.id,
            is_active=True,
        )
        db_session.add(sub_emp)
        db_session.commit()

        resp = client.get(f"/employees/{sub_emp.id}", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == sub_emp.id

    def test_score_summary_includes_sub_department_records(self, client: TestClient, manager_token, manager_user, db_session: Session):
        """Manager should see score summary records in sub-departments."""
        parent_dept = Department(name="技术部", code="TECH_P20_3")
        db_session.add(parent_dept)
        db_session.flush()

        sub_dept = Department(name="前端组", code="FE_P20_3", parent_id=parent_dept.id)
        db_session.add(sub_dept)
        db_session.flush()

        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        mgr.department_id = parent_dept.id
        db_session.commit()

        sub_emp = Employee(
            employee_no="SUB003",
            name="子部门员工3",
            department_id=sub_dept.id,
            is_active=True,
        )
        db_session.add(sub_emp)
        db_session.commit()

        cycle = _create_cycle(db_session, status="pending_manager")
        record = _create_record(
            db_session,
            cycle.id,
            sub_emp.id,
            department_id=sub_dept.id,
            status="pending_manager",
            total_score=85.0,
            grade="B",
        )

        resp = client.get(f"/scores/summary/{cycle.id}", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        record_ids = [r["record_id"] for r in data]
        assert record.id in record_ids, f"Expected record {record.id} in summary {record_ids}"

    def test_record_detail_sub_department_allowed(self, client: TestClient, manager_token, manager_user, db_session: Session):
        """Manager should be able to view record detail in sub-department."""
        parent_dept = Department(name="技术部", code="TECH_P20_4")
        db_session.add(parent_dept)
        db_session.flush()

        sub_dept = Department(name="前端组", code="FE_P20_4", parent_id=parent_dept.id)
        db_session.add(sub_dept)
        db_session.flush()

        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        mgr.department_id = parent_dept.id
        db_session.commit()

        sub_emp = Employee(
            employee_no="SUB004",
            name="子部门员工4",
            department_id=sub_dept.id,
            is_active=True,
        )
        db_session.add(sub_emp)
        db_session.commit()

        cycle = _create_cycle(db_session, status="published")
        record = _create_record(
            db_session,
            cycle.id,
            sub_emp.id,
            department_id=sub_dept.id,
            status="published",
            total_score=88.0,
            grade="B",
        )

        resp = client.get(f"/scores/records/{record.id}/detail", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["record_id"] == record.id

    def test_distribution_includes_sub_department(self, client: TestClient, manager_token, manager_user, db_session: Session):
        """Manager should see distribution records in sub-departments."""
        parent_dept = Department(name="技术部", code="TECH_P20_5")
        db_session.add(parent_dept)
        db_session.flush()

        sub_dept = Department(name="前端组", code="FE_P20_5", parent_id=parent_dept.id)
        db_session.add(sub_dept)
        db_session.flush()

        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        mgr.department_id = parent_dept.id
        db_session.commit()

        sub_emp = Employee(
            employee_no="SUB005",
            name="子部门员工5",
            department_id=sub_dept.id,
            is_active=True,
        )
        db_session.add(sub_emp)
        db_session.commit()

        cycle = _create_cycle(db_session, status="published")
        record = _create_record(
            db_session,
            cycle.id,
            sub_emp.id,
            department_id=sub_dept.id,
            status="published",
            total_score=88.0,
            grade="B",
        )

        resp = client.get(f"/reports/cycle/{cycle.id}/distribution", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_records"] >= 1
        # distribution returns aggregated dept stats, not individual records
        dept_ids = [d["department_id"] for d in data.get("department_stats", [])]
        assert sub_dept.id in dept_ids, f"Expected sub-dept {sub_dept.id} in distribution stats {dept_ids}"

    def test_trend_sub_department_allowed(self, client: TestClient, manager_token, manager_user, db_session: Session):
        """Manager should be able to view trend of employee in sub-department."""
        parent_dept = Department(name="技术部", code="TECH_P20_6")
        db_session.add(parent_dept)
        db_session.flush()

        sub_dept = Department(name="前端组", code="FE_P20_6", parent_id=parent_dept.id)
        db_session.add(sub_dept)
        db_session.flush()

        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        mgr.department_id = parent_dept.id
        db_session.commit()

        sub_emp = Employee(
            employee_no="SUB006",
            name="子部门员工6",
            department_id=sub_dept.id,
            is_active=True,
        )
        db_session.add(sub_emp)
        db_session.commit()

        cycle = _create_cycle(db_session, status="published")
        _create_record(
            db_session,
            cycle.id,
            sub_emp.id,
            department_id=sub_dept.id,
            status="published",
            total_score=88.0,
            grade="B",
        )

        resp = client.get(f"/reports/employee/{sub_emp.id}/trend", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_interview_sub_department_allowed(self, client: TestClient, manager_token, manager_user, db_session: Session):
        """Manager should be able to view interview of employee in sub-department."""
        parent_dept = Department(name="技术部", code="TECH_P20_7")
        db_session.add(parent_dept)
        db_session.flush()

        sub_dept = Department(name="前端组", code="FE_P20_7", parent_id=parent_dept.id)
        db_session.add(sub_dept)
        db_session.flush()

        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        mgr.department_id = parent_dept.id
        db_session.commit()

        sub_emp = Employee(
            employee_no="SUB007",
            name="子部门员工7",
            department_id=sub_dept.id,
            is_active=True,
        )
        db_session.add(sub_emp)
        db_session.commit()

        cycle = _create_cycle(db_session, status="published")
        record = _create_record(
            db_session,
            cycle.id,
            sub_emp.id,
            department_id=sub_dept.id,
            status="published",
        )

        interview = InterviewRecord(
            record_id=record.id,
            interviewer_id=mgr.id,
            content="面谈内容",
        )
        db_session.add(interview)
        db_session.commit()

        resp = client.get(f"/interviews/{record.id}", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["record_id"] == record.id

    def test_nested_sub_department_visibility(self, client: TestClient, manager_token, manager_user, db_session: Session):
        """Manager should see employees in nested sub-departments (grandchild)."""
        parent_dept = Department(name="技术部", code="TECH_P20_8")
        db_session.add(parent_dept)
        db_session.flush()

        child_dept = Department(name="后端组", code="BE_P20_8", parent_id=parent_dept.id)
        db_session.add(child_dept)
        db_session.flush()

        grandchild_dept = Department(name="Java组", code="JAVA_P20_8", parent_id=child_dept.id)
        db_session.add(grandchild_dept)
        db_session.flush()

        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        mgr.department_id = parent_dept.id
        db_session.commit()

        gc_emp = Employee(
            employee_no="GC001",
            name="孙部门员工",
            department_id=grandchild_dept.id,
            is_active=True,
        )
        db_session.add(gc_emp)
        db_session.commit()

        resp = client.get("/employees", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        employee_ids = [e["id"] for e in data.get("items", [])]
        assert gc_emp.id in employee_ids, f"Expected grandchild dept employee {gc_emp.id} in {employee_ids}"

    def test_other_department_excluded(self, client: TestClient, manager_token, manager_user, db_session: Session):
        """Manager should NOT see employees in unrelated departments."""
        parent_dept = Department(name="技术部", code="TECH_P20_9")
        db_session.add(parent_dept)
        db_session.flush()

        other_dept = Department(name="销售部", code="SALE_P20_9")
        db_session.add(other_dept)
        db_session.flush()

        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        mgr.department_id = parent_dept.id
        db_session.commit()

        other_emp = Employee(
            employee_no="OTH001",
            name="其他部门员工",
            department_id=other_dept.id,
            is_active=True,
        )
        db_session.add(other_emp)
        db_session.commit()

        resp = client.get("/employees", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        employee_ids = [e["id"] for e in data.get("items", [])]
        assert other_emp.id not in employee_ids, f"Expected other dept employee {other_emp.id} NOT in {employee_ids}"

    def test_manager_without_department_uses_subordinates(self, client: TestClient, manager_token, manager_user, db_session: Session):
        """Manager without department_id should still see direct subordinates."""
        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        mgr.department_id = None
        db_session.commit()

        sub_emp = Employee(
            employee_no="SUB009",
            name="直属下属",
            department_id=None,
            manager_id=mgr.id,
            is_active=True,
        )
        db_session.add(sub_emp)
        db_session.commit()

        resp = client.get("/employees", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        employee_ids = [e["id"] for e in data.get("items", [])]
        assert sub_emp.id in employee_ids, f"Expected direct subordinate {sub_emp.id} in {employee_ids}"
