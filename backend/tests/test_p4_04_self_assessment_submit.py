from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import AssessmentRecord, ScoreDetail, User, Employee
from app.database import SessionLocal
from app.utils.json_columns import load_json

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
def employee_token():
    return login("emp001", "Emp001@123")


@pytest.fixture(scope="module")
def admin_token():
    return login("admin", "admin123")


@pytest.fixture(scope="function")
def sample_record(db: Session):
    """获取 emp001 的 pending_self 记录"""
    emp_user = db.query(User).filter(User.username == "emp001").first()
    if not emp_user:
        pytest.skip("缺少 emp001 用户")
    rec = db.query(AssessmentRecord).filter(
        AssessmentRecord.employee_id == emp_user.employee_id,
        AssessmentRecord.status.in_(["pending_self", "not_started"])
    ).first()
    if not rec:
        # 如果没有 pending_self 记录，创建一条
        from app.models import AssessmentCycle
        cycle = db.query(AssessmentCycle).first()
        if not cycle:
            cycle = AssessmentCycle(name="test-cycle", type="annual", start_date=date(2026, 7, 1), end_date=date(2026, 7, 31))
            db.add(cycle)
            db.flush()
        rec = AssessmentRecord(cycle_id=cycle.id, employee_id=emp_user.employee_id, status="pending_self")
        db.add(rec)
        db.commit()
        db.refresh(rec)
    # 确保状态为 pending_self
    rec.status = "pending_self"
    rec.self_scores = None
    db.commit()
    db.refresh(rec)
    yield rec


def test_submit_self_score_success(employee_token, sample_record, db: Session):
    """员工成功提交自评，状态变为 pending_manager"""
    payload = {
        "performance": 85,
        "ability": 90,
        "attitude": 88,
    }
    resp = client.post(
        f"/api/v1/scores/self/{sample_record.id}",
        json=payload,
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["record_id"] == sample_record.id
    assert data["self_scores"] == payload
    assert data["status"] == "pending_manager"

    # 验证数据库状态
    db.refresh(sample_record)
    assert sample_record.status == "pending_manager"
    self_scores = load_json(sample_record.self_scores, {})
    assert self_scores["performance"] == 85
    assert self_scores["ability"] == 90
    assert self_scores["attitude"] == 88

    # 恢复状态供后续测试
    sample_record.status = "pending_self"
    sample_record.self_scores = None
    db.commit()


def test_submit_self_score_with_kpi(employee_token, sample_record, db: Session):
    """提交自评时携带 KPI 分数"""
    # 先设置 KPI snapshot
    sample_record.kpi_snapshot = '[{"name": "项目交付率", "weight": 60, "target": "100%"}, {"name": "代码质量", "weight": 40, "target": "95%"}]'
    db.commit()
    db.refresh(sample_record)

    payload = {
        "performance": 80,
        "ability": 85,
        "attitude": 90,
        "kpi_scores": [85, 90],
    }
    resp = client.post(
        f"/api/v1/scores/self/{sample_record.id}",
        json=payload,
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 200

    # 验证 ScoreDetail 记录
    details = db.query(ScoreDetail).filter(ScoreDetail.record_id == sample_record.id).all()
    assert len(details) == 2
    assert float(details[0].self_score) == 85
    assert float(details[1].self_score) == 90

    # 清理
    for d in details:
        db.delete(d)
    sample_record.status = "pending_self"
    sample_record.self_scores = None
    sample_record.kpi_snapshot = None
    db.commit()


def test_submit_self_score_403_other_employee(employee_token, admin_token, sample_record, db: Session):
    """员工不能为其他员工提交自评"""
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        pytest.skip("缺少 admin 用户")

    # 确保记录不属于 emp001
    if sample_record.employee_id == admin_user.employee_id:
        # 找一个 emp001 的记录
        emp_user = db.query(User).filter(User.username == "emp001").first()
        sample_record.employee_id = emp_user.employee_id
        db.commit()
    else:
        # 将记录改为 admin 的
        sample_record.employee_id = admin_user.employee_id
        db.commit()
    sample_record.status = "pending_self"
    db.commit()

    resp = client.post(
        f"/api/v1/scores/self/{sample_record.id}",
        json={"performance": 80, "ability": 80, "attitude": 80},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["message"] == "无权操作此考核记录"

    # 恢复
    emp_user = db.query(User).filter(User.username == "emp001").first()
    sample_record.employee_id = emp_user.employee_id
    db.commit()


def test_submit_self_score_422_invalid_status(employee_token, sample_record, db: Session):
    """非 pending_self 状态不允许提交自评"""
    sample_record.status = "pending_manager"
    db.commit()

    resp = client.post(
        f"/api/v1/scores/self/{sample_record.id}",
        json={"performance": 80, "ability": 80, "attitude": 80},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 422
    assert resp.json()["message"] == "当前状态不允许提交自评"

    # 恢复
    sample_record.status = "pending_self"
    db.commit()


def test_submit_self_score_422_invalid_scores(employee_token, sample_record):
    """分数超出 0-100 范围应返回 422"""
    for bad_score in [-1, 101, 150]:
        resp = client.post(
            f"/api/v1/scores/self/{sample_record.id}",
            json={"performance": bad_score, "ability": 80, "attitude": 80},
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 422, f"score={bad_score} should fail"
        assert "分数需在0-100之间" in resp.json()["message"]


def test_submit_self_score_404(employee_token):
    """不存在的记录返回 404"""
    resp = client.post(
        "/api/v1/scores/self/999999",
        json={"performance": 80, "ability": 80, "attitude": 80},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 404
    assert resp.json()["message"] == "考核记录不存在"


def test_role_restriction(admin_token, sample_record):
    """非 employee 角色不能访问此接口"""
    resp = client.post(
        f"/api/v1/scores/self/{sample_record.id}",
        json={"performance": 80, "ability": 80, "attitude": 80},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 403


def test_submit_self_score_from_not_started(employee_token, sample_record, db: Session):
    """not_started 状态不能直接提交自评，会返回 400/422"""
    sample_record.status = "not_started"
    sample_record.self_scores = None
    db.commit()
    db.refresh(sample_record)

    payload = {"performance": 70, "ability": 75, "attitude": 80}
    resp = client.post(
        f"/api/v1/scores/self/{sample_record.id}",
        json=payload,
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    # 状态机不允许 not_started -> submit_self，状态校验直接返回 422
    assert resp.status_code == 422

    # restore
    sample_record.status = "pending_self"
    sample_record.self_scores = None
    db.commit()


def test_submit_self_score_boundary_values(employee_token, sample_record, db: Session):
    """边界值 0 和 100 应被接受"""
    for boundary in [0, 100]:
        db.expire_all()
        rec = db.query(AssessmentRecord).filter(AssessmentRecord.id == sample_record.id).first()
        rec.status = "pending_self"
        rec.self_scores = None
        db.commit()
        db.refresh(rec)

        payload = {"performance": boundary, "ability": boundary, "attitude": boundary}
        resp = client.post(
            f"/api/v1/scores/self/{rec.id}",
            json=payload,
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 200, f"boundary={boundary} should pass"

    # final restore
    db.expire_all()
    rec = db.query(AssessmentRecord).filter(AssessmentRecord.id == sample_record.id).first()
    rec.status = "pending_self"
    rec.self_scores = None
    db.commit()


def test_submit_self_score_missing_dimension(employee_token, sample_record):
    """缺少维度字段应返回 422"""
    resp = client.post(
        f"/api/v1/scores/self/{sample_record.id}",
        json={"performance": 80, "ability": 80},  # missing attitude
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 422
