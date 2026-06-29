import pytest
from fastapi.testclient import TestClient
from app.models import AssessmentCycle, Employee, Department, Position, AssessmentRecord, CycleEmployee
from datetime import date, timedelta
import json


class TestCycleList:
    """Tests for GET /assessment-cycles"""

    def test_list_cycles_success(self, client: TestClient, admin_token, db_session):
        cycle = AssessmentCycle(
            name="测试周期", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30),
            self_due_date=date.today() + timedelta(days=10),
            manager_due_date=date.today() + timedelta(days=20),
            peer_due_date=date.today() + timedelta(days=25),
            status="not_started"
        )
        db_session.add(cycle)
        db_session.commit()

        resp = client.get("/assessment-cycles", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        cycle_data = next(c for c in data if c["name"] == "测试周期")
        assert cycle_data["type"] == "monthly"
        assert cycle_data["status"] == "not_started"
        assert "start_date" in cycle_data
        assert "end_date" in cycle_data
        assert cycle_data["self_due_date"] == str(date.today() + timedelta(days=10))
        assert cycle_data["manager_due_date"] == str(date.today() + timedelta(days=20))
        assert cycle_data["peer_due_date"] == str(date.today() + timedelta(days=25))
        assert "id" in cycle_data
        assert "created_at" in cycle_data
        assert "weights" in cycle_data
        assert "grade_rules" in cycle_data

    def test_list_cycles_no_auth(self, client: TestClient):
        resp = client.get("/assessment-cycles")
        assert resp.status_code == 401


class TestCycleCreate:
    """Tests for POST /assessment-cycles"""

    def test_create_cycle_success(self, client: TestClient, admin_token):
        payload = {
            "name": "新建周期",
            "type": "monthly",
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=30)),
            "self_due_date": str(date.today() + timedelta(days=10)),
            "manager_due_date": str(date.today() + timedelta(days=20)),
            "peer_due_date": str(date.today() + timedelta(days=25)),
            "weights": {"self": 30, "manager": 50, "peer": 20},
            "grade_rules": {"A": 90, "B": 80, "C": 60, "D": 0}
        }
        resp = client.post("/assessment-cycles", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "新建周期"
        assert data["status"] == "未开始"
        assert data["type"] == "monthly"
        assert data["start_date"] == str(date.today())
        assert data["end_date"] == str(date.today() + timedelta(days=30))
        assert data["self_due_date"] == str(date.today() + timedelta(days=10))
        assert data["manager_due_date"] == str(date.today() + timedelta(days=20))
        assert data["peer_due_date"] == str(date.today() + timedelta(days=25))
        assert data["weights"] == {"self": 30, "manager": 50, "peer": 20}
        assert data["grade_rules"] == {"A": 90, "B": 80, "C": 60, "D": 0}
        assert "id" in data
        assert data["id"] is not None
        assert "created_at" in data
        assert data["start_date"] == str(date.today())
        assert data["weights"] == {"self": 30, "manager": 50, "peer": 20}
        assert data["grade_rules"] == {"A": 90, "B": 80, "C": 60, "D": 0}
        assert "created_at" in data

    def test_create_cycle_weights_not_100(self, client: TestClient, admin_token):
        payload = {
            "name": "错误权重",
            "type": "monthly",
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=30)),
            "weights": {"self": 30, "manager": 50, "peer": 10},
            "grade_rules": {"A": 90, "B": 80, "C": 60, "D": 0}
        }
        resp = client.post("/assessment-cycles", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "权重总和必须等于100" in resp.json()["message"]

    def test_create_cycle_end_before_start(self, client: TestClient, admin_token):
        today = date.today()
        payload = {
            "name": "错误日期",
            "type": "monthly",
            "start_date": str(today),
            "end_date": str(today - timedelta(days=1)),
            "weights": {"self": 30, "manager": 50, "peer": 20},
            "grade_rules": {"A": 90, "B": 80, "C": 60, "D": 0}
        }
        resp = client.post("/assessment-cycles", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "结束日期不能早于开始日期" in resp.json()["message"]

    def test_create_cycle_unauthorized(self, client: TestClient, employee_token):
        payload = {"name": "未授权", "type": "monthly", "start_date": str(date.today()), "end_date": str(date.today()), "weights": {"self": 30, "manager": 50, "peer": 20}, "grade_rules": {"A": 90}}
        resp = client.post("/assessment-cycles", json=payload, headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403


class TestCycleUpdate:
    """Tests for PUT /assessment-cycles/{cycle_id}"""

    def test_update_cycle_success(self, client: TestClient, admin_token, db_session):
        cycle = AssessmentCycle(
            name="更新前", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30),
            self_due_date=date.today() + timedelta(days=10),
            manager_due_date=date.today() + timedelta(days=20),
            peer_due_date=date.today() + timedelta(days=25),
            status="not_started"
        )
        db_session.add(cycle)
        db_session.commit()
        db_session.refresh(cycle)

        payload = {
            "name": "更新后",
            "self_due_date": str(date.today() + timedelta(days=15)),
            "manager_due_date": str(date.today() + timedelta(days=22)),
            "peer_due_date": str(date.today() + timedelta(days=28)),
        }
        resp = client.put(f"/assessment-cycles/{cycle.id}", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "更新后"
        assert data["id"] == cycle.id
        assert data["status"] == "not_started"
        assert data["self_due_date"] == str(date.today() + timedelta(days=15))
        assert data["manager_due_date"] == str(date.today() + timedelta(days=22))
        assert data["peer_due_date"] == str(date.today() + timedelta(days=28))
        assert data["type"] == "monthly"
        assert "start_date" in data
        assert "end_date" in data
        assert "weights" in data
        assert "grade_rules" in data
        assert "created_at" in data

    def test_update_cycle_not_found(self, client: TestClient, admin_token):
        payload = {"name": "不存在"}
        resp = client.put("/assessment-cycles/99999", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404

    def test_update_cycle_already_launched(self, client: TestClient, admin_token, db_session):
        cycle = AssessmentCycle(
            name="已发起", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status="pending_self"
        )
        db_session.add(cycle)
        db_session.commit()
        db_session.refresh(cycle)

        payload = {"name": "尝试修改"}
        resp = client.put(f"/assessment-cycles/{cycle.id}", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 409
        assert resp.json()["message"] == "已发起的考核周期不可修改"


class TestCycleDelete:
    """Tests for DELETE /assessment-cycles/{cycle_id}"""

    def test_delete_cycle_success(self, client: TestClient, admin_token, db_session):
        cycle = AssessmentCycle(
            name="待删除", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status="not_started"
        )
        db_session.add(cycle)
        db_session.commit()
        db_session.refresh(cycle)

        resp = client.delete(f"/assessment-cycles/{cycle.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 204

    def test_delete_cycle_with_records(self, client: TestClient, admin_token, db_session):
        cycle = AssessmentCycle(
            name="有记录", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status="not_started"
        )
        db_session.add(cycle)
        db_session.flush()
        dept = Department(name="测试部", code="TEST")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="DELC001", name="员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
        record = AssessmentRecord(cycle_id=cycle.id, employee_id=emp.id)
        db_session.add(record)
        db_session.commit()
        db_session.refresh(cycle)

        resp = client.delete(f"/assessment-cycles/{cycle.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 409
        assert resp.json()["message"] == "该周期已包含考核数据，不可删除"

    def test_delete_cycle_not_found(self, client: TestClient, admin_token):
        resp = client.delete("/assessment-cycles/99999", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404


class TestCycleLaunch:
    """Tests for POST /assessment-cycles/launch"""

    def test_launch_cycle_success(self, client: TestClient, admin_token, db_session):
        cycle = AssessmentCycle(
            name="发起周期", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status="not_started"
        )
        db_session.add(cycle)
        db_session.flush()
        dept = Department(name="测试部", code="TEST")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="LAUNCH001", name="员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.commit()
        db_session.refresh(cycle)
        db_session.refresh(emp)

        payload = {"cycle_id": cycle.id, "employee_ids": [emp.id]}
        resp = client.post("/assessment-cycles/launch", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["created_records"] == 1

    def test_launch_cycle_no_employees(self, client: TestClient, admin_token, db_session):
        cycle = AssessmentCycle(
            name="空周期", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status="not_started"
        )
        db_session.add(cycle)
        db_session.commit()
        db_session.refresh(cycle)

        payload = {"cycle_id": cycle.id, "employee_ids": []}
        resp = client.post("/assessment-cycles/launch", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 409
        assert resp.json()["message"] == "至少选择一名员工"

    def test_launch_cycle_invalid_employee(self, client: TestClient, admin_token, db_session):
        cycle = AssessmentCycle(
            name="无效员工", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status="not_started"
        )
        db_session.add(cycle)
        db_session.commit()
        db_session.refresh(cycle)

        payload = {"cycle_id": cycle.id, "employee_ids": [99999]}
        resp = client.post("/assessment-cycles/launch", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422

    def test_launch_cycle_not_found(self, client: TestClient, admin_token):
        payload = {"cycle_id": 99999, "employee_ids": [1]}
        resp = client.post("/assessment-cycles/launch", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404


class TestCycleAddEmployees:
    """Tests for POST /assessment-cycles/add-employees"""

    def test_add_employees_success(self, client: TestClient, admin_token, db_session):
        cycle = AssessmentCycle(
            name="添加员工", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status="not_started"
        )
        db_session.add(cycle)
        db_session.flush()
        dept = Department(name="测试部", code="TEST")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="ADD001", name="员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.commit()
        db_session.refresh(cycle)
        db_session.refresh(emp)

        payload = {"cycle_id": cycle.id, "employee_ids": [emp.id]}
        resp = client.post("/assessment-cycles/add-employees", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "employees" in data

    def test_add_employees_cycle_not_found(self, client: TestClient, admin_token):
        payload = {"cycle_id": 99999, "employee_ids": [1]}
        resp = client.post("/assessment-cycles/add-employees", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404


class TestCycleRemoveEmployee:
    """Tests for DELETE /assessment-cycles/{cycle_id}/employees/{employee_id}"""

    def test_remove_employee_success(self, client: TestClient, admin_token, db_session):
        cycle = AssessmentCycle(
            name="移除员工", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status="not_started"
        )
        db_session.add(cycle)
        db_session.flush()
        dept = Department(name="测试部", code="TEST")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="REM001", name="员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
        ce = CycleEmployee(cycle_id=cycle.id, employee_id=emp.id)
        db_session.add(ce)
        db_session.commit()

        resp = client.delete(f"/assessment-cycles/{cycle.id}/employees/{emp.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 204

    def test_remove_employee_not_found(self, client: TestClient, admin_token):
        resp = client.delete("/assessment-cycles/99999/employees/99999", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 204


class TestCycleProgress:
    """Tests for GET /assessment-cycles/{cycle_id}/progress"""

    def test_cycle_progress_success(self, client: TestClient, admin_token, db_session):
        cycle = AssessmentCycle(
            name="进度周期", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status="pending_self"
        )
        db_session.add(cycle)
        db_session.flush()
        dept = Department(name="测试部", code="TEST")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="PROG001", name="员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
        ce = CycleEmployee(cycle_id=cycle.id, employee_id=emp.id)
        db_session.add(ce)
        db_session.commit()
        db_session.refresh(cycle)

        resp = client.get(f"/assessment-cycles/{cycle.id}/progress", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["cycle_id"] == cycle.id
        assert data["total_employees"] == 1
        assert "stages" in data
        assert "overall_progress" in data

    def test_cycle_progress_not_found(self, client: TestClient, admin_token):
        resp = client.get("/assessment-cycles/99999/progress", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404

    def test_cycle_progress_unauthorized(self, client: TestClient, employee_token):
        resp = client.get("/assessment-cycles/1/progress", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403
