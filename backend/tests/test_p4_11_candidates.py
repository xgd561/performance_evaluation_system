import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import Employee, Department, Position, User
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
def ensure_candidates(db: Session):
    """确保数据库中存在至少2个部门、多个员工，用于候选协作人查询"""
    dept_a = db.query(Department).filter(Department.name == "Test Dept A").first()
    if not dept_a:
        dept_a = Department(name="Test Dept A", code="TDA")
        db.add(dept_a)
        db.flush()

    dept_b = db.query(Department).filter(Department.name == "Test Dept B").first()
    if not dept_b:
        dept_b = Department(name="Test Dept B", code="TDB")
        db.add(dept_b)
        db.flush()

    pos = db.query(Position).filter(Position.name == "Test Position").first()
    if not pos:
        pos = Position(name="Test Position")
        db.add(pos)
        db.flush()

    # 创建员工 A（部门 A）
    emp_a = db.query(Employee).filter(Employee.employee_no == "CANDA001").first()
    if not emp_a:
        emp_a = Employee(
            name="张三",
            employee_no="CANDA001",
            department_id=dept_a.id,
            position_id=pos.id,
            is_active=True,
        )
        db.add(emp_a)
        db.flush()
    else:
        emp_a.is_active = True
        db.flush()

    # 创建员工 B（部门 B）
    emp_b = db.query(Employee).filter(Employee.employee_no == "CANDB001").first()
    if not emp_b:
        emp_b = Employee(
            name="李四",
            employee_no="CANDB001",
            department_id=dept_b.id,
            position_id=pos.id,
            is_active=True,
        )
        db.add(emp_b)
        db.flush()
    else:
        emp_b.is_active = True
        db.flush()

    # 创建员工 C（部门 A，非在职）
    emp_c = db.query(Employee).filter(Employee.employee_no == "CANDC001").first()
    if not emp_c:
        emp_c = Employee(
            name="王五",
            employee_no="CANDC001",
            department_id=dept_a.id,
            position_id=pos.id,
            is_active=False,
        )
        db.add(emp_c)
        db.flush()

    db.commit()

    yield {
        "dept_a": dept_a,
        "dept_b": dept_b,
        "emp_a": emp_a,
        "emp_b": emp_b,
        "emp_c": emp_c,
    }

    # teardown: 软删除测试数据
    for emp in [emp_a, emp_b, emp_c]:
        emp.is_active = False
    db.commit()


class TestP4_11Candidates:
    """P4-11: 候选协作人查询接口测试"""

    def test_candidates_success_admin(self, admin_token, ensure_candidates):
        """admin 可成功查询候选协作人"""
        resp = client.get(
            "/api/v1/employees/candidates",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        emp_nos = [item["employee_no"] for item in data]
        assert "CANDA001" in emp_nos
        assert "CANDB001" in emp_nos
        assert "CANDC001" not in emp_nos

    def test_candidates_success_hr(self, hr_token, ensure_candidates):
        """hr 可成功查询候选协作人"""
        resp = client.get(
            "/api/v1/employees/candidates",
            headers={"Authorization": f"Bearer {hr_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_candidates_success_manager(self, mgr_token, ensure_candidates):
        """manager 可成功查询候选协作人"""
        resp = client.get(
            "/api/v1/employees/candidates",
            headers={"Authorization": f"Bearer {mgr_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_candidates_exclude_id(self, admin_token, ensure_candidates):
        """exclude_id 排除指定员工，并优先返回其他部门员工"""
        emp_a = ensure_candidates["emp_a"]
        emp_b = ensure_candidates["emp_b"]
        resp = client.get(
            f"/api/v1/employees/candidates?exclude_id={emp_a.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        ids = [item["id"] for item in data]
        assert emp_a.id not in ids
        assert emp_b.id in ids

    def test_candidates_keyword_by_name(self, admin_token, ensure_candidates):
        """keyword 按姓名模糊查询"""
        resp = client.get(
            "/api/v1/employees/candidates?keyword=张三",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any(item["name"] == "张三" for item in data)

    def test_candidates_keyword_by_employee_no(self, admin_token, ensure_candidates):
        """keyword 按工号模糊查询"""
        resp = client.get(
            "/api/v1/employees/candidates?keyword=CANDB",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any(item["employee_no"] == "CANDB001" for item in data)

    def test_candidates_empty_result(self, admin_token, ensure_candidates):
        """keyword 无匹配时返回空列表"""
        resp = client.get(
            "/api/v1/employees/candidates?keyword=不存在的名字",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data == []

    def test_candidates_forbidden_employee(self, emp_token, ensure_candidates):
        """普通员工角色无权访问候选协作人接口"""
        resp = client.get(
            "/api/v1/employees/candidates",
            headers={"Authorization": f"Bearer {emp_token}"},
        )
        assert resp.status_code == 403
        assert "权限" in resp.json()["message"]

    def test_candidates_response_fields(self, admin_token, ensure_candidates):
        """返回结果包含预期的字段"""
        resp = client.get(
            "/api/v1/employees/candidates",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        item = data[0]
        assert "id" in item
        assert "name" in item
        assert "employee_no" in item
        assert "department_id" in item
        assert "department_name" in item
        assert "position_id" in item
        assert "position_name" in item
