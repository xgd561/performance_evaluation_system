import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.database import get_db, SessionLocal
from app.models import Department, Position, Employee, User
from app.auth import get_password_hash

client = TestClient(app)


# --- DB override for integration tests ---
@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def api_client(db_session):
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def admin_token(api_client):
    res = api_client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    return res.json()["access_token"]


class TestEmployeeOrganizationIntegration:
    """
    集成测试：创建部门 -> 创建岗位 -> 创建经理 -> 创建员工（指定上级）
    -> 查询员工详情（含上级）-> 查询上级下属列表 -> 导入员工 Excel
    """

    def test_full_organization_workflow(self, api_client, admin_token, db_session):
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Step 1: 创建部门
        dept_res = api_client.post("/api/departments", headers=headers, json={
            "code": "INT-DEPT", "name": "集成测试部"
        })
        assert dept_res.status_code == 201
        dept = dept_res.json()
        dept_id = dept["id"]

        # Step 2: 创建岗位
        pos_res = api_client.post("/api/positions", headers=headers, json={
            "name": "集成工程师", "level": "P5", "department_id": dept_id
        })
        assert pos_res.status_code == 201
        pos = pos_res.json()
        pos_id = pos["id"]

        # Step 3: 创建经理
        mgr_res = api_client.post("/api/employees", headers=headers, json={
            "employee_no": "INT-MGR-001",
            "name": "集成经理",
            "department_id": dept_id,
            "position_id": pos_id,
            "email": "int-mgr@example.com",
            "phone": "13800001111"
        })
        assert mgr_res.status_code == 201
        mgr = mgr_res.json()
        mgr_id = mgr["id"]

        # Step 4: 创建员工（指定上级）
        emp_res = api_client.post("/api/employees", headers=headers, json={
            "employee_no": "INT-EMP-001",
            "name": "集成员工",
            "department_id": dept_id,
            "position_id": pos_id,
            "manager_id": mgr_id,
            "email": "int-emp@example.com",
            "phone": "13800002222"
        })
        assert emp_res.status_code == 201
        emp = emp_res.json()
        emp_id = emp["id"]
        assert emp["manager_id"] == mgr_id

        # Step 5: 查询员工详情（含上级）
        detail_res = api_client.get(f"/api/employees/{emp_id}", headers=headers)
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["manager_id"] == mgr_id
        assert detail["department_id"] == dept_id
        assert detail["position_id"] == pos_id

        # Step 6: 查询上级下属列表
        sub_res = api_client.get(f"/api/employees/{mgr_id}/subordinates", headers=headers)
        assert sub_res.status_code == 200
        subs = sub_res.json()
        assert any(s["id"] == emp_id for s in subs)

        # Step 7: 查询员工列表包含新创建记录
        list_res = api_client.get("/api/employees?page=1&size=100", headers=headers)
        assert list_res.status_code == 200
        items = list_res.json()["items"]
        assert any(e["employee_no"] == "INT-EMP-001" for e in items)
        assert any(e["employee_no"] == "INT-MGR-001" for e in items)

        # Step 8: 软删除员工
        del_res = api_client.delete(f"/api/employees/{emp_id}", headers=headers)
        assert del_res.status_code == 200
        # 查询列表应显示 is_active=false
        list2 = api_client.get("/api/employees?page=1&size=100", headers=headers).json()["items"]
        deleted = next((e for e in list2 if e["employee_no"] == "INT-EMP-001"), None)
        assert deleted is not None
        assert deleted["is_active"] is False

        # Step 9: 删除岗位（有员工时应失败）
        # 经理还在，所以删除岗位应该失败
        pos_del = api_client.delete(f"/api/positions/{pos_id}", headers=headers)
        assert pos_del.status_code == 409

        # Step 10: 删除部门（有员工时应失败）
        dept_del = api_client.delete(f"/api/departments/{dept_id}", headers=headers)
        assert dept_del.status_code == 400

        # 清理：先删除经理，再删除岗位，再删除部门
        api_client.delete(f"/api/employees/{mgr_id}", headers=headers)
        api_client.delete(f"/api/positions/{pos_id}", headers=headers)
        api_client.delete(f"/api/departments/{dept_id}", headers=headers)

    def test_department_tree_query(self, api_client, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        tree_res = api_client.get("/api/departments?tree=true", headers=headers)
        assert tree_res.status_code == 200
        tree = tree_res.json()
        assert isinstance(tree, list)
        # 根节点为 parent_id=null 的部门
        if tree:
            assert "children" in tree[0]
