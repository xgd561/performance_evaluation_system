import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.models import (
    AssessmentCycle, Employee, Department, Position, ApprovalRecord, AppealRecord, AssessmentRecord, User
)
from app.auth import get_password_hash


class TestDashboardRoleScopedStats:
    """Tests for P1-21: Dashboard should return role-scoped stats, not global sensitive stats."""

    def test_admin_sees_global_stats(self, client: TestClient, admin_token, admin_user, db_session: Session):
        """Admin should see global pending_approvals and pending_appeals."""
        # Create other employee's approval and appeal
        other_dept = Department(name="其他部", code="OTHER_P21_1")
        db_session.add(other_dept)
        db_session.flush()
        other_pos = Position(name="其他岗", department_id=other_dept.id)
        db_session.add(other_pos)
        db_session.flush()
        other_emp = Employee(employee_no="OTH001", name="其他员工", department_id=other_dept.id, position_id=other_pos.id)
        db_session.add(other_emp)
        db_session.flush()

        cycle = AssessmentCycle(
            name="P21周期", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30)
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(cycle_id=cycle.id, employee_id=other_emp.id, status="pending_approval")
        db_session.add(record)
        db_session.flush()

        app = ApprovalRecord(record_id=record.id, approver_id=other_emp.id, step_index=1)
        db_session.add(app)

        appeal = AppealRecord(record_id=record.id, employee_id=other_emp.id, reason="test")
        db_session.add(appeal)
        db_session.commit()

        resp = client.get("/dashboard", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        stats = data["stats"]
        assert stats["pending_approvals"] >= 1
        assert stats["pending_appeals"] >= 1

    def test_hr_sees_global_stats(self, client: TestClient, hr_token, hr_user, db_session: Session):
        """HR should see global pending_approvals and pending_appeals."""
        other_dept = Department(name="其他部", code="OTHER_P21_2")
        db_session.add(other_dept)
        db_session.flush()
        other_pos = Position(name="其他岗", department_id=other_dept.id)
        db_session.add(other_pos)
        db_session.flush()
        other_emp = Employee(employee_no="OTH002", name="其他员工2", department_id=other_dept.id, position_id=other_pos.id)
        db_session.add(other_emp)
        db_session.flush()

        cycle = AssessmentCycle(
            name="P21周期2", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30)
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(cycle_id=cycle.id, employee_id=other_emp.id, status="pending_approval")
        db_session.add(record)
        db_session.flush()

        app = ApprovalRecord(record_id=record.id, approver_id=other_emp.id, step_index=1)
        db_session.add(app)

        appeal = AppealRecord(record_id=record.id, employee_id=other_emp.id, reason="test")
        db_session.add(appeal)
        db_session.commit()

        resp = client.get("/dashboard", headers={"Authorization": f"Bearer {hr_token}"})
        assert resp.status_code == 200
        data = resp.json()
        stats = data["stats"]
        assert stats["pending_approvals"] >= 1
        assert stats["pending_appeals"] >= 1

    def test_manager_sees_team_stats(self, client: TestClient, manager_token, manager_user, db_session: Session):
        """Manager should only see subordinate/department stats, not global."""
        # Setup manager's department
        parent_dept = Department(name="技术部", code="TECH_P21_3")
        db_session.add(parent_dept)
        db_session.flush()

        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        mgr.department_id = parent_dept.id
        db_session.commit()

        # Subordinate in same department
        sub_emp = Employee(employee_no="SUB001", name="下属", department_id=parent_dept.id, manager_id=mgr.id)
        db_session.add(sub_emp)
        db_session.flush()

        # Other employee in other department
        other_dept = Department(name="销售部", code="SALE_P21_3")
        db_session.add(other_dept)
        db_session.flush()
        other_emp = Employee(employee_no="OTH003", name="其他员工3", department_id=other_dept.id)
        db_session.add(other_emp)
        db_session.flush()

        cycle = AssessmentCycle(
            name="P21周期3", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30)
        )
        db_session.add(cycle)
        db_session.flush()

        # Subordinate's record + approval + appeal
        sub_record = AssessmentRecord(cycle_id=cycle.id, employee_id=sub_emp.id, status="pending_approval")
        db_session.add(sub_record)
        db_session.flush()
        sub_app = ApprovalRecord(record_id=sub_record.id, approver_id=sub_emp.id, step_index=1)
        db_session.add(sub_app)
        sub_appeal = AppealRecord(record_id=sub_record.id, employee_id=sub_emp.id, reason="test")
        db_session.add(sub_appeal)

        # Other employee's record + approval + appeal
        other_record = AssessmentRecord(cycle_id=cycle.id, employee_id=other_emp.id, status="pending_approval")
        db_session.add(other_record)
        db_session.flush()
        other_app = ApprovalRecord(record_id=other_record.id, approver_id=other_emp.id, step_index=1)
        db_session.add(other_app)
        other_appeal = AppealRecord(record_id=other_record.id, employee_id=other_emp.id, reason="test")
        db_session.add(other_appeal)
        db_session.commit()

        resp = client.get("/dashboard", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        stats = data["stats"]

        # Manager should see subordinate's stats (1 sub + 1 manager themselves)
        assert stats["total_employees"] >= 2
        # Manager should see subordinate's approval and appeal
        assert stats["pending_approvals"] >= 1
        assert stats["pending_appeals"] >= 1
        # But should NOT see the other department's employee in count
        # The total employees in the system is 3+, manager should see only 2
        all_emp_count = db_session.query(Employee).filter(Employee.is_active == True).count()
        assert stats["total_employees"] < all_emp_count

    def test_employee_sees_own_stats(self, client: TestClient, employee_user, employee_token, db_session: Session):
        """Employee should only see own stats, not global."""
        # Need to set is_first_login=False
        employee_user.is_first_login = False
        db_session.commit()

        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()

        # Other employee's approval and appeal
        other_dept = Department(name="其他部", code="OTHER_P21_4")
        db_session.add(other_dept)
        db_session.flush()
        other_pos = Position(name="其他岗", department_id=other_dept.id)
        db_session.add(other_pos)
        db_session.flush()
        other_emp = Employee(employee_no="OTH004", name="其他员工4", department_id=other_dept.id, position_id=other_pos.id)
        db_session.add(other_emp)
        db_session.flush()

        cycle = AssessmentCycle(
            name="P21周期4", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30)
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(cycle_id=cycle.id, employee_id=other_emp.id, status="pending_approval")
        db_session.add(record)
        db_session.flush()

        other_app = ApprovalRecord(record_id=record.id, approver_id=other_emp.id, step_index=1)
        db_session.add(other_app)

        other_appeal = AppealRecord(record_id=record.id, employee_id=other_emp.id, reason="test")
        db_session.add(other_appeal)
        db_session.commit()

        # Re-login to get fresh token after is_first_login change
        resp = client.post("/auth/login", json={"username": "emp001", "password": "Emp001@123"})
        assert resp.status_code == 200
        fresh_token = resp.json()["access_token"]

        resp = client.get("/dashboard", headers={"Authorization": f"Bearer {fresh_token}"})
        assert resp.status_code == 200
        data = resp.json()
        stats = data["stats"]

        # Employee should only see themselves
        assert stats["total_employees"] == 1
        # No pending approvals/appeals for employee (no records created for them)
        assert stats["pending_approvals"] == 0
        assert stats["pending_appeals"] == 0

    def test_peer_sees_own_stats(self, client: TestClient, peer_token, peer_user, db_session: Session):
        """Peer should only see own stats, not global."""
        # Other employee's approval and appeal
        other_dept = Department(name="其他部", code="OTHER_P21_5")
        db_session.add(other_dept)
        db_session.flush()
        other_pos = Position(name="其他岗", department_id=other_dept.id)
        db_session.add(other_pos)
        db_session.flush()
        other_emp = Employee(employee_no="OTH005", name="其他员工5", department_id=other_dept.id, position_id=other_pos.id)
        db_session.add(other_emp)
        db_session.flush()

        cycle = AssessmentCycle(
            name="P21周期5", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30)
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(cycle_id=cycle.id, employee_id=other_emp.id, status="pending_approval")
        db_session.add(record)
        db_session.flush()

        other_app = ApprovalRecord(record_id=record.id, approver_id=other_emp.id, step_index=1)
        db_session.add(other_app)

        other_appeal = AppealRecord(record_id=record.id, employee_id=other_emp.id, reason="test")
        db_session.add(other_appeal)
        db_session.commit()

        resp = client.get("/dashboard", headers={"Authorization": f"Bearer {peer_token}"})
        assert resp.status_code == 200
        data = resp.json()
        stats = data["stats"]

        # Peer should only see themselves
        assert stats["total_employees"] == 1
        # No pending approvals/appeals for peer (no records created for them)
        assert stats["pending_approvals"] == 0
        assert stats["pending_appeals"] == 0

    def test_employee_not_see_other_appeals(self, client: TestClient, employee_user, employee_token, db_session: Session):
        """Employee should not see other employees' appeals/approvals even if they exist."""
        employee_user.is_first_login = False
        db_session.commit()

        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()

        # Create employee's own approval and appeal
        cycle = AssessmentCycle(
            name="P21周期6", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30)
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(cycle_id=cycle.id, employee_id=emp.id, status="pending_approval")
        db_session.add(record)
        db_session.flush()

        own_app = ApprovalRecord(record_id=record.id, approver_id=emp.id, step_index=1)
        db_session.add(own_app)

        own_appeal = AppealRecord(record_id=record.id, employee_id=emp.id, reason="test")
        db_session.add(own_appeal)

        # Create other employee's approval and appeal
        other_dept = Department(name="其他部", code="OTHER_P21_6")
        db_session.add(other_dept)
        db_session.flush()
        other_pos = Position(name="其他岗", department_id=other_dept.id)
        db_session.add(other_pos)
        db_session.flush()
        other_emp = Employee(employee_no="OTH006", name="其他员工6", department_id=other_dept.id, position_id=other_pos.id)
        db_session.add(other_emp)
        db_session.flush()

        other_record = AssessmentRecord(cycle_id=cycle.id, employee_id=other_emp.id, status="pending_approval")
        db_session.add(other_record)
        db_session.flush()

        other_app = ApprovalRecord(record_id=other_record.id, approver_id=other_emp.id, step_index=1)
        db_session.add(other_app)

        other_appeal = AppealRecord(record_id=other_record.id, employee_id=other_emp.id, reason="test")
        db_session.add(other_appeal)
        db_session.commit()

        # Re-login
        resp = client.post("/auth/login", json={"username": "emp001", "password": "Emp001@123"})
        assert resp.status_code == 200
        fresh_token = resp.json()["access_token"]

        resp = client.get("/dashboard", headers={"Authorization": f"Bearer {fresh_token}"})
        assert resp.status_code == 200
        data = resp.json()
        stats = data["stats"]

        # Employee should only see their own 1 approval and 1 appeal
        assert stats["pending_approvals"] == 1
        assert stats["pending_appeals"] == 1

    def test_manager_not_see_other_dept_appeals(self, client: TestClient, manager_token, manager_user, db_session: Session):
        """Manager should not see appeals/approvals from unrelated departments."""
        parent_dept = Department(name="技术部", code="TECH_P21_7")
        db_session.add(parent_dept)
        db_session.flush()

        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        mgr.department_id = parent_dept.id
        db_session.commit()

        # Subordinate in same department
        sub_emp = Employee(employee_no="SUB002", name="下属2", department_id=parent_dept.id, manager_id=mgr.id)
        db_session.add(sub_emp)
        db_session.flush()

        # Other employee in other department
        other_dept = Department(name="销售部", code="SALE_P21_7")
        db_session.add(other_dept)
        db_session.flush()
        other_emp = Employee(employee_no="OTH007", name="其他员工7", department_id=other_dept.id)
        db_session.add(other_emp)
        db_session.flush()

        cycle = AssessmentCycle(
            name="P21周期7", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30)
        )
        db_session.add(cycle)
        db_session.flush()

        # Subordinate's record + approval + appeal
        sub_record = AssessmentRecord(cycle_id=cycle.id, employee_id=sub_emp.id, status="pending_approval")
        db_session.add(sub_record)
        db_session.flush()
        sub_app = ApprovalRecord(record_id=sub_record.id, approver_id=sub_emp.id, step_index=1)
        db_session.add(sub_app)
        sub_appeal = AppealRecord(record_id=sub_record.id, employee_id=sub_emp.id, reason="test")
        db_session.add(sub_appeal)

        # Other employee's record + approval + appeal (multiple)
        other_record = AssessmentRecord(cycle_id=cycle.id, employee_id=other_emp.id, status="pending_approval")
        db_session.add(other_record)
        db_session.flush()
        other_app = ApprovalRecord(record_id=other_record.id, approver_id=other_emp.id, step_index=1)
        db_session.add(other_app)
        other_appeal = AppealRecord(record_id=other_record.id, employee_id=other_emp.id, reason="test")
        db_session.add(other_appeal)
        db_session.commit()

        resp = client.get("/dashboard", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        stats = data["stats"]

        # Manager should only see 1 subordinate approval and 1 appeal, not the other department's
        assert stats["pending_approvals"] == 1
        assert stats["pending_appeals"] == 1

    def test_executive_sees_global_stats(self, client: TestClient, executive_token, executive_user, db_session: Session):
        """Executive should see global stats like admin/hr."""
        other_dept = Department(name="其他部", code="OTHER_P21_8")
        db_session.add(other_dept)
        db_session.flush()
        other_pos = Position(name="其他岗", department_id=other_dept.id)
        db_session.add(other_pos)
        db_session.flush()
        other_emp = Employee(employee_no="OTH008", name="其他员工8", department_id=other_dept.id, position_id=other_pos.id)
        db_session.add(other_emp)
        db_session.flush()

        cycle = AssessmentCycle(
            name="P21周期8", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30)
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(cycle_id=cycle.id, employee_id=other_emp.id, status="pending_approval")
        db_session.add(record)
        db_session.flush()

        app = ApprovalRecord(record_id=record.id, approver_id=other_emp.id, step_index=1)
        db_session.add(app)

        appeal = AppealRecord(record_id=record.id, employee_id=other_emp.id, reason="test")
        db_session.add(appeal)
        db_session.commit()

        resp = client.get("/dashboard", headers={"Authorization": f"Bearer {executive_token}"})
        assert resp.status_code == 200
        data = resp.json()
        stats = data["stats"]
        assert stats["pending_approvals"] >= 1
        assert stats["pending_appeals"] >= 1

    def test_manager_sees_sub_department_stats(self, client: TestClient, manager_token, manager_user, db_session: Session):
        """Manager should see stats from sub-departments."""
        parent_dept = Department(name="技术部", code="TECH_P21_9")
        db_session.add(parent_dept)
        db_session.flush()

        sub_dept = Department(name="前端组", code="FE_P21_9", parent_id=parent_dept.id)
        db_session.add(sub_dept)
        db_session.flush()

        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        mgr.department_id = parent_dept.id
        db_session.commit()

        # Employee in sub-department
        sub_emp = Employee(employee_no="SUB003", name="子部门员工", department_id=sub_dept.id)
        db_session.add(sub_emp)
        db_session.flush()

        cycle = AssessmentCycle(
            name="P21周期9", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30)
        )
        db_session.add(cycle)
        db_session.flush()

        sub_record = AssessmentRecord(cycle_id=cycle.id, employee_id=sub_emp.id, status="pending_approval")
        db_session.add(sub_record)
        db_session.flush()
        sub_app = ApprovalRecord(record_id=sub_record.id, approver_id=sub_emp.id, step_index=1)
        db_session.add(sub_app)
        sub_appeal = AppealRecord(record_id=sub_record.id, employee_id=sub_emp.id, reason="test")
        db_session.add(sub_appeal)
        db_session.commit()

        resp = client.get("/dashboard", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        stats = data["stats"]

        # Manager should see sub-department employee in count
        assert stats["total_employees"] >= 2  # manager + sub dept employee
        # Manager should see sub-department approval and appeal
        assert stats["pending_approvals"] >= 1
        assert stats["pending_appeals"] >= 1
