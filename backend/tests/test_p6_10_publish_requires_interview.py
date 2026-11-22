"""P6-10: 面谈是发布前的强制节点。

产品口径：周期发布（publish）只能把「已完成面谈」的记录置为 published；
仍处于 pending_interview 且没有面谈记录的记录必须阻断发布，并明确提示数量。
"""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    AssessmentCycle,
    AssessmentRecord,
    Department,
    Employee,
    Position,
)


def _build_cycle_with_record(db_session: Session, employee_no: str, status: str):
    cycle = AssessmentCycle(
        name=f"发布校验-{employee_no}",
        type="monthly",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        status="pending_approval",
    )
    db_session.add(cycle)
    db_session.flush()

    dept = Department(name=f"发布校验部-{employee_no}", code=f"PUB_{employee_no}")
    db_session.add(dept)
    db_session.flush()

    pos = Position(name="校验岗", department_id=dept.id)
    db_session.add(pos)
    db_session.flush()

    emp = Employee(
        employee_no=employee_no,
        name=f"员工{employee_no}",
        department_id=dept.id,
        position_id=pos.id,
    )
    db_session.add(emp)
    db_session.flush()

    record = AssessmentRecord(
        cycle_id=cycle.id,
        employee_id=emp.id,
        position_id=pos.id,
        department_id=dept.id,
        total_score=85.0,
        grade="B",
        status=status,
        is_locked=False,
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(cycle)
    db_session.refresh(record)
    return cycle, record


class TestPublishRequiresInterview:
    def test_publish_blocked_when_interview_missing(
        self, client: TestClient, admin_token, db_session: Session
    ):
        cycle, record = _build_cycle_with_record(
            db_session, "PUB001", status="pending_interview"
        )

        resp = client.post(
            f"/assessment-cycles/{cycle.id}/publish",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
        assert "面谈" in resp.json()["message"]
        db_session.refresh(record)
        db_session.refresh(cycle)
        assert record.status == "pending_interview"
        assert cycle.status != "published"

    def test_publish_succeeds_when_all_interviews_completed(
        self, client: TestClient, admin_token, db_session: Session
    ):
        cycle, record = _build_cycle_with_record(
            db_session, "PUB002", status="pending_interview"
        )
        record.interview_record = {
            "interview_time": "2026-01-01T10:00:00",
            "location": "会议室",
            "content": "已完成绩效面谈，就本期评分依据与改进方向达成一致。",
            "improvement_plan": None,
            "interviewer_id": 1,
            "interviewer_name": "张经理",
        }
        db_session.commit()

        resp = client.post(
            f"/assessment-cycles/{cycle.id}/publish",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        db_session.refresh(record)
        db_session.refresh(cycle)
        assert record.status == "published"
        assert cycle.status == "published"

    def test_publish_message_reports_missing_interview_count(
        self, client: TestClient, admin_token, db_session: Session
    ):
        cycle, first = _build_cycle_with_record(
            db_session, "PUB003", status="pending_interview"
        )
        dept = db_session.query(Department).filter(Department.code == "PUB_PUB003").first()
        pos = db_session.query(Position).filter(Position.department_id == dept.id).first()
        emp = Employee(
            employee_no="PUB004",
            name="员工PUB004",
            department_id=dept.id,
            position_id=pos.id,
        )
        db_session.add(emp)
        db_session.flush()
        second = AssessmentRecord(
            cycle_id=cycle.id,
            employee_id=emp.id,
            position_id=pos.id,
            department_id=dept.id,
            total_score=88.0,
            grade="B",
            status="pending_interview",
            is_locked=False,
        )
        db_session.add(second)
        db_session.commit()

        resp = client.post(
            f"/assessment-cycles/{cycle.id}/publish",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert resp.status_code == 422
        assert "2" in resp.json()["message"]