"""P6-09: 申诉 review 终审闭环。

产品口径：`review` 是唯一终审入口，复核意见即终审结论，申诉随即结束；
考核记录必须从 `appealed` 回写为 `published`，并向员工推送通知。
"""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import get_password_hash
from app.models import (
    AppealRecord,
    AssessmentCycle,
    AssessmentRecord,
    Department,
    Employee,
    Notification,
    Position,
    User,
)


@pytest.fixture
def appeal_context(db_session: Session, employee_user):
    """构造一条处于申诉中的考核记录，以及对应的申诉记录与员工账号。"""
    dept = Department(name="申诉测试部", code="APL_REVIEW")
    db_session.add(dept)
    db_session.flush()

    pos = Position(name="申诉测试岗", department_id=dept.id)
    db_session.add(pos)
    db_session.flush()

    emp = Employee(
        employee_no="APL001",
        name="申诉员工",
        department_id=dept.id,
        position_id=pos.id,
    )
    db_session.add(emp)
    db_session.flush()

    emp_user = User(
        username="apl001",
        password_hash=get_password_hash("Apl001@123"),
        role="employee",
        employee_id=emp.id,
        is_first_login=False,
    )
    db_session.add(emp_user)
    db_session.flush()

    cycle = AssessmentCycle(
        name="申诉终审周期",
        type="monthly",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        status="published",
    )
    db_session.add(cycle)
    db_session.flush()

    record = AssessmentRecord(
        cycle_id=cycle.id,
        employee_id=emp.id,
        position_id=pos.id,
        department_id=dept.id,
        total_score=85.0,
        grade="B",
        original_grade="B",
        status="appealed",
    )
    db_session.add(record)
    db_session.flush()

    appeal = AppealRecord(
        record_id=record.id,
        employee_id=emp.id,
        reason="对等级划分有异议",
        detail="我认为本次考核等级划分不合理，申请重新复核。",
        status="pending",
    )
    db_session.add(appeal)
    db_session.commit()

    return {"record": record, "appeal": appeal, "employee": emp, "user": emp_user}


class TestAppealReviewFinal:
    """review 即终审：结束申诉并回写考核记录状态"""

    def test_review_approve_restores_record_and_notifies(
        self, client: TestClient, hr_token, appeal_context, db_session: Session
    ):
        """复核通过：申诉置 resolved，考核记录回到 published，员工收到通知"""
        appeal = appeal_context["appeal"]
        record = appeal_context["record"]
        emp_user = appeal_context["user"]

        resp = client.post(
            f"/appeals/{appeal.id}/review",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={"action": "approve", "review_result": "复核通过，维持原等级"},
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"

        db_session.refresh(record)
        db_session.refresh(appeal)
        assert appeal.status == "resolved"
        assert record.status == "published"

        notifications = (
            db_session.query(Notification)
            .filter(Notification.user_id == emp_user.id)
            .all()
        )
        assert len(notifications) == 1
        assert notifications[0].type == "appeal_resolved"

    def test_review_reject_restores_record_and_notifies(
        self, client: TestClient, hr_token, appeal_context, db_session: Session
    ):
        """复核拒绝：申诉置 rejected，考核记录同样回到 published"""
        appeal = appeal_context["appeal"]
        record = appeal_context["record"]
        emp_user = appeal_context["user"]

        resp = client.post(
            f"/appeals/{appeal.id}/review",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={"action": "reject", "review_result": "复核后驳回，维持原结果"},
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

        db_session.refresh(record)
        db_session.refresh(appeal)
        assert appeal.status == "rejected"
        assert record.status == "published"
        assert (
            db_session.query(Notification)
            .filter(Notification.user_id == emp_user.id)
            .count()
            == 1
        )

    def test_review_twice_is_rejected(
        self, client: TestClient, hr_token, appeal_context
    ):
        """终审只允许一次：已处理的申诉再次复核返回 400"""
        appeal = appeal_context["appeal"]

        first = client.post(
            f"/appeals/{appeal.id}/review",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={"action": "approve", "review_result": "复核通过"},
        )
        assert first.status_code == 200

        second = client.post(
            f"/appeals/{appeal.id}/review",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={"action": "reject", "review_result": "再次复核"},
        )
        assert second.status_code == 400
        assert "已" in second.json()["message"]