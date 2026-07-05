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
# P1-18: 考核结果发布后员工可见
# ---------------------------------------------------------------------------

class TestPublicationVisibility:
    """Tests for P1-18: employees should only see scores after publication."""

    def test_my_assessment_masks_unpublished_scores(self, client: TestClient, employee_token, employee_user, db_session: Session):
        """Employee should see masked scores for unpublished records."""
        cycle = _create_cycle(db_session, status="pending_approval")
        record = _create_record(
            db_session,
            cycle.id,
            employee_user.employee_id,
            status="pending_approval",
            self_scores='{"performance":80,"ability":70,"attitude":90}',
            manager_scores='{"performance":85,"ability":75,"attitude":95}',
            peer_scores='{"performance":82,"ability":72,"attitude":92}',
            weighted_performance=83.0,
            weighted_ability=73.0,
            weighted_attitude=93.0,
            total_score=85.0,
            grade="B",
            original_grade="B",
            manager_comment="表现良好",
        )

        resp = client.get("/scores/my-assessment", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["record_id"] == record.id
        assert item["status"] == "pending_approval"
        # self_scores is visible to employee even for unpublished records; other scores are masked
        assert item["self_scores"] == {"performance": 80, "ability": 70, "attitude": 90}
        assert item["manager_scores"] == {}
        assert item["peer_scores"] == {}
        assert item["weighted_performance"] is None
        assert item["weighted_ability"] is None
        assert item["weighted_attitude"] is None
        assert item["total_score"] is None
        assert item["grade"] is None
        assert item["original_grade"] is None
        assert item["manager_comment"] is None

    def test_my_assessment_shows_published_scores(self, client: TestClient, employee_token, employee_user, db_session: Session):
        """Employee should see full scores for published records."""
        cycle = _create_cycle(db_session, status="published")
        record = _create_record(
            db_session,
            cycle.id,
            employee_user.employee_id,
            status="published",
            self_scores='{"performance":80,"ability":70,"attitude":90}',
            manager_scores='{"performance":85,"ability":75,"attitude":95}',
            peer_scores='{"performance":82,"ability":72,"attitude":92}',
            weighted_performance=83.0,
            weighted_ability=73.0,
            weighted_attitude=93.0,
            total_score=85.0,
            grade="B",
            original_grade="B",
            manager_comment="表现良好",
        )

        resp = client.get("/scores/my-assessment", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["record_id"] == record.id
        assert item["status"] == "published"
        # Scores should be visible
        assert item["self_scores"] == {"performance": 80, "ability": 70, "attitude": 90}
        assert item["manager_scores"] == {"performance": 85, "ability": 75, "attitude": 95}
        assert item["peer_scores"] == {"performance": 82, "ability": 72, "attitude": 92}
        assert item["weighted_performance"].startswith("83")
        assert item["weighted_ability"].startswith("73")
        assert item["weighted_attitude"].startswith("93")
        assert item["total_score"].startswith("85")
        assert item["grade"] == "B"
        assert item["original_grade"] == "B"
        assert item["manager_comment"] == "表现良好"

    def test_my_assessment_detail_unpublished_forbidden(self, client: TestClient, employee_token, employee_user, db_session: Session):
        """Employee should get 403 when viewing detail of unpublished record."""
        cycle = _create_cycle(db_session, status="pending_approval")
        record = _create_record(
            db_session,
            cycle.id,
            employee_user.employee_id,
            status="pending_approval",
            total_score=85.0,
            grade="B",
        )

        resp = client.get(f"/scores/records/{record.id}/detail", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403
        assert "尚未发布" in resp.json()["message"]

    def test_my_assessment_detail_published_ok(self, client: TestClient, employee_token, employee_user, db_session: Session):
        """Employee should be able to view detail of published record."""
        cycle = _create_cycle(db_session, status="published")
        record = _create_record(
            db_session,
            cycle.id,
            employee_user.employee_id,
            status="published",
            total_score=85.0,
            grade="B",
            manager_comment="表现良好",
        )

        resp = client.get(f"/scores/records/{record.id}/detail", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["record_id"] == record.id
        assert data["total_score"].startswith("85")
        assert data["grade"] == "B"
        assert data["manager_comment"] == "表现良好"

    def test_trend_filters_unpublished_for_employee(self, client: TestClient, employee_token, employee_user, db_session: Session):
        """Employee trend should only include published/archived records."""
        cycle_unpublished = _create_cycle(db_session, status="pending_approval")
        cycle_published = _create_cycle(db_session, status="published")
        cycle_archived = _create_cycle(db_session, status="archived")

        # Unpublished record
        _create_record(
            db_session,
            cycle_unpublished.id,
            employee_user.employee_id,
            status="pending_approval",
            total_score=70.0,
            grade="C",
        )
        # Published record
        _create_record(
            db_session,
            cycle_published.id,
            employee_user.employee_id,
            status="published",
            total_score=85.0,
            grade="B",
        )
        # Archived record
        _create_record(
            db_session,
            cycle_archived.id,
            employee_user.employee_id,
            status="archived",
            total_score=90.0,
            grade="A",
        )

        resp = client.get(f"/reports/employee/{employee_user.employee_id}/trend", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        for item in data["items"]:
            assert item["status"] in ["published", "archived"]
            # Verify scores are present
            assert item["total_score"] is not None

    def test_manager_can_view_unpublished_detail(self, client: TestClient, manager_token, employee_user, db_session: Session):
        """Manager should still be able to view unpublished record detail."""
        cycle = _create_cycle(db_session, status="pending_approval")
        record = _create_record(
            db_session,
            cycle.id,
            employee_user.employee_id,
            status="pending_approval",
            total_score=85.0,
            grade="B",
        )
        # Link employee to manager
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        mgr = db_session.query(Employee).filter(Employee.employee_no == "MGR001").first()
        if emp and mgr:
            emp.manager_id = mgr.id
            db_session.commit()

        resp = client.get(f"/scores/records/{record.id}/detail", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["record_id"] == record.id
        assert data["total_score"].startswith("85")

    def test_admin_can_view_unpublished_trend(self, client: TestClient, admin_token, employee_user, db_session: Session):
        """Admin trend should include unpublished records."""
        cycle = _create_cycle(db_session, status="pending_approval")
        _create_record(
            db_session,
            cycle.id,
            employee_user.employee_id,
            status="pending_approval",
            total_score=70.0,
            grade="C",
        )

        resp = client.get(f"/reports/employee/{employee_user.employee_id}/trend", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "pending_approval"
