import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import AssessmentRecord, ScoreDraft, User, Employee, AssessmentCycle
from app.database import SessionLocal

client = TestClient(app)


def login(username: str, password: str):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def admin_token():
    return login("admin", "admin123")


@pytest.fixture(scope="module")
def employee_token():
    return login("emp001", "Emp001@123")


@pytest.fixture(scope="module")
def mgr_token():
    return login("mgr001", "Mgr001@123")


@pytest.fixture(scope="function")
def sample_record(db: Session):
    """获取 emp001 的考核记录，并确保 kpi_snapshot 有值"""
    emp_user = db.query(User).filter(User.username == "emp001").first()
    if not emp_user:
        pytest.skip("缺少 emp001 用户")
    rec = db.query(AssessmentRecord).filter(AssessmentRecord.employee_id == emp_user.employee_id).first()
    if not rec:
        pytest.skip("缺少考核记录")
    # 设置 KPI snapshot
    rec.kpi_snapshot = '[{"name": "项目交付率", "weight": 60, "target": "100%"}, {"name": "代码质量", "weight": 40, "target": "95%"}]'
    rec.self_scores = None
    rec.status = "pending_self"
    db.commit()
    db.refresh(rec)
    yield rec


@pytest.fixture(scope="module")
def db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_get_self_assessment_data(employee_token, sample_record, db: Session):
    """员工可以加载自己的自评数据"""
    resp = client.get(
        f"/api/v1/scores/self/{sample_record.id}",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["record_id"] == sample_record.id
    assert data["status"] == sample_record.status
    assert isinstance(data["kpi_items"], list)
    assert len(data["kpi_items"]) == 2
    assert data["kpi_items"][0]["name"] == "项目交付率"
    assert data["self_scores"] == {}
    assert data["draft"] is None
    assert data["has_draft"] is False
    assert data["dimension_weights"] is not None


def test_get_self_assessment_with_draft(employee_token, sample_record, db: Session):
    """已有草稿时返回草稿数据"""
    draft = ScoreDraft(
        record_id=sample_record.id,
        draft_type="self",
        draft_data={"performance": 85, "ability": 90, "attitude": 88},
    )
    db.add(draft)
    db.commit()

    resp = client.get(
        f"/api/v1/scores/self/{sample_record.id}",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["draft"] == {"performance": 85, "ability": 90, "attitude": 88}
    assert data["has_draft"] is True

    # cleanup
    db.delete(draft)
    db.commit()


def test_get_self_assessment_404(employee_token):
    """记录不存在返回 404"""
    resp = client.get(
        "/api/v1/scores/self/999999",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 404
    assert resp.json()["message"] == "考核记录不存在"


def test_get_self_assessment_403(employee_token, admin_token, db: Session):
    """员工不能查看其他员工的记录"""
    admin_user = db.query(User).filter(User.username == "admin").first()
    admin_emp = db.query(Employee).filter(Employee.id == admin_user.employee_id).first()
    rec = db.query(AssessmentRecord).filter(AssessmentRecord.employee_id == admin_emp.id).first()
    if not rec:
        pytest.skip("admin 缺少考核记录")

    resp = client.get(
        f"/api/v1/scores/self/{rec.id}",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["message"] == "无权查看此考核记录"


def test_get_self_assessment_role_restriction(admin_token, sample_record):
    """非 employee 角色不能访问此接口"""
    resp = client.get(
        f"/api/v1/scores/self/{sample_record.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 403
    assert "权限" in resp.json()["message"]


def test_get_self_assessment_not_started_status(employee_token, db: Session):
    """not_started 状态的记录也能加载自评数据"""
    emp_user = db.query(User).filter(User.username == "emp001").first()
    if not emp_user:
        pytest.skip("缺少 emp001 用户")
    rec = db.query(AssessmentRecord).filter(
        AssessmentRecord.employee_id == emp_user.employee_id
    ).first()
    if not rec:
        pytest.skip("缺少考核记录")

    old_status = rec.status
    rec.status = "not_started"
    rec.kpi_snapshot = '[{"name": "测试KPI", "weight": 50, "target": "80%"}]'
    db.commit()
    db.refresh(rec)

    resp = client.get(
        f"/api/v1/scores/self/{rec.id}",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "not_started"
    assert data["kpi_items"] == [{"name": "测试KPI", "weight": 50, "target": "80%"}]

    # restore
    rec.status = old_status
    db.commit()


def test_get_self_assessment_dimension_weights(employee_token, sample_record, db: Session):
    """返回的 dimension_weights 应与周期配置一致"""
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == sample_record.cycle_id).first()
    if cycle and cycle.dimension_weights:
        resp = client.get(
            f"/api/v1/scores/self/{sample_record.id}",
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["dimension_weights"] is not None
    else:
        pytest.skip("周期无 dimension_weights")
