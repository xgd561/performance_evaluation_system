from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import AssessmentRecord, AssessmentCycle, Employee, Department, Position, User, ScoreDetail, AppealRecord
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
def mgr_token():
    return login("mgr001", "Mgr001@123")


@pytest.fixture(scope="module")
def employee_token():
    return login("emp001", "Emp001@123")


@pytest.fixture(scope="module")
def admin_token():
    return login("admin", "admin123")


@pytest.fixture(scope="function")
def manager_record_setup(db: Session):
    """设置经理-下属关系并创建考核记录"""
    mgr = db.query(User).filter(User.username == "mgr001").first()
    emp = db.query(User).filter(User.username == "emp001").first()
    if not mgr or not emp:
        pytest.skip("缺少 mgr001 或 emp001")

    mgr_emp = db.query(Employee).filter(Employee.id == mgr.employee_id).first()
    emp_emp = db.query(Employee).filter(Employee.id == emp.employee_id).first()
    if not mgr_emp or not emp_emp:
        pytest.skip("缺少员工数据")

    old_manager_id = emp_emp.manager_id
    emp_emp.manager_id = mgr_emp.id
    db.commit()

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

    rec = db.query(AssessmentRecord).filter(
        AssessmentRecord.employee_id == emp_emp.id,
        AssessmentRecord.cycle_id == cycle.id
    ).first()
    if not rec:
        rec = AssessmentRecord(
            cycle_id=cycle.id,
            employee_id=emp_emp.id,
            department_id=emp_emp.department_id,
            position_id=emp_emp.position_id,
            status="pending_manager",
            self_scores='{"performance": 80, "ability": 85, "attitude": 90}',
            kpi_snapshot='[{"name": "项目交付率", "weight": 60, "target": "100%"}, {"name": "代码质量", "weight": 40, "target": "95%"}]',
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
    else:
        rec.status = "pending_manager"
        rec.self_scores = '{"performance": 80, "ability": 85, "attitude": 90}'
        rec.kpi_snapshot = '[{"name": "项目交付率", "weight": 60, "target": "100%"}, {"name": "代码质量", "weight": 40, "target": "95%"}]'
        db.commit()
        db.refresh(rec)

    # 确保 ScoreDetail 存在
    details = db.query(ScoreDetail).filter(ScoreDetail.record_id == rec.id).all()
    if not details:
        sd1 = ScoreDetail(record_id=rec.id, kpi_name="项目交付率", weight=60, target_value="100%")
        sd2 = ScoreDetail(record_id=rec.id, kpi_name="代码质量", weight=40, target_value="95%")
        db.add_all([sd1, sd2])
        db.commit()

    yield {
        "record": rec,
        "employee": emp_emp,
        "manager": mgr_emp,
    }

    try:
        db.rollback()
    except Exception:
        pass
    emp_emp.manager_id = old_manager_id
    db.commit()


def test_manager_can_view_detail(mgr_token, manager_record_setup):
    """经理可以查看下属考核详情"""
    rec = manager_record_setup["record"]
    resp = client.get(
        f"/api/v1/scores/records/{rec.id}/detail",
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["record_id"] == rec.id
    assert data["employee_id"] == manager_record_setup["employee"].id
    assert "kpi_details" in data
    assert len(data["kpi_details"]) == 2


def test_manager_cannot_view_other_dept_detail(mgr_token, manager_record_setup, db: Session):
    """经理不能查看非下属/非本部门记录"""
    rec = manager_record_setup["record"]
    # 将记录改为其他部门
    old_dept_id = rec.department_id
    other_dept = db.query(Department).filter(Department.code == "OTHER").first()
    if not other_dept:
        other_dept = Department(name="其他部", code="OTHER")
        db.add(other_dept)
        db.flush()
    rec.department_id = other_dept.id
    db.commit()

    # 同时移除上下级关系
    old_manager_id = manager_record_setup["employee"].manager_id
    manager_record_setup["employee"].manager_id = None
    db.commit()

    resp = client.get(
        f"/api/v1/scores/records/{rec.id}/detail",
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert resp.status_code == 403
    assert "无权" in resp.json()["message"]

    # 恢复
    rec.department_id = old_dept_id
    manager_record_setup["employee"].manager_id = old_manager_id
    db.commit()


def test_detail_404(mgr_token):
    """不存在的记录返回 404"""
    resp = client.get(
        "/api/v1/scores/records/999999/detail",
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert resp.status_code == 404
    assert resp.json()["message"] == "考核记录不存在"


def test_employee_can_view_own_detail(employee_token, manager_record_setup):
    """员工在 pending_manager 状态查看自己的记录，应该被 403"""
    rec = manager_record_setup["record"]
    resp = client.get(
        f"/api/v1/scores/records/{rec.id}/detail",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 403
    assert "尚未发布" in resp.json()["message"]


def test_admin_can_view_any_detail(admin_token, manager_record_setup):
    """admin 可以查看任意考核详情"""
    rec = manager_record_setup["record"]
    resp = client.get(
        f"/api/v1/scores/records/{rec.id}/detail",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["record_id"] == rec.id


def test_employee_can_view_published_detail(employee_token, manager_record_setup, db: Session):
    """员工可以查看已发布状态的考核详情"""
    rec = manager_record_setup["record"]
    old_status = rec.status
    rec.status = "published"
    rec.self_scores = '{"performance": 80, "ability": 85, "attitude": 90}'
    rec.manager_scores = '{"performance": 82, "ability": 86, "attitude": 88}'
    db.commit()
    db.refresh(rec)

    resp = client.get(
        f"/api/v1/scores/records/{rec.id}/detail",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["record_id"] == rec.id
    assert data["self_scores"] == {"performance": 80, "ability": 85, "attitude": 90}
    assert data["manager_scores"] == {"performance": 82, "ability": 86, "attitude": 88}

    # restore
    rec.status = old_status
    db.commit()


def test_detail_contains_kpi_and_appeal_interview(mgr_token, manager_record_setup, db: Session):
    """详情应包含 KPI 明细、申诉、面谈字段"""
    rec = manager_record_setup["record"]
    resp = client.get(
        f"/api/v1/scores/records/{rec.id}/detail",
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "kpi_details" in data
    assert isinstance(data["kpi_details"], list)
    assert "appeal" in data
    assert "interview" in data


def test_detail_with_appeal_record(admin_token, manager_record_setup, db: Session):
    """详情中包含申诉信息"""
    rec = manager_record_setup["record"]
    emp = manager_record_setup["employee"]
    appeal = AppealRecord(
        record_id=rec.id,
        employee_id=emp.id,
        reason="测试申诉",
        detail="申诉详情",
        status="pending",
    )
    db.add(appeal)
    db.commit()

    resp = client.get(
        f"/api/v1/scores/records/{rec.id}/detail",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["appeal"] is not None
    assert data["appeal"]["reason"] == "测试申诉"

    # cleanup
    db.delete(appeal)
    db.commit()


def test_detail_kpi_scores_populated(admin_token, manager_record_setup, db: Session):
    """KPI 明细中包含自评和上级评分"""
    rec = manager_record_setup["record"]
    # 确保 ScoreDetail 有自评和经理评分
    details = db.query(ScoreDetail).filter(ScoreDetail.record_id == rec.id).all()
    for d in details:
        d.self_score = 85
        d.manager_score = 88
    db.commit()

    resp = client.get(
        f"/api/v1/scores/records/{rec.id}/detail",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    for kpi in data["kpi_details"]:
        assert kpi["self_score"] in ("85", "85.00")
        assert kpi["manager_score"] in ("88", "88.00")

    # cleanup
    for d in details:
        d.self_score = None
        d.manager_score = None
    db.commit()
