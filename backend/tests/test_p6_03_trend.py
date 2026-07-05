import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date, timedelta
import json

from app.models import AssessmentRecord, AssessmentCycle, Employee, Department, Position, User
from app.auth import get_password_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_cycle(db_session: Session, name: str = "测试考核周期", status: str = "pending_self"):
    cycle = AssessmentCycle(
        name=name,
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


def _create_record(db_session: Session, cycle_id: int, employee_id: int, status: str = "pending_self", **kwargs):
    record = AssessmentRecord(
        cycle_id=cycle_id,
        employee_id=employee_id,
        status=status,
        **kwargs,
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


# ---------------------------------------------------------------------------
# P6-03: 员工历史绩效趋势
# ---------------------------------------------------------------------------

class TestP6_03Trend:
    """Tests for GET /reports/employee/{employee_id}/trend"""

    # 1. Employee sees own trend with default limit 8
    def test_employee_sees_own_trend_default_limit(self, client: TestClient, employee_token, employee_user, db_session: Session):
        """Employee can view their own trend; default limit is 8."""
        for i in range(10):
            cycle = _create_cycle(db_session, name=f"周期{i}", status="published")
            _create_record(
                db_session,
                cycle.id,
                employee_user.employee_id,
                status="published",
                total_score=80.0 + i,
                grade="B",
            )

        resp = client.get(
            f"/reports/employee/{employee_user.employee_id}/trend",
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 8
        assert len(data["items"]) == 8

    # 2. Employee sees own trend with limit=4
    def test_employee_sees_own_trend_limit_4(self, client: TestClient, employee_token, employee_user, db_session: Session):
        """Employee can view their own trend with a custom limit of 4."""
        for i in range(6):
            cycle = _create_cycle(db_session, name=f"周期{i}", status="published")
            _create_record(
                db_session,
                cycle.id,
                employee_user.employee_id,
                status="published",
                total_score=80.0 + i,
                grade="B",
            )

        resp = client.get(
            f"/reports/employee/{employee_user.employee_id}/trend?limit=4",
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 4
        assert len(data["items"]) == 4

    # 3. Employee cannot see another employee's trend (403)
    def test_employee_cannot_see_other_employee_trend(self, client: TestClient, employee_token, employee_user, db_session: Session):
        """Employee gets 403 when trying to view another employee's trend."""
        # Create another employee
        dept = Department(name="其他部", code="OTHER")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="其他岗位", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        other_emp = Employee(employee_no="OTHER001", name="其他员工", department_id=dept.id, position_id=pos.id)
        db_session.add(other_emp)
        db_session.flush()

        cycle = _create_cycle(db_session, status="published")
        _create_record(db_session, cycle.id, other_emp.id, status="published", total_score=85.0, grade="B")

        resp = client.get(
            f"/reports/employee/{other_emp.id}/trend",
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 403
        assert "只能查看本人" in resp.json()["message"]

    # 4. Employee trend excludes non-published/archived records
    def test_employee_trend_excludes_non_published_archived(self, client: TestClient, employee_token, employee_user, db_session: Session):
        """Employee trend should only include published and archived records."""
        cycle_pending = _create_cycle(db_session, name="pending", status="pending_self")
        cycle_published = _create_cycle(db_session, name="published", status="published")
        cycle_archived = _create_cycle(db_session, name="archived", status="archived")
        cycle_approval = _create_cycle(db_session, name="approval", status="pending_approval")

        _create_record(db_session, cycle_pending.id, employee_user.employee_id, status="pending_self", total_score=70.0, grade="C")
        _create_record(db_session, cycle_published.id, employee_user.employee_id, status="published", total_score=85.0, grade="B")
        _create_record(db_session, cycle_archived.id, employee_user.employee_id, status="archived", total_score=90.0, grade="A")
        _create_record(db_session, cycle_approval.id, employee_user.employee_id, status="pending_approval", total_score=75.0, grade="C")

        resp = client.get(
            f"/reports/employee/{employee_user.employee_id}/trend",
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        for item in data["items"]:
            assert item["status"] in ["published", "archived"]

    # 5. Manager can see subordinate's trend
    def test_manager_can_see_subordinate_trend(self, client: TestClient, manager_token, manager_user, employee_user, db_session: Session):
        """Manager can view subordinate's trend."""
        mgr_emp = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        emp.manager_id = mgr_emp.id
        emp.department_id = mgr_emp.department_id
        db_session.commit()

        cycle = _create_cycle(db_session, status="published")
        _create_record(db_session, cycle.id, emp.id, status="published", total_score=88.0, grade="B")

        resp = client.get(
            f"/reports/employee/{emp.id}/trend",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["total_score"].startswith("88")

    # 6. Manager can see own trend
    def test_manager_can_see_own_trend(self, client: TestClient, manager_token, manager_user, db_session: Session):
        """Manager can view their own trend."""
        cycle = _create_cycle(db_session, status="published")
        _create_record(db_session, cycle.id, manager_user.employee_id, status="published", total_score=92.0, grade="A")

        resp = client.get(
            f"/reports/employee/{manager_user.employee_id}/trend",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["total_score"].startswith("92")

    # 7. Peer gets 403
    def test_peer_gets_403(self, client: TestClient, peer_token, employee_user, db_session: Session):
        """Peer role should get 403 for any employee trend."""
        cycle = _create_cycle(db_session, status="published")
        _create_record(db_session, cycle.id, employee_user.employee_id, status="published", total_score=85.0, grade="B")

        resp = client.get(
            f"/reports/employee/{employee_user.employee_id}/trend",
            headers={"Authorization": f"Bearer {peer_token}"},
        )
        assert resp.status_code == 403
        assert "无权" in resp.json()["message"]

    # 8. Admin can see any employee's trend
    def test_admin_can_see_any_employee_trend(self, client: TestClient, admin_token, employee_user, db_session: Session):
        """Admin can view any employee's trend, including unpublished records."""
        cycle = _create_cycle(db_session, status="pending_approval")
        _create_record(db_session, cycle.id, employee_user.employee_id, status="pending_approval", total_score=70.0, grade="C")

        resp = client.get(
            f"/reports/employee/{employee_user.employee_id}/trend",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "pending_approval"

    # 9. Limit validation (limit=0 returns 422, limit=21 returns 422)
    def test_limit_validation_zero(self, client: TestClient, admin_token, employee_user, db_session: Session):
        """limit=0 should return 422 Unprocessable Entity."""
        resp = client.get(
            f"/reports/employee/{employee_user.employee_id}/trend?limit=0",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    def test_limit_validation_too_large(self, client: TestClient, admin_token, employee_user, db_session: Session):
        """limit=21 should return 422 Unprocessable Entity."""
        resp = client.get(
            f"/reports/employee/{employee_user.employee_id}/trend?limit=21",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422
