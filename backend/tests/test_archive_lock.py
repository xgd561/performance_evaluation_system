import pytest
from fastapi.testclient import TestClient
from datetime import date
from app.models import AssessmentCycle, AssessmentRecord, Employee, Department, Position, OperationLog


@pytest.fixture
def published_cycle(db_session):
    """创建一个已发布的考核周期，并关联员工和考核记录"""
    dept = Department(name="测试部", code="TEST_ARC")
    db_session.add(dept)
    db_session.flush()

    pos = Position(name="测试岗位", department_id=dept.id)
    db_session.add(pos)
    db_session.flush()

    emp = Employee(employee_no="ARC001", name="归档员工", department_id=dept.id, position_id=pos.id)
    db_session.add(emp)
    db_session.flush()

    cycle = AssessmentCycle(
        name="归档测试周期",
        type="annual",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="published",
        is_locked=False,
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
        status="published",
        is_locked=False,
    )
    db_session.add(record)
    db_session.commit()

    return cycle


class TestArchiveLockInterceptor:
    """P6-14: 归档锁定后端拦截中间件测试"""

    def _archive_cycle(self, client: TestClient, token, cycle):
        """Helper: 归档周期"""
        resp = client.post(
            f"/api/v1/assessment-cycles/{cycle.id}/archive",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        return resp.json()

    def test_archived_record_blocks_score_update(self, client: TestClient, admin_token, published_cycle, db_session):
        """已归档周期中的考核记录禁止重新评分（返回 400）"""
        record = db_session.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == published_cycle.id).first()
        self._archive_cycle(client, admin_token, published_cycle)

        resp = client.post(
            f"/api/v1/scores/manager/{record.id}",
            json={
                "performance": 80,
                "ability": 75,
                "attitude": 70,
                "comment": "测试评分，至少十个字",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        print("SCORE RESP:", resp.status_code, resp.json())
        assert resp.status_code == 400
        assert "已归档" in resp.json()["message"]

    def test_archived_record_blocks_approval(self, client: TestClient, admin_token, published_cycle, db_session):
        """已归档周期中的考核记录禁止审批（返回 400）"""
        record = db_session.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == published_cycle.id).first()
        # 先把记录状态改为 pending_approval 以便测试审批接口
        record.status = "pending_approval"
        db_session.commit()
        self._archive_cycle(client, admin_token, published_cycle)

        resp = client.post(
            f"/api/v1/approvals/{record.id}/approve",
            json={"comment": "测试审批，至少十个字以上"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 400
        assert "已归档" in resp.json()["message"]

    def test_archived_record_blocks_appeal(self, client: TestClient, admin_token, published_cycle, db_session):
        """已归档周期中的考核记录禁止发起申诉（返回 400）"""
        record = db_session.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == published_cycle.id).first()
        self._archive_cycle(client, admin_token, published_cycle)

        resp = client.post(
            "/api/v1/appeals",
            json={
                "record_id": record.id,
                "reason": "测试申诉理由",
                "detail": "测试申诉详细说明，至少需要二十个字符",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 400
        assert "已归档" in resp.json()["message"]

    def test_archived_record_blocks_interview(self, client: TestClient, admin_token, published_cycle, db_session):
        """已归档周期中的考核记录禁止创建面谈（返回 400）"""
        record = db_session.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == published_cycle.id).first()
        self._archive_cycle(client, admin_token, published_cycle)

        resp = client.post(
            f"/api/v1/interviews/{record.id}",
            json={
                "interview_time": "2026-06-01T10:00:00",
                "location": "会议室A",
                "content": "测试面谈内容",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 400
        assert "已归档" in resp.json()["message"]

    def test_admin_can_unarchive(self, client: TestClient, admin_token, published_cycle, db_session):
        """Admin 可以解冻已归档周期"""
        self._archive_cycle(client, admin_token, published_cycle)

        resp = client.post(
            f"/api/v1/assessment-cycles/{published_cycle.id}/unarchive",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "考核周期已解冻"
        assert data["cycle_id"] == published_cycle.id

        db_session.refresh(published_cycle)
        assert published_cycle.status == "published"
        assert published_cycle.is_locked is False

    def test_unarchive_unlocks_records(self, client: TestClient, admin_token, published_cycle, db_session):
        """解冻后所有关联考核记录应解锁"""
        records = db_session.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == published_cycle.id).all()
        self._archive_cycle(client, admin_token, published_cycle)
        for r in records:
            db_session.refresh(r)
            assert r.is_locked is True

        client.post(
            f"/api/v1/assessment-cycles/{published_cycle.id}/unarchive",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        for r in records:
            db_session.refresh(r)
            assert r.is_locked is False

    def test_unarchive_logs_operation(self, client: TestClient, admin_token, published_cycle, db_session):
        """解冻应记录 operation_logs"""
        self._archive_cycle(client, admin_token, published_cycle)

        client.post(
            f"/api/v1/assessment-cycles/{published_cycle.id}/unarchive",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        log = db_session.query(OperationLog).filter(
            OperationLog.action == "unarchive_cycle",
            OperationLog.target_id == published_cycle.id,
        ).first()
        assert log is not None
        assert log.target_type == "assessment_cycle"
        import json
        new_val = json.loads(log.new_value) if isinstance(log.new_value, str) else log.new_value
        assert new_val["status"] == "published"
        assert new_val["is_locked"] is False
        old_val = json.loads(log.old_value) if isinstance(log.old_value, str) else log.old_value
        assert old_val["status"] == "archived"
        assert old_val["is_locked"] is True

    def test_hr_cannot_unarchive(self, client: TestClient, hr_token, published_cycle, db_session):
        """HR 无权解冻，应返回 403"""
        self._archive_cycle(client, hr_token, published_cycle)

        resp = client.post(
            f"/api/v1/assessment-cycles/{published_cycle.id}/unarchive",
            headers={"Authorization": f"Bearer {hr_token}"},
        )
        assert resp.status_code == 403

    def test_manager_cannot_unarchive(self, client: TestClient, manager_token, published_cycle, db_session):
        """Manager 无权解冻，应返回 403"""
        # 用 admin 归档，因为 manager 无权归档
        client.post(
            f"/api/v1/assessment-cycles/{published_cycle.id}/archive",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        # 归档可能失败（403），但周期状态仍是 published，所以 unarchive 会返回 422
        # 为了测试 403，我们直接请求 unarchive
        resp = client.post(
            f"/api/v1/assessment-cycles/{published_cycle.id}/unarchive",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 403

    def test_unarchive_not_archived_returns_422(self, client: TestClient, admin_token, published_cycle):
        """非 archived 周期解冻应返回 422"""
        resp = client.post(
            f"/api/v1/assessment-cycles/{published_cycle.id}/unarchive",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422
        assert "只有已归档的考核周期才能解冻" in resp.json()["message"]

    def test_unarchive_nonexistent_cycle_returns_404(self, client: TestClient, admin_token):
        """不存在的周期解冻应返回 404"""
        resp = client.post(
            "/api/v1/assessment-cycles/99999/unarchive",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404
        assert "考核周期不存在" in resp.json()["message"]
