import pytest
from fastapi.testclient import TestClient
from app.models import Department, Position, Employee


class TestDepartmentList:
    """Tests for GET /departments"""

    def test_list_departments_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="测试部", code="TEST")
        db_session.add(dept)
        db_session.commit()

        resp = client.get("/departments", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        dept_data = next(d for d in data if d["name"] == "测试部")
        assert dept_data["code"] == "TEST"
        assert "id" in dept_data
        assert "created_at" in dept_data
        assert "position_count" in dept_data
        assert "employee_count" in dept_data
        assert "parent_name" in dept_data

    def test_list_departments_with_counts(self, client: TestClient, admin_token, db_session):
        dept = Department(name="计数部", code="COUNT")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="计数岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="CNT001", name="计数员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.commit()

        resp = client.get("/departments", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        dept_data = next(d for d in data if d["name"] == "计数部")
        assert dept_data["position_count"] == 1
        assert dept_data["employee_count"] == 1

    def test_list_departments_no_auth(self, client: TestClient):
        resp = client.get("/departments")
        assert resp.status_code == 401


class TestDepartmentCreate:
    """Tests for POST /departments"""

    def test_create_department_success(self, client: TestClient, admin_token):
        payload = {"name": "新建部门", "code": "NEWDEPT"}
        resp = client.post("/departments", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "新建部门"
        assert data["code"] == "NEWDEPT"
        assert data["id"] is not None
        assert "created_at" in data

    def test_create_department_duplicate_code(self, client: TestClient, admin_token, db_session):
        dept = Department(name="已有部门", code="EXIST")
        db_session.add(dept)
        db_session.commit()

        payload = {"name": "新部门", "code": "EXIST"}
        resp = client.post("/departments", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 409
        assert resp.json()["message"] == "部门编码已存在"

    def test_create_department_duplicate_name(self, client: TestClient, admin_token, db_session):
        dept = Department(name="唯一名称", code="UNIQUE1")
        db_session.add(dept)
        db_session.commit()

        payload = {"name": "唯一名称", "code": "UNIQUE2"}
        resp = client.post("/departments", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 409
        assert resp.json()["message"] == "部门名称已存在"

    def test_create_department_unauthorized(self, client: TestClient, employee_token):
        payload = {"name": "未授权部门"}
        resp = client.post("/departments", json=payload, headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403

    def test_create_department_no_auth(self, client: TestClient):
        payload = {"name": "未认证部门"}
        resp = client.post("/departments", json=payload)
        assert resp.status_code == 401


class TestDepartmentUpdate:
    """Tests for PUT /departments/{dept_id}"""

    def test_update_department_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="更新前", code="UPD1")
        db_session.add(dept)
        db_session.commit()
        db_session.refresh(dept)

        payload = {"name": "更新后"}
        resp = client.put(f"/departments/{dept.id}", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == dept.id
        assert data["name"] == "更新后"
        assert data["code"] == "UPD1"
        assert "created_at" in data

    def test_update_department_not_found(self, client: TestClient, admin_token):
        payload = {"name": "不存在"}
        resp = client.put("/departments/99999", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404

    def test_update_department_unauthorized(self, client: TestClient, employee_token):
        payload = {"name": "未授权"}
        resp = client.put("/departments/1", json=payload, headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403


class TestDepartmentDelete:
    """Tests for DELETE /departments/{dept_id}"""

    def test_delete_department_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="待删除", code="DEL1")
        db_session.add(dept)
        db_session.commit()
        db_session.refresh(dept)

        resp = client.delete(f"/departments/{dept.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 204

    def test_delete_department_with_employees(self, client: TestClient, admin_token, db_session):
        dept = Department(name="有员工部", code="WEMP")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="有员工岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="WEMP001", name="员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.commit()
        db_session.refresh(dept)

        resp = client.delete(f"/departments/{dept.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 400
        assert resp.json()["message"] == "部门下存在员工，不可删除"

    def test_delete_department_with_positions(self, client: TestClient, admin_token, db_session):
        dept = Department(name="有岗位部", code="WPOS")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="有岗位岗", department_id=dept.id)
        db_session.add(pos)
        db_session.commit()
        db_session.refresh(dept)

        resp = client.delete(f"/departments/{dept.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 400
        assert resp.json()["message"] == "部门下存在岗位，不可删除"

    def test_delete_department_with_children(self, client: TestClient, admin_token, db_session):
        """删除有子部门的部门应返回 400"""
        parent = Department(name="父部门", code="PARENT")
        db_session.add(parent)
        db_session.flush()
        child = Department(name="子部门", code="CHILD", parent_id=parent.id)
        db_session.add(child)
        db_session.commit()
        db_session.refresh(parent)

        resp = client.delete(f"/departments/{parent.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 400
        assert resp.json()["message"] == "部门下存在子部门，不可删除"

    def test_delete_department_not_found(self, client: TestClient, admin_token):
        resp = client.delete("/departments/99999", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404

    def test_delete_department_unauthorized(self, client: TestClient, employee_token):
        resp = client.delete("/departments/1", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403


class TestDepartmentTree:
    """Tests for GET /departments?tree=true (recursive CTE tree query)"""

    def test_tree_query_returns_nested_structure(self, client: TestClient, admin_token, db_session):
        """创建研发部 → 创建产品部（parent_id=研发部）→ 树形查询返回正确层级."""
        # Create root department
        rd = Department(name="研发部", code="RD")
        db_session.add(rd)
        db_session.flush()
        # Create child department
        pd = Department(name="产品部", code="PD", parent_id=rd.id)
        db_session.add(pd)
        db_session.commit()

        resp = client.get("/departments?tree=true", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

        # Find root node
        rd_node = next(d for d in data if d["name"] == "研发部")
        assert rd_node["code"] == "RD"
        assert rd_node["parent_id"] is None
        assert rd_node["level"] == 0
        assert "children" in rd_node
        assert len(rd_node["children"]) == 1

        # Verify child node
        child = rd_node["children"][0]
        assert child["name"] == "产品部"
        assert child["code"] == "PD"
        assert child["parent_id"] == rd.id
        assert child["level"] == 1
        assert child["children"] == []

    def test_tree_query_with_deep_nesting(self, client: TestClient, admin_token, db_session):
        """验证三级嵌套部门树形查询."""
        # Create grandparent
        gp = Department(name="总公司", code="HQ")
        db_session.add(gp)
        db_session.flush()
        # Create parent
        p = Department(name="分公司", code="BRANCH", parent_id=gp.id)
        db_session.add(p)
        db_session.flush()
        # Create child
        c = Department(name="办事处", code="OFFICE", parent_id=p.id)
        db_session.add(c)
        db_session.commit()

        resp = client.get("/departments?tree=true", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()

        hq_node = next(d for d in data if d["name"] == "总公司")
        assert hq_node["level"] == 0
        assert len(hq_node["children"]) == 1

        branch_node = hq_node["children"][0]
        assert branch_node["name"] == "分公司"
        assert branch_node["level"] == 1
        assert len(branch_node["children"]) == 1

        office_node = branch_node["children"][0]
        assert office_node["name"] == "办事处"
        assert office_node["level"] == 2
        assert office_node["children"] == []

    def test_tree_query_no_auth(self, client: TestClient):
        resp = client.get("/departments?tree=true")
        assert resp.status_code == 401

    def test_tree_query_empty(self, client: TestClient, admin_token):
        """无部门时树形查询返回空列表."""
        resp = client.get("/departments?tree=true", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


class TestPositionList:
    """Tests for GET /positions"""

    def test_list_positions_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="岗位部", code="POS")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.commit()

        resp = client.get("/positions", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) >= 1
        item = data["items"][0]
        assert "id" in item and "name" in item and "department_id" in item and "created_at" in item

    def test_list_positions_by_department(self, client: TestClient, admin_token, db_session):
        dept = Department(name="筛选岗部", code="FPOS")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="筛选岗", department_id=dept.id)
        db_session.add(pos)
        db_session.commit()

        resp = client.get(f"/positions?department_id={dept.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert all(p["department_id"] == dept.id for p in data["items"])

    def test_list_positions_no_auth(self, client: TestClient):
        resp = client.get("/positions")
        assert resp.status_code == 401


class TestPositionCreate:
    """Tests for POST /positions"""

    def test_create_position_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="新建岗部", code="NEWPOS")
        db_session.add(dept)
        db_session.commit()

        payload = {"name": "新岗位", "department_id": dept.id}
        resp = client.post("/positions", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "新岗位"
        assert data["department_id"] == dept.id
        assert data["id"] is not None
        assert "created_at" in data

    def test_create_position_unauthorized(self, client: TestClient, employee_token):
        payload = {"name": "未授权岗"}
        resp = client.post("/positions", json=payload, headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403


class TestPositionUpdate:
    """Tests for PUT /positions/{pos_id}"""

    def test_update_position_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="更新岗部", code="UPDPOS")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="原岗位", department_id=dept.id)
        db_session.add(pos)
        db_session.commit()
        db_session.refresh(pos)

        payload = {"name": "新岗位名"}
        resp = client.put(f"/positions/{pos.id}", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "新岗位名"
        assert data["id"] == pos.id
        assert data["department_id"] == dept.id
        assert "created_at" in data

    def test_update_position_not_found(self, client: TestClient, admin_token):
        payload = {"name": "不存在"}
        resp = client.put("/positions/99999", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404


class TestPositionDelete:
    """Tests for DELETE /positions/{pos_id}"""

    def test_delete_position_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="删除岗部", code="DELPOS")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="待删除岗", department_id=dept.id)
        db_session.add(pos)
        db_session.commit()
        db_session.refresh(pos)

        resp = client.delete(f"/positions/{pos.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 204

    def test_delete_position_with_employees(self, client: TestClient, admin_token, db_session):
        dept = Department(name="有员工岗部", code="WEMPPOS")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="有员工岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="WEMP001", name="员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.commit()
        db_session.refresh(pos)

        resp = client.delete(f"/positions/{pos.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 409
        assert resp.json()["message"] == "岗位下存在员工，不可删除"

    def test_delete_position_not_found(self, client: TestClient, admin_token):
        resp = client.delete("/positions/99999", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404

    def test_delete_position_unauthorized(self, client: TestClient, employee_token):
        resp = client.delete("/positions/1", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403
