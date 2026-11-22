from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import AssessmentRecord, ScoreDraft, User
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
def employee_token():
    return login("emp001", "Emp001@123")


@pytest.fixture(scope="module")
def mgr_token():
    return login("mgr001", "Mgr001@123")


@pytest.fixture(scope="function")
def sample_record(db: Session):
    """确保至少有一条 assessment record 可供测试"""
    rec = db.query(AssessmentRecord).first()
    if not rec:
        from app.models import AssessmentCycle, Employee
        cycle = db.query(AssessmentCycle).first()
        if not cycle:
            cycle = AssessmentCycle(
                name="test-cycle",
                type="annual",
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 31),
            )
            db.add(cycle)
            db.flush()
        emp = db.query(Employee).filter(Employee.employee_no == "WANG001").first()
        if not emp:
            emp = Employee(employee_no="WANG001", name="王员工")
            db.add(emp)
            db.flush()
        rec = AssessmentRecord(cycle_id=cycle.id, employee_id=emp.id, status="pending_self")
        db.add(rec)
        db.commit()
        db.refresh(rec)
    yield rec


def test_create_score_draft(admin_token, sample_record):
    payload = {
        "record_id": sample_record.id,
        "draft_type": "self",
        "draft_data": {"performance": 85, "ability": 90},
    }
    resp = client.post(
        "/api/v1/score-drafts",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["record_id"] == sample_record.id
    assert data["draft_type"] == "self"
    assert data["draft_data"] == payload["draft_data"]
    assert "id" in data


def test_upsert_score_draft(admin_token, sample_record):
    """同一 (record_id, draft_type) 仅保留最新记录"""
    payload = {
        "record_id": sample_record.id,
        "draft_type": "self",
        "draft_data": {"performance": 95, "attitude": 80},
    }
    resp1 = client.post(
        "/api/v1/score-drafts",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp1.status_code == 200
    first_id = resp1.json()["id"]

    resp2 = client.post(
        "/api/v1/score-drafts",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp2.status_code == 200
    second = resp2.json()
    assert second["id"] == first_id  # id 不变，说明是更新
    assert second["draft_data"] == payload["draft_data"]
    assert second["updated_at"] != second["created_at"] or second["updated_at"] >= second["created_at"]


def test_get_score_draft(admin_token, sample_record):
    resp = client.get(
        f"/api/v1/score-drafts/{sample_record.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(d["record_id"] == sample_record.id for d in data)


def test_get_score_draft_by_type(admin_token, sample_record):
    resp = client.get(
        f"/api/v1/score-drafts/{sample_record.id}?draft_type=self",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["draft_type"] == "self"


def test_create_score_draft_404(admin_token):
    payload = {
        "record_id": 999999,
        "draft_type": "self",
        "draft_data": {"a": 1},
    }
    resp = client.post(
        "/api/v1/score-drafts",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404
    assert resp.json()["message"] == "考核记录不存在"


def test_get_score_draft_404(admin_token):
    resp = client.get(
        "/api/v1/score-drafts/999999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404
    assert resp.json()["message"] == "考核记录不存在"


def test_employee_can_access_own_record(employee_token, sample_record, db: Session):
    """员工可以访问自己的考核记录"""
    emp_user = db.query(User).filter(User.username == "emp001").first()
    if emp_user and sample_record.employee_id != emp_user.employee_id:
        # 将 sample_record 绑定到 emp001
        sample_record.employee_id = emp_user.employee_id
        db.commit()

    resp = client.get(
        f"/api/v1/score-drafts/{sample_record.id}",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 200


def test_employee_cannot_access_others_record(employee_token, admin_token, sample_record, db: Session):
    """员工不能访问其他员工的考核记录"""
    emp_user = db.query(User).filter(User.username == "emp001").first()
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not emp_user or not admin_user:
        pytest.skip("缺少用户数据")

    # 确保 record 不属于 emp001
    if sample_record.employee_id == emp_user.employee_id:
        sample_record.employee_id = admin_user.employee_id
        db.commit()

    resp = client.get(
        f"/api/v1/score-drafts/{sample_record.id}",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["message"] == "无权查看此考核记录"
