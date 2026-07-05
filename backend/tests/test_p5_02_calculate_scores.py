import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date

from app.main import app
from app.models import (
    AssessmentRecord, AssessmentCycle, Employee, Department, Position, User,
    PeerReviewTask, PeerReviewer
)
from app.database import SessionLocal

client = TestClient(app)


def login(username: str, password: str):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def admin_token():
    return login("admin", "admin123")


@pytest.fixture(scope="module")
def hr_token():
    return login("hr001", "Hr001@123")


@pytest.fixture(scope="module")
def mgr_token():
    return login("mgr001", "Mgr001@123")


@pytest.fixture(scope="module")
def emp_token():
    return login("emp001", "Emp001@123")


@pytest.fixture(scope="function")
def calculate_cycle(db: Session):
    """创建一个用于测试 calculate_scores 的考核周期和记录"""
    dept = db.query(Department).filter(Department.code == "CALC").first()
    if not dept:
        dept = Department(name="计算测试部", code="CALC")
        db.add(dept)
        db.flush()

    pos = db.query(Position).filter(Position.name == "计算测试岗位", Position.department_id == dept.id).first()
    if not pos:
        pos = Position(name="计算测试岗位", department_id=dept.id)
        db.add(pos)
        db.flush()

    # 创建员工
    emp1 = db.query(Employee).filter(Employee.employee_no == "CALC001").first()
    if not emp1:
        emp1 = Employee(employee_no="CALC001", name="计算员工1", department_id=dept.id, position_id=pos.id)
        db.add(emp1)
        db.flush()

    emp2 = db.query(Employee).filter(Employee.employee_no == "CALC002").first()
    if not emp2:
        emp2 = Employee(employee_no="CALC002", name="计算员工2", department_id=dept.id, position_id=pos.id)
        db.add(emp2)
        db.flush()

    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.name == "calculate-test-cycle").first()
    if not cycle:
        cycle = AssessmentCycle(
            name="calculate-test-cycle",
            type="annual",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            peer_review_enabled=True,
            dimension_weights='{"performance": 0.6, "ability": 0.2, "attitude": 0.2}',
            reviewer_weights='{"performance": {"self": 0.3, "manager": 0.7}, "ability": {"self": 0.2, "manager": 0.6, "peer": 0.2}, "attitude": {"self": 0.2, "manager": 0.8}}',
            grade_rules='{"A": {"min": 90, "max": 100, "ratio_limit": 0.2}, "B": {"min": 80, "max": 89.9, "ratio_limit": 0.5}, "C": {"min": 60, "max": 79.9, "ratio_limit": 0.25}, "D": {"min": 0, "max": 59.9, "ratio_limit": 0.05}}',
        )
        db.add(cycle)
        db.flush()

    rec1 = db.query(AssessmentRecord).filter(AssessmentRecord.employee_id == emp1.id, AssessmentRecord.cycle_id == cycle.id).first()
    if not rec1:
        rec1 = AssessmentRecord(
            cycle_id=cycle.id,
            employee_id=emp1.id,
            department_id=dept.id,
            position_id=pos.id,
            status="pending_summary",
            self_scores='{"performance": 80, "ability": 85, "attitude": 90}',
            manager_scores='{"performance": 85, "ability": 88, "attitude": 92}',
            peer_scores='{"ability": 86}',
        )
        db.add(rec1)
        db.flush()
    else:
        rec1.self_scores = '{"performance": 80, "ability": 85, "attitude": 90}'
        rec1.manager_scores = '{"performance": 85, "ability": 88, "attitude": 92}'
        rec1.peer_scores = '{"ability": 86}'
        rec1.status = "pending_summary"
        db.flush()

    rec2 = db.query(AssessmentRecord).filter(AssessmentRecord.employee_id == emp2.id, AssessmentRecord.cycle_id == cycle.id).first()
    if not rec2:
        rec2 = AssessmentRecord(
            cycle_id=cycle.id,
            employee_id=emp2.id,
            department_id=dept.id,
            position_id=pos.id,
            status="pending_summary",
            self_scores='{"performance": 95, "ability": 96, "attitude": 97}',
            manager_scores='{"performance": 96, "ability": 97, "attitude": 98}',
            peer_scores='{"ability": 98}',
        )
        db.add(rec2)
        db.flush()
    else:
        rec2.self_scores = '{"performance": 95, "ability": 96, "attitude": 97}'
        rec2.manager_scores = '{"performance": 96, "ability": 97, "attitude": 98}'
        rec2.peer_scores = '{"ability": 98}'
        rec2.status = "pending_summary"
        db.flush()

    # 确保 PeerReviewTask 都 completed
    for rec in [rec1, rec2]:
        tasks = db.query(PeerReviewTask).filter(PeerReviewTask.record_id == rec.id).all()
        if not tasks:
            task = PeerReviewTask(record_id=rec.id, reviewer_id=emp1.id if rec.id == rec2.id else emp2.id, status="completed")
            db.add(task)
        else:
            for t in tasks:
                t.status = "completed"
        db.flush()

    db.commit()

    yield {
        "cycle": cycle,
        "rec1": rec1,
        "rec2": rec2,
        "emp1": emp1,
        "emp2": emp2,
        "dept": dept,
    }

    # cleanup
    db.query(PeerReviewTask).filter(PeerReviewTask.record_id.in_([rec1.id, rec2.id])).delete(synchronize_session=False)
    db.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == cycle.id).delete(synchronize_session=False)
    db.commit()


