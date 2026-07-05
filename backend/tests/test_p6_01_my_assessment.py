import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date, timedelta
import json

from app.models import (
    AssessmentRecord, AssessmentCycle, Employee, Department, Position,
    ScoreDetail, AppealRecord, User
)
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


def _create_score_detail(db_session: Session, record_id: int, kpi_name: str, weight: float, target_value: str, self_score=None, manager_score=None):
    detail = ScoreDetail(
        record_id=record_id,
        kpi_name=kpi_name,
        weight=weight,
        target_value=target_value,
        self_score=self_score,
        manager_score=manager_score,
    )
    db_session.add(detail)
    db_session.commit()
    db_session.refresh(detail)
    return detail


def _create_appeal(db_session: Session, record_id: int, employee_id: int, reason: str, detail: str, status: str = "pending"):
    appeal = AppealRecord(
        record_id=record_id,
        employee_id=employee_id,
        reason=reason,
        detail=detail,
        status=status,
    )
    db_session.add(appeal)
    db_session.commit()
    db_session.refresh(appeal)
    return appeal


# ---------------------------------------------------------------------------
# 1. Employee gets their own published assessment with all enhanced fields
# ---------------------------------------------------------------------------

class TestMyAssessmentPublished:
    """Tests for GET /scores/my-assessment with published status."""

    def test_employee_published_assessment_with_enhanced_fields(self, client: TestClient, employee_token, employee_user, db_session: Session):
        """Employee should see full scores, KPI details, distribution override, appeal, and published_at for published record."""
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
            is_distribution_override=True,
            override_reason="部门强制分布调整",
        )

        # Create KPI score details
        detail1 = _create_score_detail(db_session, record.id, "销售额完成率", 0.5, "100万", self_score=85, manager_score=88)
        detail2 = _create_score_detail(db_session, record.id, "客户满意度", 0.3, "95%", self_score=90, manager_score=92)
        detail3 = _create_score_detail(db_session, record.id, "项目交付及时率", 0.2, "100%", self_score=80, manager_score=85)

        # Create appeal record
        appeal = _create_appeal(db_session, record.id, employee_user.employee_id, "对评分有异议", "认为自评分更合理", status="pending")

        resp = client.get("/scores/my-assessment", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["record_id"] == record.id
        assert item["status"] == "published"

        # Enhanced fields should be present
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

        # KPI details
        assert len(item["kpi_details"]) == 3
        kpi_names = [d["kpi_name"] for d in item["kpi_details"]]
        assert "销售额完成率" in kpi_names
        assert "客户满意度" in kpi_names
        assert "项目交付及时率" in kpi_names

        # Distribution override
        assert item["is_distribution_override"] is True
        assert item["override_reason"] == "部门强制分布调整"

        # Appeal
        assert item["appeal"] is not None
        assert item["appeal"]["id"] == appeal.id
        assert item["appeal"]["reason"] == "对评分有异议"
        assert item["appeal"]["detail"] == "认为自评分更合理"
        assert item["appeal"]["status"] == "pending"

        # published_at
        assert item["published_at"] is not None


# ---------------------------------------------------------------------------
# 2. Employee gets archived assessment with all enhanced fields
# ---------------------------------------------------------------------------

class TestMyAssessmentArchived:
    """Tests for GET /scores/my-assessment with archived status."""

    def test_employee_archived_assessment_with_enhanced_fields(self, client: TestClient, employee_token, employee_user, db_session: Session):
        """Employee should see full scores, KPI details, distribution override, appeal, and published_at for archived record."""
        cycle = _create_cycle(db_session, status="archived")
        record = _create_record(
            db_session,
            cycle.id,
            employee_user.employee_id,
            status="archived",
            self_scores='{"performance":90,"ability":85,"attitude":88}',
            manager_scores='{"performance":92,"ability":87,"attitude":89}',
            peer_scores='{"performance":91,"ability":86,"attitude":88}',
            weighted_performance=91.0,
            weighted_ability=86.0,
            weighted_attitude=88.0,
            total_score=90.0,
            grade="A",
            original_grade="A",
            manager_comment="表现优秀",
            is_distribution_override=False,
            override_reason=None,
        )

        # Create KPI score details
        _create_score_detail(db_session, record.id, "销售额完成率", 0.5, "100万", self_score=90, manager_score=92)
        _create_score_detail(db_session, record.id, "客户满意度", 0.3, "95%", self_score=85, manager_score=87)
        _create_score_detail(db_session, record.id, "项目交付及时率", 0.2, "100%", self_score=88, manager_score=90)

        # Create resolved appeal
        appeal = _create_appeal(db_session, record.id, employee_user.employee_id, "对评分有异议", "认为评分偏低", status="resolved")
        appeal.review_result = "维持原评分"
        db_session.commit()
        db_session.refresh(appeal)

        resp = client.get("/scores/my-assessment", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["record_id"] == record.id
        assert item["status"] == "archived"

        # Enhanced fields should be present
        assert item["self_scores"] == {"performance": 90, "ability": 85, "attitude": 88}
        assert item["manager_scores"] == {"performance": 92, "ability": 87, "attitude": 89}
        assert item["peer_scores"] == {"performance": 91, "ability": 86, "attitude": 88}
        assert item["weighted_performance"].startswith("91")
        assert item["weighted_ability"].startswith("86")
        assert item["weighted_attitude"].startswith("88")
        assert item["total_score"].startswith("90")
        assert item["grade"] == "A"
        assert item["original_grade"] == "A"
        assert item["manager_comment"] == "表现优秀"

        # KPI details
        assert len(item["kpi_details"]) == 3

        # Distribution override
        assert item["is_distribution_override"] is False
        assert item["override_reason"] is None

        # Appeal
        assert item["appeal"] is not None
        assert item["appeal"]["id"] == appeal.id
        assert item["appeal"]["status"] == "resolved"
        assert item["appeal"]["review_result"] == "维持原评分"

        # published_at
        assert item["published_at"] is not None


# ---------------------------------------------------------------------------
# 3. Non-published/non-archived status returns None for enhanced fields
# ---------------------------------------------------------------------------

class TestMyAssessmentNonPublished:
    """Tests for GET /scores/my-assessment with non-published/non-archived statuses."""

    def test_pending_self_returns_none_enhanced_fields(self, client: TestClient, employee_token, employee_user, db_session: Session):
        """pending_self status should return None/empty for enhanced fields."""
        cycle = _create_cycle(db_session, status="pending_self")
        record = _create_record(
            db_session,
            cycle.id,
            employee_user.employee_id,
            status="pending_self",
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
            is_distribution_override=True,
            override_reason="部门强制分布调整",
        )

        # Create score details and appeal (should be hidden)
        _create_score_detail(db_session, record.id, "销售额完成率", 0.5, "100万", self_score=85, manager_score=88)
        _create_appeal(db_session, record.id, employee_user.employee_id, "对评分有异议", "认为自评分更合理")

        resp = client.get("/scores/my-assessment", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["record_id"] == record.id
        assert item["status"] == "pending_self"

        # Scores should be masked (self_scores is visible to employee even when unpublished)
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

        # Enhanced fields should be None/empty
        assert item["kpi_details"] == []
        assert item["is_distribution_override"] is None
        assert item["override_reason"] is None
        assert item["appeal"] is None
        assert item["published_at"] is None

    def test_pending_manager_returns_none_enhanced_fields(self, client: TestClient, employee_token, employee_user, db_session: Session):
        """pending_manager status should return None/empty for enhanced fields."""
        cycle = _create_cycle(db_session, status="pending_manager")
        record = _create_record(
            db_session,
            cycle.id,
            employee_user.employee_id,
            status="pending_manager",
            total_score=85.0,
            grade="B",
        )

        resp = client.get("/scores/my-assessment", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["status"] == "pending_manager"
        assert item["total_score"] is None
        assert item["grade"] is None
        assert item["kpi_details"] == []
        assert item["is_distribution_override"] is None
        assert item["override_reason"] is None
        assert item["appeal"] is None
        assert item["published_at"] is None

    def test_pending_approval_returns_none_enhanced_fields(self, client: TestClient, employee_token, employee_user, db_session: Session):
        """pending_approval status should return None/empty for enhanced fields."""
        cycle = _create_cycle(db_session, status="pending_approval")
        record = _create_record(
            db_session,
            cycle.id,
            employee_user.employee_id,
            status="pending_approval",
            total_score=90.0,
            grade="A",
        )

        resp = client.get("/scores/my-assessment", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["status"] == "pending_approval"
        assert item["total_score"] is None
        assert item["grade"] is None
        assert item["kpi_details"] == []
        assert item["is_distribution_override"] is None
        assert item["override_reason"] is None
        assert item["appeal"] is None
        assert item["published_at"] is None


# ---------------------------------------------------------------------------
# 4. 404 when no assessment record exists
# ---------------------------------------------------------------------------

class TestMyAssessmentNoRecord:
    """Tests for GET /scores/my-assessment when no records exist."""

    def test_no_assessment_record_returns_empty(self, client: TestClient, employee_token, employee_user, db_session: Session):
        """When employee has no assessment records, should return empty items and total 0."""
        # Ensure no records exist for this employee
        existing = db_session.query(AssessmentRecord).filter(
            AssessmentRecord.employee_id == employee_user.employee_id
        ).all()
        for r in existing:
            db_session.delete(r)
        db_session.commit()

        resp = client.get("/scores/my-assessment", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []


# ---------------------------------------------------------------------------
# 5. Manager role can access their own my-assessment
# ---------------------------------------------------------------------------

class TestMyAssessmentManagerRole:
    """Tests for GET /scores/my-assessment with manager role."""

    def test_manager_can_access_own_my_assessment(self, client: TestClient, manager_token, manager_user, db_session: Session):
        """Manager with employee role should be able to access their own my-assessment endpoint."""
        cycle = _create_cycle(db_session, status="published")
        record = _create_record(
            db_session,
            cycle.id,
            manager_user.employee_id,
            status="published",
            self_scores='{"performance":88,"ability":82,"attitude":90}',
            manager_scores='{"performance":90,"ability":85,"attitude":92}',
            peer_scores='{"performance":89,"ability":83,"attitude":91}',
            weighted_performance=89.0,
            weighted_ability=84.0,
            weighted_attitude=91.0,
            total_score=88.0,
            grade="B",
            original_grade="B",
            manager_comment="管理表现良好",
            is_distribution_override=False,
            override_reason=None,
        )

        # Create KPI score details
        _create_score_detail(db_session, record.id, "团队目标完成率", 0.6, "100%", self_score=88, manager_score=90)
        _create_score_detail(db_session, record.id, "下属培养", 0.4, "5人", self_score=85, manager_score=87)

        resp = client.get("/scores/my-assessment", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["record_id"] == record.id
        assert item["status"] == "published"

        # Enhanced fields should be present for manager too (manager role is not treated as employee in the endpoint logic)
        assert item["self_scores"] == {"performance": 88, "ability": 82, "attitude": 90}
        assert item["manager_scores"] == {"performance": 90, "ability": 85, "attitude": 92}
        assert item["peer_scores"] == {"performance": 89, "ability": 83, "attitude": 91}
        assert item["total_score"].startswith("88")
        assert item["grade"] == "B"
        assert item["manager_comment"] == "管理表现良好"

        # KPI details
        assert len(item["kpi_details"]) == 2
        kpi_names = [d["kpi_name"] for d in item["kpi_details"]]
        assert "团队目标完成率" in kpi_names
        assert "下属培养" in kpi_names

        # Distribution override
        assert item["is_distribution_override"] is False
        assert item["override_reason"] is None

        # Appeal should be None
        assert item["appeal"] is None

        # published_at
        assert item["published_at"] is not None

    def test_manager_unpublished_record_masks_fields(self, client: TestClient, manager_token, manager_user, db_session: Session):
        """Manager's own unpublished record should show full scores but None for enhanced fields that depend on published status."""
        cycle = _create_cycle(db_session, status="pending_manager")
        record = _create_record(
            db_session,
            cycle.id,
            manager_user.employee_id,
            status="pending_manager",
            total_score=85.0,
            grade="B",
        )

        resp = client.get("/scores/my-assessment", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["status"] == "pending_manager"
        # Manager role sees full scores even for unpublished records (role != "employee")
        assert item["total_score"] is not None
        assert item["grade"] is not None
        assert item["kpi_details"] == []
        # For manager role, is_distribution_override returns the actual boolean value (False default), not None
        assert item["is_distribution_override"] is False
        assert item["override_reason"] is None
        assert item["appeal"] is None
        # published_at returns updated_at for manager role too since masking only applies to employee role
        assert item["published_at"] is not None
