import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.models import AssessmentRecord, AssessmentCycle, Employee, Department, Position, User, AppealRecord
from app.auth import get_password_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_cycle(db_session: Session, status: str = "published"):
    cycle = AssessmentCycle(
        name="申诉复核周期",
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


def _create_record(db_session: Session, cycle_id: int, employee_id: int, status: str = "appealed", grade: str = "B"):
    record = AssessmentRecord(
        cycle_id=cycle_id,
        employee_id=employee_id,
        status=status,
        self_scores='{"performance":80,"ability":70,"attitude":90}',
        manager_scores='{"performance":85,"ability":75,"attitude":95}',
        total_score=85.0,
        grade=grade,
        original_grade=grade,
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


def _create_appeal(db_session: Session, record_id: int, employee_id: int):
    appeal = AppealRecord(
        record_id=record_id,
        employee_id=employee_id,
        reason="我认为我的绩效评定结果不符合预期，需要重新复核",
        status="pending",
    )
    db_session.add(appeal)
    db_session.commit()
    db_session.refresh(appeal)
    return appeal


# ---------------------------------------------------------------------------
# P6-06: 申诉复核接口
# ---------------------------------------------------------------------------

class TestAppealResolve:
    """Tests for POST /appeals/{id}/resolve"""

    def test_resolve_maintain_success(self, client: TestClient, hr_token, employee_user, db_session: Session):
        """HR 复核维持原结果，状态回 published，员工收到通知"""
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="appealed", grade="B")
        appeal = _create_appeal(db_session, record.id, employee_user.employee_id)

        resp = client.post(
            f"/appeals/{appeal.id}/resolve",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={"resolution": "maintain", "comment": "经复核，维持原评定结果"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == appeal.id
        assert data["status"] == "resolved"
        assert data["resolution"] == "maintain"
        assert data["new_grade"] is None

        # 考核记录状态回 published
        db_session.refresh(record)
        assert record.status == "published"
        assert record.grade == "B"

    def test_resolve_adjust_success(self, client: TestClient, hr_token, employee_user, db_session: Session):
        """HR 复核调整等级，grade 更新，状态回 published"""
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="appealed", grade="B")
        appeal = _create_appeal(db_session, record.id, employee_user.employee_id)

        resp = client.post(
            f"/appeals/{appeal.id}/resolve",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={"resolution": "adjust", "new_grade": "A", "comment": "经复核，等级调整为 A"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["resolution"] == "adjust"
        assert data["new_grade"] == "A"

        db_session.refresh(record)
        assert record.status == "published"
        assert record.grade == "A"

    def test_resolve_employee_forbidden(self, client: TestClient, employee_token, employee_user, db_session: Session):
        """员工访问返回 403"""
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="appealed")
        appeal = _create_appeal(db_session, record.id, employee_user.employee_id)

        resp = client.post(
            f"/appeals/{appeal.id}/resolve",
            headers={"Authorization": f"Bearer {employee_token}"},
            json={"resolution": "maintain", "comment": "test"},
        )
        assert resp.status_code == 403

    def test_resolve_manager_forbidden(self, client: TestClient, manager_token, employee_user, db_session: Session):
        """经理访问返回 403"""
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="appealed")
        appeal = _create_appeal(db_session, record.id, employee_user.employee_id)

        resp = client.post(
            f"/appeals/{appeal.id}/resolve",
            headers={"Authorization": f"Bearer {manager_token}"},
            json={"resolution": "maintain", "comment": "test"},
        )
        assert resp.status_code == 403

    def test_resolve_not_found(self, client: TestClient, hr_token):
        """申诉记录不存在返回 404"""
        resp = client.post(
            "/appeals/99999/resolve",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={"resolution": "maintain", "comment": "test"},
        )
        assert resp.status_code == 404

    def test_resolve_record_not_appealed(self, client: TestClient, hr_token, employee_user, db_session: Session):
        """考核记录状态不是 appealed 返回 400"""
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="published", grade="B")
        appeal = _create_appeal(db_session, record.id, employee_user.employee_id)

        resp = client.post(
            f"/appeals/{appeal.id}/resolve",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={"resolution": "maintain", "comment": "test"},
        )
        assert resp.status_code == 400

    def test_resolve_invalid_resolution(self, client: TestClient, hr_token, employee_user, db_session: Session):
        """resolution 非法返回 422"""
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="appealed")
        appeal = _create_appeal(db_session, record.id, employee_user.employee_id)

        resp = client.post(
            f"/appeals/{appeal.id}/resolve",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={"resolution": "invalid", "comment": "test"},
        )
        assert resp.status_code == 422

    def test_resolve_adjust_missing_grade(self, client: TestClient, hr_token, employee_user, db_session: Session):
        """adjust 时缺少 new_grade 返回 422"""
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="appealed")
        appeal = _create_appeal(db_session, record.id, employee_user.employee_id)

        resp = client.post(
            f"/appeals/{appeal.id}/resolve",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={"resolution": "adjust", "comment": "test"},
        )
        assert resp.status_code == 422
