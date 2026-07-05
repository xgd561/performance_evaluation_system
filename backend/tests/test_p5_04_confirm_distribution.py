import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    Employee,
    Department,
    Position,
    AssessmentRecord,
    AssessmentCycle,
    OperationLog,
)
from datetime import date


class TestP5_04ConfirmDistribution:
    """P5-04: 确认强制分布调整接口测试"""

    @pytest.fixture(scope="function")
    def setup_cycle_and_records(self, db_session: Session):
        """创建考核周期及 pending_distribution_review 状态的记录"""
        dept = Department(name="技术部", code="TECH")
        db_session.add(dept)
        db_session.flush()

        employees = []
        for i in range(3):
            emp = Employee(
                employee_no=f"EMP{i:03d}",
                name=f"员工{i}",
                department_id=dept.id,
            )
            db_session.add(emp)
            db_session.flush()
            employees.append(emp)

        cycle = AssessmentCycle(
            name="测试周期",
            type="季度",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            status="pending_distribution_review",
        )
        db_session.add(cycle)
        db_session.flush()

        records = []
        for i, emp in enumerate(employees):
            record = AssessmentRecord(
                cycle_id=cycle.id,
                employee_id=emp.id,
                department_id=dept.id,
                total_score=90 + i,
                grade="A" if i == 0 else "B",
                original_grade="B" if i == 0 else "A",  # grade != original_grade
                status="pending_distribution_review",
            )
            db_session.add(record)
            records.append(record)
        db_session.commit()

        yield {"cycle": cycle, "records": records, "dept": dept, "employees": employees}

    def test_confirm_distribution_success(self, client: TestClient, admin_token, setup_cycle_and_records, db_session: Session):
        """成功确认强制分布调整，记录状态变为 pending_approval，original_grade 被更新为 grade"""
        cycle = setup_cycle_and_records["cycle"]
        records = setup_cycle_and_records["records"]

        resp = client.post(
            f"/scores/cycles/{cycle.id}/confirm-distribution",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated"] == 3
        assert data["cycle_id"] == cycle.id
        assert data["status"] == "pending_approval"
        assert data["skipped"] == []

        for r in records:
            db_session.refresh(r)
            assert r.status == "pending_approval"
            assert r.original_grade == r.grade

    def test_confirm_distribution_404_nonexistent_cycle(self, client: TestClient, admin_token):
        """非存在的周期返回 404"""
        resp = client.post(
            "/scores/cycles/999999/confirm-distribution",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    def test_confirm_distribution_forbidden_employee(self, client: TestClient, employee_token):
        """普通员工角色无权访问，返回 403"""
        resp = client.post(
            "/scores/cycles/1/confirm-distribution",
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 403

    def test_confirm_distribution_forbidden_manager(self, client: TestClient, manager_token):
        """manager 角色无权访问，返回 403"""
        resp = client.post(
            "/scores/cycles/1/confirm-distribution",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 403

    def test_confirm_distribution_idempotency(self, client: TestClient, admin_token, setup_cycle_and_records, db_session: Session):
        """幂等性：再次调用对已处于 pending_approval 的记录应返回 0 更新"""
        cycle = setup_cycle_and_records["cycle"]

        # 第一次调用
        resp = client.post(
            f"/scores/cycles/{cycle.id}/confirm-distribution",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] == 3

        # 第二次调用
        resp = client.post(
            f"/scores/cycles/{cycle.id}/confirm-distribution",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated"] == 0
        assert data["status"] == "pending_approval"

    def test_confirm_distribution_logs_operation(self, client: TestClient, admin_token, setup_cycle_and_records, db_session: Session):
        """操作日志被正确记录"""
        cycle = setup_cycle_and_records["cycle"]

        resp = client.post(
            f"/scores/cycles/{cycle.id}/confirm-distribution",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

        log = (
            db_session.query(OperationLog)
            .filter(OperationLog.action == "confirm_distribution")
            .filter(OperationLog.target_type == "assessment_cycle")
            .filter(OperationLog.target_id == cycle.id)
            .first()
        )
        assert log is not None
        assert "pending_distribution_review" in log.old_value
        assert "pending_approval" in log.new_value

    def test_confirm_distribution_skips_none_grade(self, client: TestClient, admin_token, setup_cycle_and_records, db_session: Session):
        """grade 为 None 的记录应被跳过，其他记录正常处理"""
        cycle = setup_cycle_and_records["cycle"]
        records = setup_cycle_and_records["records"]

        # 将第一条记录的 grade 设为 None
        records[0].grade = None
        db_session.commit()

        resp = client.post(
            f"/scores/cycles/{cycle.id}/confirm-distribution",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated"] == 2
        assert len(data["skipped"]) == 1
        assert data["skipped"][0]["record_id"] == records[0].id

        db_session.refresh(records[0])
        db_session.refresh(records[1])
        db_session.refresh(records[2])
        assert records[0].status == "pending_distribution_review"
        assert records[1].status == "pending_approval"
        assert records[2].status == "pending_approval"
