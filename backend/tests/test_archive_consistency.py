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


class TestArchiveCycle:
    """P6-10: 归档后端接口严格测试"""

    def test_archive_success_by_hr(self, client: TestClient, hr_token, published_cycle, db_session):
        """HR 归档已发布周期应成功，并返回正确结构"""
        resp = client.post(
            f"/api/v1/assessment-cycles/{published_cycle.id}/archive",
            headers={"Authorization": f"Bearer {hr_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "考核周期已归档"
        assert data["cycle_id"] == published_cycle.id

        # 数据库状态验证
        db_session.refresh(published_cycle)
        assert published_cycle.status == "archived"
        assert published_cycle.is_locked is True
        assert published_cycle.archived_at is not None

    def test_archive_success_by_admin(self, client: TestClient, admin_token, published_cycle, db_session):
        """Admin 归档已发布周期应成功"""
        resp = client.post(
            f"/api/v1/assessment-cycles/{published_cycle.id}/archive",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        db_session.refresh(published_cycle)
        assert published_cycle.status == "archived"
        assert published_cycle.archived_at is not None

    def test_archive_locks_all_assessment_records(self, client: TestClient, hr_token, published_cycle, db_session):
        """归档后所有关联考核记录应被锁定"""
        records = db_session.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == published_cycle.id).all()
        assert len(records) > 0
        for r in records:
            assert r.is_locked is False

        client.post(
            f"/api/v1/assessment-cycles/{published_cycle.id}/archive",
            headers={"Authorization": f"Bearer {hr_token}"},
        )

        for r in records:
            db_session.refresh(r)
            assert r.is_locked is True

    def test_archive_records_operation_log(self, client: TestClient, hr_token, published_cycle, db_session):
        """归档应记录 operation_logs，包含 archived_at"""
        client.post(
            f"/api/v1/assessment-cycles/{published_cycle.id}/archive",
            headers={"Authorization": f"Bearer {hr_token}"},
        )

        log = db_session.query(OperationLog).filter(
            OperationLog.action == "archive_cycle",
            OperationLog.target_id == published_cycle.id,
        ).first()
        assert log is not None
        assert log.target_type == "assessment_cycle"
        import json
        new_val = json.loads(log.new_value) if isinstance(log.new_value, str) else log.new_value
        assert new_val["status"] == "archived"
        assert new_val["is_locked"] is True
        assert "archived_at" in new_val

    def test_archive_not_published_returns_422(self, client: TestClient, hr_token, db_session):
        """非 published 周期归档应返回 422"""
        cycle = AssessmentCycle(
            name="未发布周期",
            type="annual",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status="not_started",
        )
        db_session.add(cycle)
        db_session.commit()

        resp = client.post(
            f"/api/v1/assessment-cycles/{cycle.id}/archive",
            headers={"Authorization": f"Bearer {hr_token}"},
        )
        assert resp.status_code == 422
        assert "只有已发布的考核周期才能归档" in resp.json()["message"]

    def test_archive_nonexistent_cycle_returns_404(self, client: TestClient, hr_token):
        """不存在的周期归档应返回 404"""
        resp = client.post(
            "/api/v1/assessment-cycles/99999/archive",
            headers={"Authorization": f"Bearer {hr_token}"},
        )
        assert resp.status_code == 404
        assert "考核周期不存在" in resp.json()["message"]

    def test_archive_by_manager_returns_403(self, client: TestClient, manager_token, published_cycle):
        """Manager 角色无权归档，应返回 403"""
        resp = client.post(
            f"/api/v1/assessment-cycles/{published_cycle.id}/archive",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 403

    def test_archive_by_employee_returns_403(self, client: TestClient, employee_token, published_cycle):
        """Employee 角色无权归档，应返回 403"""
        resp = client.post(
            f"/api/v1/assessment-cycles/{published_cycle.id}/archive",
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 403

    def test_archive_prevents_edit_cycle(self, client: TestClient, hr_token, published_cycle, db_session):
        """已归档周期禁止编辑（或至少 is_locked=True）"""
        client.post(
            f"/api/v1/assessment-cycles/{published_cycle.id}/archive",
            headers={"Authorization": f"Bearer {hr_token}"},
        )
        db_session.refresh(published_cycle)
        assert published_cycle.is_locked is True
        assert published_cycle.status == "archived"

    def test_archive_prevents_score_update(self, client: TestClient, hr_token, published_cycle, db_session):
        """已归档周期中的考核记录禁止重新评分（is_locked=True）"""
        record = db_session.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == published_cycle.id).first()
        assert record is not None
        assert record.is_locked is False

        client.post(
            f"/api/v1/assessment-cycles/{published_cycle.id}/archive",
            headers={"Authorization": f"Bearer {hr_token}"},
        )

        db_session.refresh(record)
        assert record.is_locked is True
