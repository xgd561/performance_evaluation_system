import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Employee, Department, AssessmentRecord, AssessmentCycle, AppealRecord
from datetime import date


class TestAppealsReview:
    """Tests for appeal review with result modification"""

    def test_approve_appeal_with_new_score(self, client: TestClient, hr_user, employee_user, db_session: Session):
        """HR can approve appeal and update score/grade"""
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()

        cycle = AssessmentCycle(
            name="测试周期", type="季度",
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            status="published",
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id, employee_id=emp.id,
            total_score=75, grade="C", status="published",
        )
        db_session.add(record)
        db_session.flush()

        appeal = AppealRecord(
            record_id=record.id,
            employee_id=emp.id,
            reason="评分不公",
            detail="自评分90，上级评75",
            status="pending",
        )
        db_session.add(appeal)
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "hr001", "password": "Hr001@123"})
        hr_token = resp.json()["access_token"]

        resp = client.post(
            f"/appeals/{appeal.id}/review",
            json={
                "action": "approve",
                "review_result": "经复核，自评分依据充分，调整总分",
                "total_score": 85,
                "grade": "B",
            },
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "resolved"

        # Verify record updated
        db_session.refresh(record)
        assert record.total_score == 85
        assert record.grade == "B"

    def test_reject_appeal_keeps_original(self, client: TestClient, hr_user, employee_user, db_session: Session):
        """Rejecting appeal should not change score/grade"""
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()

        cycle = AssessmentCycle(
            name="测试周期", type="季度",
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            status="published",
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id, employee_id=emp.id,
            total_score=75, grade="C", status="published",
        )
        db_session.add(record)
        db_session.flush()

        appeal = AppealRecord(
            record_id=record.id,
            employee_id=emp.id,
            reason="评分不公",
            status="pending",
        )
        db_session.add(appeal)
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "hr001", "password": "Hr001@123"})
        hr_token = resp.json()["access_token"]

        resp = client.post(
            f"/appeals/{appeal.id}/review",
            json={
                "action": "reject",
                "review_result": "经复核，评分依据充分，维持原结果",
                "total_score": 90,
                "grade": "A",
            },
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"

        # Verify record NOT updated
        db_session.refresh(record)
        assert record.total_score == 75
        assert record.grade == "C"
