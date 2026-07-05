import pytest
from fastapi.testclient import TestClient
from app.models import Department, Position, Employee


class TestPositionList:
    """Tests for GET /positions"""

    def test_list_positions_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="技术部", code="TECH")
        db_session.add(dept)
        db_session.flush()
        pos1 = Position(name="Java工程师", department_id=dept.id)
        pos2 = Position(name="前端工程师", department_id=dept.id)
        db_session.add_all([pos1, pos2])
        db_session.commit()

        resp = client.get("/positions", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) >= 2
        names = [p["name"] for p in data["items"]]
        assert "Java工程师" in names
        assert "前端工程师" in names

    def test_list_positions_by_department(self, client: TestClient, admin_token, db_session):
        dept1 = Department(name="技术部", code="TECH")
        dept2 = Department(name="HR部", code="HR")
        db_session.add_all([dept1, dept2])
        db_session.flush()
        pos1 = Position(name="Java工程师", department_id=dept1.id)
        pos2 = Position(name="HR专员", department_id=dept2.id)
        db_session.add_all([pos1, pos2])
        db_session.commit()

        resp = client.get(f"/positions?department_id={dept1.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Java工程师"

    def test_list_positions_no_auth(self, client: TestClient):
        resp = client.get("/positions")
        assert resp.status_code == 401


class TestPositionCreate:
    """Tests for POST /positions"""

    def test_create_position_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="研发部", code="RD")
        db_session.add(dept)
        db_session.commit()

        payload = {"name": "研发工程师", "department_id": dept.id}
        resp = client.post("/positions", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "研发工程师"
        assert data["department_id"] == dept.id
        assert data["id"] is not None

    def test_create_position_without_department(self, client: TestClient, admin_token):
        payload = {"name": "无部门岗位"}
        resp = client.post("/positions", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "无部门岗位"
        assert data["department_id"] is None

    def test_create_position_unauthorized(self, client: TestClient, employee_token):
        payload = {"name": "未授权岗位"}
        resp = client.post("/positions", json=payload, headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403

    def test_create_position_no_auth(self, client: TestClient):
        payload = {"name": "未认证岗位"}
        resp = client.post("/positions", json=payload)
        assert resp.status_code == 401


class TestPositionUpdate:
    """Tests for PUT /positions/{pos_id}"""

    def test_update_position_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="更新部", code="UPD")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="原岗位", department_id=dept.id)
        db_session.add(pos)
        db_session.commit()
        db_session.refresh(pos)

        payload = {"name": "新岗位"}
        resp = client.put(f"/positions/{pos.id}", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == pos.id
        assert data["name"] == "新岗位"
        assert data["department_id"] == dept.id

    def test_update_position_not_found(self, client: TestClient, admin_token):
        payload = {"name": "不存在"}
        resp = client.put("/positions/99999", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404

    def test_update_position_unauthorized(self, client: TestClient, employee_token):
        payload = {"name": "未授权"}
        resp = client.put("/positions/1", json=payload, headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403


class TestPositionDelete:
    """Tests for DELETE /positions/{pos_id}"""

    def test_delete_position_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="删除部", code="DEL")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="待删除岗", department_id=dept.id)
        db_session.add(pos)
        db_session.commit()
        db_session.refresh(pos)

        resp = client.delete(f"/positions/{pos.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 204

    def test_delete_position_with_employees(self, client: TestClient, admin_token, db_session):
        dept = Department(name="有员工部", code="WEMP")
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
        assert "岗位下存在员工" in resp.json()["message"]

    def test_delete_position_not_found(self, client: TestClient, admin_token):
        resp = client.delete("/positions/99999", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404

    def test_delete_position_unauthorized(self, client: TestClient, employee_token):
        resp = client.delete("/positions/1", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403

    def test_delete_position_no_auth(self, client: TestClient):
        resp = client.delete("/positions/1")
        assert resp.status_code == 401