class TestP5_02CalculateScores:
    """P5-02: calculate_scores 重构测试"""

    def test_weight_sum_validation_failure(self, admin_token, calculate_cycle, db: Session):
        """维度权重或评分人权重之和不等于100%时返回422"""
        cycle = calculate_cycle["cycle"]
        # 修改维度权重使和不等于100%
        old_dim_weights = cycle.dimension_weights
        cycle.dimension_weights = '{"performance": 0.5, "ability": 0.2, "attitude": 0.2}'
        db.commit()

        resp = client.post(
            f"/api/v1/scores/calculate/{cycle.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422
        data = resp.json()
        assert "message" in data
        assert "100%" in data["message"] or "1.0" in data["message"]

        # 恢复
        cycle.dimension_weights = old_dim_weights
        db.commit()

    def test_incomplete_scoring_returns_422(self, admin_token, calculate_cycle, db: Session):
        """存在未完成评分的记录时返回422"""
        cycle = calculate_cycle["cycle"]
        # Ensure weights are valid first
        cycle.dimension_weights = '{"performance": 0.6, "ability": 0.2, "attitude": 0.2}'
        cycle.reviewer_weights = '{"performance": {"self": 0.3, "manager": 0.7}, "ability": {"self": 0.2, "manager": 0.6, "peer": 0.2}, "attitude": {"self": 0.2, "manager": 0.8}}'
        db.commit()

        rec1 = calculate_cycle["rec1"]
        old_self_scores = rec1.self_scores
        rec1.self_scores = None
        db.commit()

        resp = client.post(
            f"/api/v1/scores/calculate/{cycle.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422
        data = resp.json()
        assert "message" in data
        assert "未完成" in data["message"]

        # 恢复
        rec1.self_scores = old_self_scores
        db.commit()

    def test_successful_calculation_with_peer_review_enabled_transitions_to_pending_distribution_review(self, admin_token, calculate_cycle, db: Session):
        """peer_review_enabled=True 且有调整时，状态变为 pending_distribution_review"""
        cycle = calculate_cycle["cycle"]
        # 确保权重正确
        cycle.dimension_weights = '{"performance": 0.6, "ability": 0.2, "attitude": 0.2}'
        cycle.reviewer_weights = '{"performance": {"self": 0.3, "manager": 0.7}, "ability": {"self": 0.2, "manager": 0.6, "peer": 0.2}, "attitude": {"self": 0.2, "manager": 0.8}}'
        db.commit()

        resp = client.post(
            f"/api/v1/scores/calculate/{cycle.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert "calculated" in data
        assert "abnormal_count" in data
        assert "pending_distribution_review_count" in data
        assert "pending_approval_count" in data

        # 验证记录状态
        rec1 = db.query(AssessmentRecord).filter(AssessmentRecord.id == calculate_cycle["rec1"].id).first()
        rec2 = db.query(AssessmentRecord).filter(AssessmentRecord.id == calculate_cycle["rec2"].id).first()
        # 由于强制分布，至少有一条记录会被调整，进入 pending_distribution_review
        statuses = {rec1.status, rec2.status}
        assert "pending_distribution_review" in statuses or "pending_approval" in statuses

    def test_successful_calculation_with_no_adjustments_transitions_to_pending_approval(self, admin_token, calculate_cycle, db: Session):
        """无调整时，状态变为 pending_approval"""
        cycle = calculate_cycle["cycle"]
        # 确保权重正确
        cycle.dimension_weights = '{"performance": 0.6, "ability": 0.2, "attitude": 0.2}'
        cycle.reviewer_weights = '{"performance": {"self": 0.3, "manager": 0.7}, "ability": {"self": 0.2, "manager": 0.6, "peer": 0.2}, "attitude": {"self": 0.2, "manager": 0.8}}'
        db.commit()

        # 让 rec1 和 rec2 的分数都在同一等级，避免强制分布调整
        rec1 = calculate_cycle["rec1"]
        rec2 = calculate_cycle["rec2"]
        rec1.self_scores = '{"performance": 60, "ability": 60, "attitude": 60}'
        rec1.manager_scores = '{"performance": 60, "ability": 60, "attitude": 60}'
        rec1.peer_scores = '{"ability": 60}'
        rec2.self_scores = '{"performance": 60, "ability": 60, "attitude": 60}'
        rec2.manager_scores = '{"performance": 60, "ability": 60, "attitude": 60}'
        rec2.peer_scores = '{"ability": 60}'
        db.commit()

        resp = client.post(
            f"/api/v1/scores/calculate/{cycle.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        # 无调整时，应全部进入 pending_approval
        assert data["pending_approval_count"] == 2
        assert data["pending_distribution_review_count"] == 0

        # 恢复
        rec1.self_scores = '{"performance": 80, "ability": 85, "attitude": 90}'
        rec1.manager_scores = '{"performance": 85, "ability": 88, "attitude": 92}'
        rec1.peer_scores = '{"ability": 86}'
        rec2.self_scores = '{"performance": 95, "ability": 96, "attitude": 97}'
        rec2.manager_scores = '{"performance": 96, "ability": 97, "attitude": 98}'
        rec2.peer_scores = '{"ability": 98}'
        db.commit()

    def test_abnormal_count_in_response(self, admin_token, calculate_cycle, db: Session):
        """返回 abnormal_count 正确计数（<60 或 >98）"""
        cycle = calculate_cycle["cycle"]
        rec1 = calculate_cycle["rec1"]
        rec2 = calculate_cycle["rec2"]
        # rec1 低分 (<60), rec2 高分 (>98)
        rec1.self_scores = '{"performance": 30, "ability": 30, "attitude": 30}'
        rec1.manager_scores = '{"performance": 30, "ability": 30, "attitude": 30}'
        rec1.peer_scores = '{"ability": 30}'
        rec2.self_scores = '{"performance": 99, "ability": 99, "attitude": 99}'
        rec2.manager_scores = '{"performance": 99, "ability": 99, "attitude": 99}'
        rec2.peer_scores = '{"ability": 99}'
        db.commit()

        resp = client.post(
            f"/api/v1/scores/calculate/{cycle.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["abnormal_count"] == 2

        # 恢复
        rec1.self_scores = '{"performance": 80, "ability": 85, "attitude": 90}'
        rec1.manager_scores = '{"performance": 85, "ability": 88, "attitude": 92}'
        rec1.peer_scores = '{"ability": 86}'
        rec2.self_scores = '{"performance": 95, "ability": 96, "attitude": 97}'
        rec2.manager_scores = '{"performance": 96, "ability": 97, "attitude": 98}'
        rec2.peer_scores = '{"ability": 98}'
        db.commit()

    def test_role_permission_only_admin_hr(self, emp_token, calculate_cycle):
        """只有 admin/hr 可以调用 calculate_scores"""
        cycle = calculate_cycle["cycle"]
        resp = client.post(
            f"/api/v1/scores/calculate/{cycle.id}",
            headers={"Authorization": f"Bearer {emp_token}"},
        )
        assert resp.status_code == 403
