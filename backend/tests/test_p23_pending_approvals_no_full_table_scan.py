import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.models import (
    AssessmentCycle, Employee, Department, Position, AssessmentRecord, ApprovalRecord
)


class TestP23PendingApprovalsNoFullTableScan:
    """P1-23: get_pending_approvals must avoid full table scan by pre-filtering record IDs."""

    @staticmethod
    def _create_cycle(db: Session):
        cycle = AssessmentCycle(
            name="P23周期",
            type="monthly",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )
        db.add(cycle)
        db.flush()
        return cycle

    @staticmethod
    def _create_record(db: Session, cycle_id, employee_id, dept_id, pos_id, status="pending_approval"):
        record = AssessmentRecord(
            cycle_id=cycle_id,
            employee_id=employee_id,
            department_id=dept_id,
            position_id=pos_id,
            status=status,
        )
        db.add(record)
        db.flush()
        return record

    def test_manager_sees_only_subordinate_records(self, client: TestClient, manager_user, manager_token, db_session: Session):
        """Manager should only see pending_approval records of their subordinates."""
        dept = Department(name="技术部", code="TECH_P23_1")
        db_session.add(dept)
        db_session.flush()

        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        mgr.department_id = dept.id
        db_session.commit()

        pos = Position(name="开发岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()

        sub = Employee(employee_no="SUB001", name="下属", department_id=dept.id, position_id=pos.id, manager_id=mgr.id)
        db_session.add(sub)
        db_session.flush()

        other_dept = Department(name="销售部", code="SALE_P23_1")
        db_session.add(other_dept)
        db_session.flush()
        other_pos = Position(name="销售岗", department_id=other_dept.id)
        db_session.add(other_pos)
        db_session.flush()
        other = Employee(employee_no="OTH001", name="其他员工", department_id=other_dept.id, position_id=other_pos.id)
        db_session.add(other)
        db_session.flush()

        cycle = self._create_cycle(db_session)

        sub_record = self._create_record(db_session, cycle.id, sub.id, dept.id, pos.id)
        other_record = self._create_record(db_session, cycle.id, other.id, other_dept.id, other_pos.id)
        db_session.commit()

        resp = client.get("/approvals/pending", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()

        record_ids = [r["record_id"] for r in data]
        assert sub_record.id in record_ids, "Manager should see subordinate's record"
        assert other_record.id not in record_ids, "Manager should NOT see non-subordinate's record"

    def test_manager_not_sees_record_at_wrong_step(self, client: TestClient, manager_user, manager_token, db_session: Session):
        """Manager should not see subordinate's record if it's at a later step (not direct_manager)."""
        dept = Department(name="技术部", code="TECH_P23_2")
        db_session.add(dept)
        db_session.flush()

        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        mgr.department_id = dept.id
        db_session.commit()

        pos = Position(name="开发岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()

        sub = Employee(employee_no="SUB002", name="下属", department_id=dept.id, position_id=pos.id, manager_id=mgr.id)
        db_session.add(sub)
        db_session.flush()

        cycle = self._create_cycle(db_session)
        record = self._create_record(db_session, cycle.id, sub.id, dept.id, pos.id)

        # Move record to step 1 (dept_head) by adding a fake direct_manager approval
        approval = ApprovalRecord(
            record_id=record.id,
            approver_id=mgr.id,
            approver_role="direct_manager",
            step_index=1,
            action="approved",
            approval_type="normal",
        )
        db_session.add(approval)
        db_session.commit()

        resp = client.get("/approvals/pending", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        record_ids = [r["record_id"] for r in data]
        assert record.id not in record_ids, "Manager should not see record at wrong step"

    def test_dept_head_sees_only_dept_records(self, client: TestClient, manager_user, manager_token, db_session: Session):
        """Dept head should only see pending_approval records at dept_head step for their own department."""
        dept = Department(name="技术部", code="TECH_P23_3")
        db_session.add(dept)
        db_session.flush()

        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        mgr.department_id = dept.id
        db_session.commit()

        # Make manager the department head
        dept.head_id = mgr.id
        db_session.commit()

        pos = Position(name="开发岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()

        emp = Employee(employee_no="EMP001", name="部门员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()

        other_dept = Department(name="销售部", code="SALE_P23_3")
        db_session.add(other_dept)
        db_session.flush()
        other_pos = Position(name="销售岗", department_id=other_dept.id)
        db_session.add(other_pos)
        db_session.flush()
        other = Employee(employee_no="OTH002", name="其他员工", department_id=other_dept.id, position_id=other_pos.id)
        db_session.add(other)
        db_session.flush()

        cycle = self._create_cycle(db_session)

        # Record for dept employee - needs to be at step 1 (dept_head)
        record = self._create_record(db_session, cycle.id, emp.id, dept.id, pos.id)
        approval = ApprovalRecord(
            record_id=record.id,
            approver_id=mgr.id,
            approver_role="direct_manager",
            step_index=1,
            action="approved",
            approval_type="normal",
        )
        db_session.add(approval)

        # Record for other employee - also at step 1
        other_record = self._create_record(db_session, cycle.id, other.id, other_dept.id, other_pos.id)
        other_approval = ApprovalRecord(
            record_id=other_record.id,
            approver_id=other.id,
            approver_role="direct_manager",
            step_index=1,
            action="approved",
            approval_type="normal",
        )
        db_session.add(other_approval)
        db_session.commit()

        resp = client.get("/approvals/pending", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        record_ids = [r["record_id"] for r in data]
        assert record.id in record_ids, "Dept head should see their department's record"
        assert other_record.id not in record_ids, "Dept head should NOT see other department's record"

    def test_manager_without_subordinates_or_dept_head_sees_nothing(self, client: TestClient, manager_user, manager_token, db_session: Session):
        """Manager with no subordinates and not a dept head should see nothing."""
        dept = Department(name="技术部", code="TECH_P23_4")
        db_session.add(dept)
        db_session.flush()

        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        mgr.department_id = dept.id
        # NOT head, no subordinates
        db_session.commit()

        pos = Position(name="开发岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()

        other = Employee(employee_no="OTH003", name="其他员工", department_id=dept.id, position_id=pos.id)
        db_session.add(other)
        db_session.flush()

        cycle = self._create_cycle(db_session)
        self._create_record(db_session, cycle.id, other.id, dept.id, pos.id)
        db_session.commit()

        resp = client.get("/approvals/pending", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 0, "Manager with no role should see no records"

    def test_hr_sees_records_at_hr_step(self, client: TestClient, hr_token, db_session: Session):
        """HR should see all pending_approval records at the hr_head step (step 2 in default chain)."""
        dept = Department(name="技术部", code="TECH_P23_5")
        db_session.add(dept)
        db_session.flush()

        pos = Position(name="开发岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()

        emp = Employee(employee_no="EMP002", name="员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()

        cycle = self._create_cycle(db_session)
        record = self._create_record(db_session, cycle.id, emp.id, dept.id, pos.id)

        # 2 approvals to reach step 2
        app1 = ApprovalRecord(
            record_id=record.id,
            approver_id=emp.id,
            approver_role="direct_manager",
            step_index=1,
            action="approved",
            approval_type="normal",
        )
        db_session.add(app1)
        app2 = ApprovalRecord(
            record_id=record.id,
            approver_id=emp.id,
            approver_role="dept_head",
            step_index=2,
            action="approved",
            approval_type="normal",
        )
        db_session.add(app2)
        db_session.commit()

        resp = client.get("/approvals/pending", headers={"Authorization": f"Bearer {hr_token}"})
        assert resp.status_code == 200
        data = resp.json()
        record_ids = [r["record_id"] for r in data]
        assert record.id in record_ids, "HR should see record at hr_head step"

    def test_hr_not_sees_records_at_wrong_step(self, client: TestClient, hr_token, db_session: Session):
        """HR should not see records that are not at the hr_head step."""
        dept = Department(name="技术部", code="TECH_P23_6")
        db_session.add(dept)
        db_session.flush()

        pos = Position(name="开发岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()

        emp = Employee(employee_no="EMP003", name="员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()

        cycle = self._create_cycle(db_session)
        record = self._create_record(db_session, cycle.id, emp.id, dept.id, pos.id)
        # No approvals, so at step 0 (direct_manager)
        db_session.commit()

        resp = client.get("/approvals/pending", headers={"Authorization": f"Bearer {hr_token}"})
        assert resp.status_code == 200
        data = resp.json()
        record_ids = [r["record_id"] for r in data]
        assert record.id not in record_ids, "HR should not see record at wrong step"

    def test_admin_sees_records_at_hr_step(self, client: TestClient, admin_token, db_session: Session):
        """Admin should see records at hr_head step (since admin can act as hr)."""
        dept = Department(name="技术部", code="TECH_P23_7")
        db_session.add(dept)
        db_session.flush()

        pos = Position(name="开发岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()

        emp = Employee(employee_no="EMP004", name="员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()

        cycle = self._create_cycle(db_session)
        record = self._create_record(db_session, cycle.id, emp.id, dept.id, pos.id)

        # 2 approvals to reach hr_head step
        app1 = ApprovalRecord(
            record_id=record.id,
            approver_id=emp.id,
            approver_role="direct_manager",
            step_index=1,
            action="approved",
            approval_type="normal",
        )
        db_session.add(app1)
        app2 = ApprovalRecord(
            record_id=record.id,
            approver_id=emp.id,
            approver_role="dept_head",
            step_index=2,
            action="approved",
            approval_type="normal",
        )
        db_session.add(app2)
        db_session.commit()

        resp = client.get("/approvals/pending", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        record_ids = [r["record_id"] for r in data]
        assert record.id in record_ids, "Admin should see record at hr_head step"

    def test_empty_result_when_no_matching_records(self, client: TestClient, manager_user, manager_token, db_session: Session):
        """When there are no pending_approval records matching user's role, endpoint should return empty list."""
        # No records created
        resp = client.get("/approvals/pending", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data == []

    def test_endpoint_returns_list_structure(self, client: TestClient, manager_token, db_session: Session):
        """Endpoint should return a list even when empty."""
        resp = client.get("/approvals/pending", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_employee_cannot_access_pending_list(self, client: TestClient, employee_token, db_session: Session):
        """Employee should not be able to access the pending approvals endpoint."""
        resp = client.get("/approvals/pending", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403

    def test_manager_can_access_pending_list(self, client: TestClient, manager_token, db_session: Session):
        """Manager should be able to access the pending approvals endpoint."""
        resp = client.get("/approvals/pending", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200

    def test_hr_can_access_pending_list(self, client: TestClient, hr_token, db_session: Session):
        """HR should be able to access the pending approvals endpoint."""
        resp = client.get("/approvals/pending", headers={"Authorization": f"Bearer {hr_token}"})
        assert resp.status_code == 200

    def test_admin_can_access_pending_list(self, client: TestClient, admin_token, db_session: Session):
        """Admin should be able to access the pending approvals endpoint."""
        resp = client.get("/approvals/pending", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200

    def test_unauthorized_user_cannot_access_pending_list(self, client: TestClient, db_session: Session):
        """Unauthorized user should not be able to access the pending approvals endpoint."""
        resp = client.get("/approvals/pending")
        assert resp.status_code == 401
