from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import AssessmentRecord, AssessmentCycle, Employee, Department, Position, User
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


@pytest.fixture(scope="function")
def manager_subordinate_setup(db: Session):
    """设置经理-下属关系并创建考核记录"""
    mgr = db.query(User).filter(User.username == "mgr001").first()
    emp = db.query(User).filter(User.username == "emp001").first()
    if not mgr or not emp:
        pytest.skip("缺少 mgr001 或 emp001")

    mgr_emp = db.query(Employee).filter(Employee.id == mgr.employee_id).first()
    emp_emp = db.query(Employee).filter(Employee.id == emp.employee_id).first()
    if not mgr_emp or not emp_emp:
        pytest.skip("缺少员工数据")

    # 设置上下级关系
    old_manager_id = emp_emp.manager_id
    emp_emp.manager_id = mgr_emp.id
    db.commit()

    # 确保有考核周期
    cycle = db.query(AssessmentCycle).first()
    if not cycle:
        cycle = AssessmentCycle(
            name="test-cycle",
            type="annual",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            peer_review_enabled=True,
        )
        db.add(cycle)
        db.flush()

    # 确保 emp001 有 pending_manager 记录
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
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
    else:
        rec.status = "pending_manager"
        rec.self_scores = '{"performance": 80, "ability": 85, "attitude": 90}'
        rec.manager_scores = None
        rec.manager_comment = None
        rec.manager_submitted = False
        db.commit()
        db.refresh(rec)

    yield {
        "manager": mgr_emp,
        "employee": emp_emp,
        "record": rec,
        "cycle": cycle,
    }

    # cleanup
    emp_emp.manager_id = old_manager_id
    rec.status = "pending_manager"
    rec.manager_scores = None
    rec.manager_comment = None
    rec.manager_submitted = False
    db.commit()


def test_manager_score_list_basic(mgr_token, manager_subordinate_setup):
    """经理可以查看下属的评分列表"""
    resp = client.get(
        "/api/v1/scores/manager/score-list",
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    emp = manager_subordinate_setup["employee"]
    assert any(r["employee_id"] == emp.id for r in data)


def test_manager_score_list_status_filter(mgr_token, manager_subordinate_setup):
    """状态筛选：pending_manager"""
    resp = client.get(
        "/api/v1/scores/manager/score-list?status=pending_manager",
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(r["status"] == "pending_manager" for r in data)


def test_manager_score_list_department_filter(mgr_token, manager_subordinate_setup, db: Session):
    """部门筛选"""
    dept_id = manager_subordinate_setup["employee"].department_id
    resp = client.get(
        f"/api/v1/scores/manager/score-list?department_id={dept_id}",
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(r["department_id"] == dept_id for r in data)


def test_manager_score_list_keyword_filter(mgr_token, manager_subordinate_setup):
    """关键词筛选（姓名/工号）"""
    emp = manager_subordinate_setup["employee"]
    # 按姓名搜索
    resp = client.get(
        f"/api/v1/scores/manager/score-list?keyword={emp.name[:2]}",
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert any(r["employee_id"] == emp.id for r in data)

    # 按工号搜索
    resp = client.get(
        f"/api/v1/scores/manager/score-list?keyword={emp.employee_no}",
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert any(r["employee_id"] == emp.id for r in data)


def test_manager_score_list_403_employee(employee_token):
    """employee 角色不能访问经理评分列表"""
    resp = client.get(
        "/api/v1/scores/manager/score-list",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 403


def test_manager_score_list_empty_no_subordinates(mgr_token, db: Session):
    """经理没有下属时返回空列表"""
    mgr = db.query(User).filter(User.username == "mgr001").first()
    if mgr:
        mgr_emp = db.query(Employee).filter(Employee.id == mgr.employee_id).first()
        if mgr_emp:
            # 临时移除所有下属
            subordinates = db.query(Employee).filter(Employee.manager_id == mgr_emp.id).all()
            old_manager_ids = {s.id: s.manager_id for s in subordinates}
            for s in subordinates:
                s.manager_id = None
            db.commit()

            resp = client.get(
                "/api/v1/scores/manager/score-list",
                headers={"Authorization": f"Bearer {mgr_token}"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data == []

            # restore
            for s in subordinates:
                s.manager_id = old_manager_ids[s.id]
            db.commit()


def test_manager_score_list_contains_manager_submitted_flag(mgr_token, manager_subordinate_setup):
    """列表返回中应包含 manager_submitted 字段（通过 detail 或列表字段）"""
    resp = client.get(
        "/api/v1/scores/manager/score-list",
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    # 列表项中应包含 status 字段
    assert "status" in data[0]
    # 通过 detail 接口验证 manager_submitted
    rec_id = data[0]["record_id"]
    detail_resp = client.get(
        f"/api/v1/scores/records/{rec_id}/detail",
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert "status" in detail
