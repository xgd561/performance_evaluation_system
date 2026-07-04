import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.utils.data_masking import mask_phone, mask_id_card, mask_unpublished_scores
from app.schemas import AssessmentRecordOut
from app.models import AssessmentRecord, AssessmentCycle, Employee, Department, Position


class TestMaskPhone:
    """Tests for mask_phone"""

    def test_mask_phone_normal(self):
        assert mask_phone("15353639922") == "153****9922"

    def test_mask_phone_acceptance(self):
        """验收标准: mask_phone('1535363992') 返回 '153****3992'"""
        assert mask_phone("1535363992") == "153****3992"

    def test_mask_phone_short(self):
        assert mask_phone("12345") == "*****"

    def test_mask_phone_empty(self):
        assert mask_phone("") == ""


class TestMaskIdCard:
    """Tests for mask_id_card"""

    def test_mask_id_card_normal(self):
        assert mask_id_card("110101199001011234") == "110101********1234"

    def test_mask_id_card_short(self):
        assert mask_id_card("1234567") == "*******"

    def test_mask_id_card_empty(self):
        assert mask_id_card("") == ""


class TestMaskUnpublishedScores:
    """Tests for mask_unpublished_scores dict helper"""

    def test_masks_unpublished(self):
        data = {"status": "pending_self", "total_score": 85.0, "grade": "B"}
        result = mask_unpublished_scores(data)
        assert result["total_score"] is None
        assert result["grade"] is None

    def test_keeps_published(self):
        data = {"status": "published", "total_score": 85.0, "grade": "B"}
        result = mask_unpublished_scores(data)
        assert result["total_score"] == 85.0
        assert result["grade"] == "B"

    def test_keeps_archived(self):
        data = {"status": "archived", "total_score": 90.0, "grade": "A"}
        result = mask_unpublished_scores(data)
        assert result["total_score"] == 90.0
        assert result["grade"] == "A"


class TestAssessmentRecordOutValidator:
    """Tests for AssessmentRecordOut Pydantic model validator"""

    def test_unpublished_masks_total_score_and_grade(self):
        record = AssessmentRecordOut(
            id=1,
            cycle_id=1,
            employee_id=1,
            position_id=None,
            department_id=None,
            status="pending_self",
            total_score=Decimal("85.5"),
            grade="B",
            created_at=None,
        )
        assert record.total_score is None
        assert record.grade is None

    def test_published_shows_total_score_and_grade(self):
        record = AssessmentRecordOut(
            id=1,
            cycle_id=1,
            employee_id=1,
            position_id=None,
            department_id=None,
            status="published",
            total_score=Decimal("85.5"),
            grade="B",
            created_at=None,
        )
        assert record.total_score == Decimal("85.5")
        assert record.grade == "B"

    def test_archived_shows_total_score_and_grade(self):
        record = AssessmentRecordOut(
            id=1,
            cycle_id=1,
            employee_id=1,
            position_id=None,
            department_id=None,
            status="archived",
            total_score=Decimal("90.0"),
            grade="A",
            created_at=None,
        )
        assert record.total_score == Decimal("90.0")
        assert record.grade == "A"


class TestApiScoreMasking:
    """FastAPI TestClient integration tests for score masking in API responses"""

    def test_my_assessment_masks_unpublished_scores(self, client: TestClient, employee_token, employee_user, db_session: Session):
        """员工查看未发布的考核记录时，total_score 和 grade 应为 None"""
        cycle = AssessmentCycle(
            name="测试考核周期",
            type="monthly",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status="pending_approval",
            dimension_weights='{"performance":0.6,"ability":0.2,"attitude":0.2}',
            reviewer_weights='{"performance":{"self":0.3,"manager":0.7},"ability":{"self":0.2,"manager":0.6,"peer":0.2},"attitude":{"self":0.2,"manager":0.8}}',
            grade_rules='{"A":{"min":90,"max":100,"ratio_limit":0.2},"B":{"min":80,"max":89.9,"ratio_limit":0.5},"C":{"min":60,"max":79.9,"ratio_limit":0.25},"D":{"min":0,"max":59.9,"ratio_limit":0.05}}',
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id,
            employee_id=employee_user.employee_id,
            status="pending_approval",
            total_score=85.0,
            grade="B",
        )
        db_session.add(record)
        db_session.commit()

        resp = client.get("/scores/my-assessment", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["status"] == "pending_approval"
        assert item["total_score"] is None
        assert item["grade"] is None

    def test_my_assessment_shows_published_scores(self, client: TestClient, employee_token, employee_user, db_session: Session):
        """员工查看已发布的考核记录时，total_score 和 grade 应可见"""
        cycle = AssessmentCycle(
            name="测试考核周期",
            type="monthly",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status="published",
            dimension_weights='{"performance":0.6,"ability":0.2,"attitude":0.2}',
            reviewer_weights='{"performance":{"self":0.3,"manager":0.7},"ability":{"self":0.2,"manager":0.6,"peer":0.2},"attitude":{"self":0.2,"manager":0.8}}',
            grade_rules='{"A":{"min":90,"max":100,"ratio_limit":0.2},"B":{"min":80,"max":89.9,"ratio_limit":0.5},"C":{"min":60,"max":79.9,"ratio_limit":0.25},"D":{"min":0,"max":59.9,"ratio_limit":0.05}}',
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id,
            employee_id=employee_user.employee_id,
            status="published",
            total_score=85.0,
            grade="B",
        )
        db_session.add(record)
        db_session.commit()

        resp = client.get("/scores/my-assessment", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["status"] == "published"
        assert item["total_score"] is not None
        assert item["total_score"].startswith("85")
        assert item["grade"] == "B"
