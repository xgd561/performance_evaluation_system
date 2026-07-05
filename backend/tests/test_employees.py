import pytest
from fastapi.testclient import TestClient
from io import BytesIO
from app.models import Employee, Department, Position, AssessmentRecord


class TestEmployeeList:
    """Tests for GET /employees"""

    def test_list_employees_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="列表部", code="LIST")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="列表岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        mgr = Employee(employee_no="LISTM01", name="列表上级", department_id=dept.id, position_id=pos.id)
        db_session.add(mgr)
        db_session.flush()
        emp = Employee(employee_no="LIST001", name="列表员工", department_id=dept.id, position_id=pos.id, manager_id=mgr.id)
        db_session.add(emp)
        db_session.commit()

        resp = client.get("/employees", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "items" in data
        assert data["page"] == 1
        # Strict assertions for enriched fields (the bug you found)
        item = next((i for i in data["items"] if i["employee_no"] == "LIST001"), None)
        assert item is not None, "员工必须在列表中"
        assert item["department_name"] == "列表部", f"部门名称缺失或错误: {item.get('department_name')}"
        assert item["position_name"] == "列表岗", f"岗位名称缺失或错误: {item.get('position_name')}"
        assert item["manager_name"] == "列表上级", f"上级名称缺失或错误: {item.get('manager_name')}"
        assert item["manager_employee_no"] == "LISTM01", f"上级工号缺失或错误: {item.get('manager_employee_no')}"
        assert "department_id" in item
        assert "position_id" in item
        assert "manager_id" in item
        assert "is_active" in item
        assert "created_at" in item

    def test_list_employees_pagination(self, client: TestClient, admin_token, db_session):
        # Create multiple employees
        dept = Department(name="测试部", code="TEST")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        for i in range(5):
            emp = Employee(employee_no=f"EMP{i:03d}", name=f"员工{i}", department_id=dept.id, position_id=pos.id)
            db_session.add(emp)
        db_session.commit()

        resp = client.get("/employees?page=1&size=2", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] >= 5
        assert data["page"] == 1
        assert data["size"] == 2
        assert "employee_no" in data["items"][0]
        assert "name" in data["items"][0]
        assert "department_name" in data["items"][0]

    def test_list_employees_keyword_filter(self, client: TestClient, admin_token, db_session):
        dept = Department(name="测试部", code="TEST")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="SEARCH001", name="搜索测试", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.commit()

        resp = client.get("/employees?keyword=搜索", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert any(item["name"] == "搜索测试" for item in data["items"])
        assert all("department_name" in item for item in data["items"])

    def test_list_employees_by_department(self, client: TestClient, admin_token, db_session):
        dept = Department(name="筛选部", code="FILTER")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="筛选岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="FILTER001", name="筛选员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.commit()

        resp = client.get(f"/employees?department_id={dept.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert all(item["department_id"] == dept.id for item in data["items"])

    def test_list_employees_by_employee_no(self, client: TestClient, admin_token, db_session):
        dept = Department(name="测试部", code="TEST")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="UNIQUE001", name="唯一员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.commit()

        resp = client.get("/employees?employee_no=UNIQUE001", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["employee_no"] == "UNIQUE001"

    def test_list_employees_no_auth(self, client: TestClient):
        resp = client.get("/employees")
        assert resp.status_code == 401

    def test_list_employees_sort(self, client: TestClient, admin_token, db_session):
        dept = Department(name="测试部", code="TEST")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp1 = Employee(employee_no="SORT001", name="张三", department_id=dept.id, position_id=pos.id)
        emp2 = Employee(employee_no="SORT002", name="李四", department_id=dept.id, position_id=pos.id)
        db_session.add_all([emp1, emp2])
        db_session.commit()

        resp = client.get("/employees?sort=name&order=asc", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        names = [item["name"] for item in data["items"] if item["name"] in ("张三", "李四")]
        assert names == sorted(names)


class TestEmployeeGet:
    """Tests for GET /employees/{employee_id}"""

    def test_get_employee_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="测试部", code="TEST")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="GET001", name="获取员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.commit()
        db_session.refresh(emp)

        resp = client.get(f"/employees/{emp.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == emp.id
        assert data["employee_no"] == "GET001"
        assert data["name"] == "获取员工"
        assert data["department_id"] == dept.id
        assert data["department_name"] == "测试部"
        assert data["position_id"] == pos.id
        assert data["position_name"] == "测试岗"
        assert data["is_active"] is True
        assert "created_at" in data

    def test_get_employee_not_found(self, client: TestClient, admin_token):
        resp = client.get("/employees/99999", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404

    def test_get_employee_no_auth(self, client: TestClient):
        resp = client.get("/employees/1")
        assert resp.status_code == 401


class TestEmployeeCreate:
    """Tests for POST /employees"""

    def test_create_employee_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="新建部", code="NEW")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="新建岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        db_session.commit()

        payload = {
            "employee_no": "NEW001",
            "name": "新员工",
            "department_id": dept.id,
            "position_id": pos.id,
        }
        resp = client.post("/employees", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] is not None
        assert data["employee_no"] == "NEW001"
        assert data["name"] == "新员工"
        assert data["department_id"] == dept.id
        assert data["department_name"] == "新建部"
        assert data["position_id"] == pos.id
        assert data["position_name"] == "新建岗"
        assert data["is_active"] is True
        assert "created_at" in data

    def test_create_employee_duplicate_employee_no(self, client: TestClient, admin_token, db_session):
        dept = Department(name="重复部", code="DUP")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="重复岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="DUP001", name="已有员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.commit()

        payload = {"employee_no": "DUP001", "name": "新员工", "department_id": dept.id, "position_id": pos.id}
        resp = client.post("/employees", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 409
        assert resp.json()["message"] == "工号已存在"

    def test_create_employee_invalid_department(self, client: TestClient, admin_token):
        payload = {"employee_no": "INV001", "name": "员工", "department_id": 99999, "position_id": 1}
        resp = client.post("/employees", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert resp.json()["message"] == "部门不存在"

    def test_create_employee_invalid_position(self, client: TestClient, admin_token, db_session):
        dept = Department(name="测试部", code="TEST")
        db_session.add(dept)
        db_session.flush()
        db_session.commit()

        payload = {"employee_no": "INV002", "name": "员工", "department_id": dept.id, "position_id": 99999}
        resp = client.post("/employees", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert resp.json()["message"] == "岗位不存在"

    def test_create_employee_with_manager(self, client: TestClient, admin_token, db_session):
        dept = Department(name="测试部", code="TEST")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        mgr = Employee(employee_no="MGR001", name="上级", department_id=dept.id, position_id=pos.id)
        db_session.add(mgr)
        db_session.flush()
        db_session.commit()

        payload = {"employee_no": "SUB001", "name": "下属", "department_id": dept.id, "position_id": pos.id, "manager_employee_no": "MGR001"}
        resp = client.post("/employees", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["manager_id"] == mgr.id
        assert data["manager_name"] == "上级"

    def test_create_employee_unauthorized_role(self, client: TestClient, employee_token):
        payload = {"employee_no": "UNAUTH001", "name": "未授权"}
        resp = client.post("/employees", json=payload, headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403

    def test_create_employee_no_auth(self, client: TestClient):
        payload = {"employee_no": "NOAUTH001", "name": "未认证"}
        resp = client.post("/employees", json=payload)
        assert resp.status_code == 401

    def test_create_employee_missing_required_fields(self, client: TestClient, admin_token):
        payload = {"name": "缺少工号"}
        resp = client.post("/employees", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422


class TestEmployeeUpdate:
    """Tests for PUT /employees/{employee_id}"""

    def test_update_employee_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="更新部", code="UPD")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="更新岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="UPD001", name="原姓名", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.commit()
        db_session.refresh(emp)

        payload = {"name": "新姓名"}
        resp = client.put(f"/employees/{emp.id}", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == emp.id
        assert data["name"] == "新姓名"
        assert data["employee_no"] == "UPD001"
        assert data["department_id"] == dept.id
        assert data["position_id"] == pos.id
        assert "created_at" in data
        assert data["id"] == emp.id
        assert data["employee_no"] == "UPD001"
        assert data["department_id"] == dept.id
        assert data["position_id"] == pos.id
        assert "created_at" in data
        assert data["id"] == emp.id
        assert data["employee_no"] == "UPD001"
        assert data["department_id"] == dept.id
        assert data["position_id"] == pos.id
        assert "created_at" in data

    def test_update_employee_not_found(self, client: TestClient, admin_token):
        payload = {"name": "新姓名"}
        resp = client.put("/employees/99999", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404

    def test_update_employee_duplicate_employee_no(self, client: TestClient, admin_token, db_session):
        dept = Department(name="重复部", code="DUP")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="重复岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp1 = Employee(employee_no="DUPA001", name="员工A", department_id=dept.id, position_id=pos.id)
        emp2 = Employee(employee_no="DUPA002", name="员工B", department_id=dept.id, position_id=pos.id)
        db_session.add_all([emp1, emp2])
        db_session.commit()

        payload = {"employee_no": "DUPA002"}
        resp = client.put(f"/employees/{emp1.id}", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 409
        assert resp.json()["message"] == "工号已存在"

    def test_update_employee_manager_by_employee_no(self, client: TestClient, admin_token, db_session):
        dept = Department(name="测试部", code="TEST")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        mgr = Employee(employee_no="MGR002", name="新上级", department_id=dept.id, position_id=pos.id)
        emp = Employee(employee_no="SUB002", name="下属", department_id=dept.id, position_id=pos.id)
        db_session.add_all([mgr, emp])
        db_session.commit()
        db_session.refresh(emp)

        payload = {"manager_employee_no": "MGR002"}
        resp = client.put(f"/employees/{emp.id}", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["manager_id"] == mgr.id
        assert data["manager_name"] == "新上级"

    def test_update_employee_unauthorized(self, client: TestClient, employee_token):
        payload = {"name": "未授权修改"}
        resp = client.put("/employees/1", json=payload, headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403


class TestEmployeeDelete:
    """Tests for DELETE /employees/{employee_id}"""

    def test_delete_employee_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="删除部", code="DEL")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="删除岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="DEL001", name="待删除", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.commit()
        db_session.refresh(emp)

        resp = client.delete(f"/employees/{emp.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 204

    def test_delete_employee_with_records(self, client: TestClient, admin_token, db_session):
        from app.models import AssessmentCycle
        from datetime import date
        dept = Department(name="删除部", code="DEL")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="删除岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="DEL002", name="有记录员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
        cycle = AssessmentCycle(name="2024Q1", type="quarterly", start_date=date(2024,1,1), end_date=date(2024,3,31))
        db_session.add(cycle)
        db_session.flush()
        record = AssessmentRecord(cycle_id=cycle.id, employee_id=emp.id)
        db_session.add(record)
        db_session.commit()
        db_session.refresh(emp)

        resp = client.delete(f"/employees/{emp.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 409
        assert "考核历史数据" in resp.json()["message"]

    def test_delete_employee_not_found(self, client: TestClient, admin_token):
        resp = client.delete("/employees/99999", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404

    def test_delete_employee_unauthorized(self, client: TestClient, employee_token):
        resp = client.delete("/employees/1", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403


class TestEmployeeImport:
    """Tests for POST /employees/import"""

    def test_import_employees_success(self, client: TestClient, admin_token):
        # This would require a valid Excel file; for now just test the endpoint structure
        # With openpyxl available in requirements
        resp = client.post("/employees/import", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422  # No file uploaded

    def test_import_employees_no_auth(self, client: TestClient):
        resp = client.post("/employees/import")
        assert resp.status_code == 401

    def test_import_employees_unauthorized(self, client: TestClient, employee_token):
        resp = client.post("/employees/import", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403


class TestEmployeeImportPreview:
    """Tests for POST /employees/import-preview"""

    def test_import_preview_no_file(self, client: TestClient, admin_token):
        resp = client.post("/employees/import-preview", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422  # No file uploaded

    def test_import_preview_no_auth(self, client: TestClient):
        resp = client.post("/employees/import-preview")
        assert resp.status_code == 401

    def test_import_preview_unauthorized(self, client: TestClient, employee_token):
        resp = client.post("/employees/import-preview", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403


class TestEmployeeImportStatus:
    """Tests for GET /employees/import/status"""

    def test_import_status_success(self, client: TestClient, admin_token):
        resp = client.get("/employees/import/status", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["progress"] == 100

    def test_import_status_no_auth(self, client: TestClient):
        resp = client.get("/employees/import/status")
        assert resp.status_code == 401


class TestEmployeeSubordinates:
    """Tests for GET /employees/{employee_id}/subordinates"""

    def test_get_subordinates_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="技术部", code="TECH")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="工程师", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        # 李建国 (manager_id=null)
        li = Employee(employee_no="LJG001", name="李建国", department_id=dept.id, position_id=pos.id, manager_id=None)
        db_session.add(li)
        db_session.flush()
        # 王志强 (manager_id=李建国)
        wang = Employee(employee_no="WZQ001", name="王志强", department_id=dept.id, position_id=pos.id, manager_id=li.id)
        db_session.add(wang)
        db_session.commit()

        resp = client.get(f"/employees/{li.id}/subordinates", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "王志强"
        assert data[0]["employee_no"] == "WZQ001"

    def test_get_subordinates_empty(self, client: TestClient, admin_token, db_session):
        dept = Department(name="技术部", code="TECH")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="工程师", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        wang = Employee(employee_no="WZQ001", name="王志强", department_id=dept.id, position_id=pos.id, manager_id=None)
        db_session.add(wang)
        db_session.commit()

        # 查询王志强下属 -> 空数组
        resp = client.get(f"/employees/{wang.id}/subordinates", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data == []

    def test_get_subordinates_not_found(self, client: TestClient, admin_token):
        resp = client.get("/employees/99999/subordinates", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404

    def test_get_subordinates_unauthorized(self, client: TestClient, employee_token):
        resp = client.get("/employees/1/subordinates", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403

    def test_get_subordinates_no_auth(self, client: TestClient):
        resp = client.get("/employees/1/subordinates")
        assert resp.status_code == 401


class TestEmployeeSubordinates:
    """Tests for GET /employees/{employee_id}/subordinates"""

    def test_get_subordinates_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="技术部", code="TECH")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="工程师", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        # 李建国 (manager_id=null)
        li = Employee(employee_no="LJG001", name="李建国", department_id=dept.id, position_id=pos.id, manager_id=None)
        db_session.add(li)
        db_session.flush()
        # 王志强 (manager_id=李建国)
        wang = Employee(employee_no="WZQ001", name="王志强", department_id=dept.id, position_id=pos.id, manager_id=li.id)
        db_session.add(wang)
        db_session.commit()

        resp = client.get(f"/employees/{li.id}/subordinates", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "王志强"
        assert data[0]["employee_no"] == "WZQ001"

    def test_get_subordinates_empty(self, client: TestClient, admin_token, db_session):
        dept = Department(name="技术部", code="TECH")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="工程师", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        wang = Employee(employee_no="WZQ001", name="王志强", department_id=dept.id, position_id=pos.id, manager_id=None)
        db_session.add(wang)
        db_session.commit()

        # 查询王志强下属 -> 空数组
        resp = client.get(f"/employees/{wang.id}/subordinates", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data == []

    def test_get_subordinates_not_found(self, client: TestClient, admin_token):
        resp = client.get("/employees/99999/subordinates", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404

    def test_get_subordinates_unauthorized(self, client: TestClient, employee_token):
        resp = client.get("/employees/1/subordinates", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403

    def test_get_subordinates_no_auth(self, client: TestClient):
        resp = client.get("/employees/1/subordinates")
        assert resp.status_code == 401
