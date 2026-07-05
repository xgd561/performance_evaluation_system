import pytest
import io
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import Department, Position, Employee, User
from app.auth import get_password_hash


@pytest.fixture(scope="function")
def integration_admin(db_session: Session):
    """Create admin user for integration tests."""
    dept = Department(name="管理部", code="ADMIN")
    db_session.add(dept)
    db_session.flush()
    pos = Position(name="系统管理员", department_id=dept.id)
    db_session.add(pos)
    db_session.flush()
    emp = Employee(employee_no="ADMIN001", name="系统管理员", department_id=dept.id, position_id=pos.id)
    db_session.add(emp)
    db_session.flush()
    user = User(
        username="admin",
        password_hash=get_password_hash("admin123"),
        role="admin",
        employee_id=emp.id,
        is_first_login=False,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture(scope="function")
def integration_admin_token(client: TestClient, integration_admin):
    resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


class TestEmployeeIntegrationChain:
    """P2-13: Full integration chain — dept → position → manager → employee → query → subordinates → import → verify."""

    def test_full_chain(self, client: TestClient, integration_admin_token: str, db_session: Session):
        token = integration_admin_token
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create department
        dept_resp = client.post("/departments", json={"name": "研发部", "code": "RD"}, headers=headers)
        assert dept_resp.status_code == 201
        dept = dept_resp.json()
        assert dept["name"] == "研发部"
        dept_id = dept["id"]

        # 2. Create position
        pos_resp = client.post("/positions", json={"name": "高级工程师", "department_id": dept_id}, headers=headers)
        assert pos_resp.status_code == 201
        pos = pos_resp.json()
        assert pos["name"] == "高级工程师"
        pos_id = pos["id"]

        # 3. Create manager employee
        mgr_resp = client.post("/employees", json={
            "employee_no": "M001",
            "name": "李建国",
            "department_id": dept_id,
            "position_id": pos_id,
            "is_active": True,
        }, headers=headers)
        assert mgr_resp.status_code == 201
        mgr = mgr_resp.json()
        assert mgr["name"] == "李建国"
        mgr_id = mgr["id"]

        # 4. Create subordinate employee
        emp_resp = client.post("/employees", json={
            "employee_no": "E001",
            "name": "王志强",
            "department_id": dept_id,
            "position_id": pos_id,
            "manager_id": mgr_id,
            "is_active": True,
        }, headers=headers)
        assert emp_resp.status_code == 201
        emp = emp_resp.json()
        assert emp["name"] == "王志强"
        assert emp["manager_id"] == mgr_id
        emp_id = emp["id"]

        # 5. Query employee details
        detail_resp = client.get(f"/employees/{emp_id}", headers=headers)
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["employee_no"] == "E001"
        assert detail["name"] == "王志强"
        assert detail["department_name"] == "研发部"
        assert detail["position_name"] == "高级工程师"
        assert detail["manager_name"] == "李建国"

        # 6. Query subordinates
        sub_resp = client.get(f"/employees/{mgr_id}/subordinates", headers=headers)
        assert sub_resp.status_code == 200
        subs = sub_resp.json()
        assert len(subs) == 1
        assert subs[0]["name"] == "王志强"
        assert subs[0]["employee_no"] == "E001"

        # 7. Import Excel with new employees
        try:
            from openpyxl import Workbook
        except ImportError:
            pytest.skip("openpyxl not installed")

        wb = Workbook()
        ws = wb.active
        ws.append(["工号", "姓名", "部门", "岗位", "直属上级工号", "是否部门负责人", "入职日期", "状态"])
        ws.append(["I001", "导入员工", "研发部", "高级工程师", "M001", "否", "2024-01-01", "在职"])
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        import_resp = client.post(
            "/employees/import",
            files={"file": ("import.xlsx", buffer, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=headers,
        )
        assert import_resp.status_code == 200
        import_result = import_resp.json()
        assert import_result["success"] >= 1
        assert import_result["failed"] == 0

        # 8. Verify imported employee
        list_resp = client.get("/employees", params={"keyword": "导入员工"}, headers=headers)
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["total"] >= 1
        items = list_data["items"]
        imported = [x for x in items if x["employee_no"] == "I001"]
        assert len(imported) == 1
        assert imported[0]["name"] == "导入员工"
        assert imported[0]["department_name"] == "研发部"
        assert imported[0]["manager_name"] == "李建国"

    def test_import_preview(self, client: TestClient, integration_admin_token: str):
        token = integration_admin_token
        headers = {"Authorization": f"Bearer {token}"}
        try:
            from openpyxl import Workbook
        except ImportError:
            pytest.skip("openpyxl not installed")

        wb = Workbook()
        ws = wb.active
        ws.append(["工号", "姓名", "部门", "岗位", "直属上级工号", "是否部门负责人", "入职日期", "状态"])
        ws.append(["P001", "预览员工", "研发部", "工程师", "", "否", "2024-01-01", "在职"])
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        preview_resp = client.post(
            "/employees/import-preview",
            files={"file": ("preview.xlsx", buffer, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=headers,
        )
        assert preview_resp.status_code == 200
        preview = preview_resp.json()
        assert preview["total"] >= 1

    def test_import_status(self, client: TestClient, integration_admin_token: str):
        token = integration_admin_token
        headers = {"Authorization": f"Bearer {token}"}
        status_resp = client.get("/employees/import/status", headers=headers)
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["status"] == "ready"
        assert data["progress"] == 100

    def test_department_delete_blocked_by_employees(self, client: TestClient, integration_admin_token: str, db_session: Session):
        token = integration_admin_token
        headers = {"Authorization": f"Bearer {token}"}

        # Create a new department and employee
        dept_resp = client.post("/departments", json={"name": "临时部", "code": "TMP"}, headers=headers)
        assert dept_resp.status_code == 201
        dept_id = dept_resp.json()["id"]

        pos_resp = client.post("/positions", json={"name": "临时工", "department_id": dept_id}, headers=headers)
        pos_id = pos_resp.json()["id"]

        emp_resp = client.post("/employees", json={
            "employee_no": "TMP001",
            "name": "临时员工",
            "department_id": dept_id,
            "position_id": pos_id,
        }, headers=headers)
        assert emp_resp.status_code == 201

        # Try to delete department — should fail because employees exist
        del_resp = client.delete(f"/departments/{dept_id}", headers=headers)
        assert del_resp.status_code == 400
        assert "员工" in del_resp.json()["message"]

    def test_position_delete_blocked_by_employees(self, client: TestClient, integration_admin_token: str, db_session: Session):
        token = integration_admin_token
        headers = {"Authorization": f"Bearer {token}"}

        # Create a new department and position
        dept_resp = client.post("/departments", json={"name": "测试部", "code": "TST"}, headers=headers)
        dept_id = dept_resp.json()["id"]

        pos_resp = client.post("/positions", json={"name": "测试岗", "department_id": dept_id}, headers=headers)
        pos_id = pos_resp.json()["id"]

        client.post("/employees", json={
            "employee_no": "TST001",
            "name": "测试员工",
            "department_id": dept_id,
            "position_id": pos_id,
        }, headers=headers)

        # Try to delete position — should fail because employees exist
        del_resp = client.delete(f"/positions/{pos_id}", headers=headers)
        assert del_resp.status_code == 409
        assert "员工" in del_resp.json()["message"]

    def test_manager_employee_no_resolution(self, client: TestClient, integration_admin_token: str, db_session: Session):
        token = integration_admin_token
        headers = {"Authorization": f"Bearer {token}"}

        dept_resp = client.post("/departments", json={"name": "经理部", "code": "MGR"}, headers=headers)
        dept_id = dept_resp.json()["id"]

        pos_resp = client.post("/positions", json={"name": "经理岗", "department_id": dept_id}, headers=headers)
        pos_id = pos_resp.json()["id"]

        mgr_resp = client.post("/employees", json={
            "employee_no": "MGR01",
            "name": "张经理",
            "department_id": dept_id,
            "position_id": pos_id,
        }, headers=headers)
        mgr_id = mgr_resp.json()["id"]

        # Create employee using manager_employee_no instead of manager_id
        emp_resp = client.post("/employees", json={
            "employee_no": "SUB01",
            "name": "李下属",
            "department_id": dept_id,
            "position_id": pos_id,
            "manager_employee_no": "MGR01",
        }, headers=headers)
        assert emp_resp.status_code == 201
        emp = emp_resp.json()
        assert emp["manager_id"] == mgr_id
        assert emp["manager_name"] == "张经理"

    def test_update_employee_manager(self, client: TestClient, integration_admin_token: str, db_session: Session):
        token = integration_admin_token
        headers = {"Authorization": f"Bearer {token}"}

        dept_resp = client.post("/departments", json={"name": "更新部", "code": "UPD"}, headers=headers)
        dept_id = dept_resp.json()["id"]
        pos_resp = client.post("/positions", json={"name": "更新岗", "department_id": dept_id}, headers=headers)
        pos_id = pos_resp.json()["id"]

        mgr1 = client.post("/employees", json={
            "employee_no": "UPDM1",
            "name": "原经理",
            "department_id": dept_id,
            "position_id": pos_id,
        }, headers=headers).json()
        mgr2 = client.post("/employees", json={
            "employee_no": "UPDM2",
            "name": "新经理",
            "department_id": dept_id,
            "position_id": pos_id,
        }, headers=headers).json()
        emp = client.post("/employees", json={
            "employee_no": "UPDE1",
            "name": "被调员工",
            "department_id": dept_id,
            "position_id": pos_id,
            "manager_id": mgr1["id"],
        }, headers=headers).json()

        # Update manager to mgr2 via manager_employee_no
        update_resp = client.put(f"/employees/{emp['id']}", json={
            "manager_employee_no": "UPDM2",
        }, headers=headers)
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["manager_id"] == mgr2["id"]
        assert updated["manager_name"] == "新经理"

    def test_employee_list_with_department_filter(self, client: TestClient, integration_admin_token: str, db_session: Session):
        token = integration_admin_token
        headers = {"Authorization": f"Bearer {token}"}

        d1 = client.post("/departments", json={"name": "A部", "code": "A"}, headers=headers).json()
        p1 = client.post("/positions", json={"name": "A岗", "department_id": d1["id"]}, headers=headers).json()
        client.post("/employees", json={"employee_no": "A001", "name": "A员工", "department_id": d1["id"], "position_id": p1["id"]}, headers=headers)

        d2 = client.post("/departments", json={"name": "B部", "code": "B"}, headers=headers).json()
        p2 = client.post("/positions", json={"name": "B岗", "department_id": d2["id"]}, headers=headers).json()
        client.post("/employees", json={"employee_no": "B001", "name": "B员工", "department_id": d2["id"], "position_id": p2["id"]}, headers=headers)

        list_resp = client.get("/employees", params={"department_id": d1["id"]}, headers=headers)
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "A员工"
