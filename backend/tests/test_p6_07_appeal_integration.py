import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.models import AssessmentRecord, AssessmentCycle, Employee, Department, Position, User, AppealRecord


def _create_cycle(db_session: Session, status: str = "published"):
    cycle = AssessmentCycle(
        name="申诉集成周期",
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


def _create_record(db_session: Session, cycle_id: int, employee_id: int, status: str = "published", grade: str = "B"):
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


class TestAppealIntegration:
    """集成测试：覆盖员工创建申诉 -> HR 处理（maintain/adjust）完整工作流"""

    def test_appeal_full_flow_maintain(self, client: TestClient, employee_token, hr_token, employee_user, db_session: Session):
        """员工创建申诉 -> HR 列表可见 -> HR 处理 maintain -> 状态回 published"""
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="published", grade="B")

        # 员工创建申诉
        resp = client.post("/appeals", headers={"Authorization": f"Bearer {employee_token}"}, json={
            "record_id": record.id,
            "reason": "我认为我的绩效评定结果不符合预期，需要重新复核",
        })
        assert resp.status_code == 201
        appeal_id = resp.json()["id"]

        # 将记录状态改为 appealed（模拟状态机流转）
        record.status = "appealed"
        db_session.commit()

        # HR 列表可见
        resp = client.get("/appeals", headers={"Authorization": f"Bearer {hr_token}"})
        assert resp.status_code == 200
        assert any(a["id"] == appeal_id for a in resp.json())

        # HR 处理 maintain
        resp = client.post(f"/appeals/{appeal_id}/resolve", headers={"Authorization": f"Bearer {hr_token}"}, json={
            "resolution": "maintain",
            "comment": "经复核，维持原评定结果",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["resolution"] == "maintain"
        assert data["new_grade"] is None

        # 验证状态回 published
        db_session.refresh(record)
        assert record.status == "published"
        assert record.grade == "B"

    def test_appeal_full_flow_adjust(self, client: TestClient, employee_token, hr_token, employee_user, db_session: Session):
        """员工创建申诉 -> HR 处理 adjust -> grade 更新为 A"""
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="published", grade="B")

        resp = client.post("/appeals", headers={"Authorization": f"Bearer {employee_token}"}, json={
            "record_id": record.id,
            "reason": "我认为我的绩效评定结果不符合预期，需要重新复核",
        })
        assert resp.status_code == 201
        appeal_id = resp.json()["id"]

        record.status = "appealed"
        db_session.commit()

        resp = client.post(f"/appeals/{appeal_id}/resolve", headers={"Authorization": f"Bearer {hr_token}"}, json={
            "resolution": "adjust",
            "new_grade": "A",
            "comment": "经复核，等级调整为 A",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["resolution"] == "adjust"
        assert data["new_grade"] == "A"

        db_session.refresh(record)
        assert record.status == "published"
        assert record.grade == "A"

    def test_appeal_reject_reason_too_short(self, client: TestClient, employee_token, employee_user, db_session: Session):
        """申诉理由少于 20 字返回 422"""
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="published")

        resp = client.post("/appeals", headers={"Authorization": f"Bearer {employee_token}"}, json={
            "record_id": record.id,
            "reason": "太短",
        })
        assert resp.status_code == 422

    def test_appeal_reject_not_published_status(self, client: TestClient, employee_token, employee_user, db_session: Session):
        """非 published 状态记录不能申诉"""
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="pending_approval")

        resp = client.post("/appeals", headers={"Authorization": f"Bearer {employee_token}"}, json={
            "record_id": record.id,
            "reason": "我认为我的绩效评定结果不符合预期，需要重新复核",
        })
        assert resp.status_code == 400

    def test_appeal_employee_cannot_resolve(self, client: TestClient, employee_token, employee_user, db_session: Session):
        """员工不能处理自己的申诉"""
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="published")

        resp = client.post("/appeals", headers={"Authorization": f"Bearer {employee_token}"}, json={
            "record_id": record.id,
            "reason": "我认为我的绩效评定结果不符合预期，需要重新复核",
        })
        appeal_id = resp.json()["id"]
        record.status = "appealed"
        db_session.commit()

        resp = client.post(f"/appeals/{appeal_id}/resolve", headers={"Authorization": f"Bearer {employee_token}"}, json={
            "resolution": "maintain",
            "comment": "test",
        })
        assert resp.status_code == 403

    def test_appeal_already_resolved_cannot_re_resolve(self, client: TestClient, employee_token, hr_token, employee_user, db_session: Session):
        """已处理申诉不能再次处理"""
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="published", grade="B")

        resp = client.post("/appeals", headers={"Authorization": f"Bearer {employee_token}"}, json={
            "record_id": record.id,
            "reason": "我认为我的绩效评定结果不符合预期，需要重新复核",
        })
        appeal_id = resp.json()["id"]

        record.status = "appealed"
        db_session.commit()

        # 第一次处理
        resp = client.post(f"/appeals/{appeal_id}/resolve", headers={"Authorization": f"Bearer {hr_token}"}, json={
            "resolution": "maintain",
            "comment": "第一次处理",
        })
        assert resp.status_code == 200

        # 再次处理应失败（因为 record 状态已不是 appealed）
        resp = client.post(f"/appeals/{appeal_id}/resolve", headers={"Authorization": f"Bearer {hr_token}"}, json={
            "resolution": "adjust",
            "new_grade": "A",
            "comment": "第二次处理",
        })
        assert resp.status_code == 400

    def test_appeal_list_my_appeals(self, client: TestClient, employee_token, employee_user, db_session: Session):
        """员工查看我的申诉列表"""
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="published")

        resp = client.post("/appeals", headers={"Authorization": f"Bearer {employee_token}"}, json={
            "record_id": record.id,
            "reason": "我认为我的绩效评定结果不符合预期，需要重新复核",
        })
        assert resp.status_code == 201

        resp = client.get("/appeals/my-appeals", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any("不符合预期" in item["reason"] for item in data)
