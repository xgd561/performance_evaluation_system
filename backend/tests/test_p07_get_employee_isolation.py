import pytest
from fastapi.testclient import TestClient
from app.models import Employee, Department, Position


class TestGetEmployeeIsolation:
    """P0-7: GET /employees/{id} data isolation."""

    def test_peer_cannot_view_any(self, client: TestClient, peer_token):
        resp = client.get(
            "/employees/1",
            headers={"Authorization": f"Bearer {peer_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_employee_can_view_self(self, client: TestClient, employee_token, employee_user):
        resp = client.get(
            f"/employees/{employee_user.employee_id}",
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert resp.json()["id"] == employee_user.employee_id

    def test_employee_cannot_view_other(self, client: TestClient, employee_token, manager_user):
        resp = client.get(
            f"/employees/{manager_user.employee_id}",
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_manager_can_view_same_department(self, client: TestClient, manager_token, employee_user):
        # employee_user and manager_user are both in TECH department by default
        resp = client.get(
            f"/employees/{employee_user.employee_id}",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_manager_can_view_direct_subordinate(self, client: TestClient, manager_token, manager_user, employee_user, db_session):
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        emp.manager_id = manager_user.employee_id
        db_session.commit()
        resp = client.get(
            f"/employees/{employee_user.employee_id}",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_manager_can_view_indirect_subordinate(self, client: TestClient, manager_token, manager_user, employee_user, db_session):
        # Set employee_user as direct subordinate of manager
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        emp.manager_id = manager_user.employee_id
        db_session.commit()

        # Create indirect subordinate (managed by employee_user)
        dept = db_session.query(Department).filter(Department.id == emp.department_id).first()
        pos = db_session.query(Position).filter(Position.department_id == dept.id).first()
        indirect = Employee(
            employee_no="EMP002",
            name="间接下属",
            department_id=dept.id,
            position_id=pos.id,
            manager_id=emp.id,
        )
        db_session.add(indirect)
        db_session.commit()
        db_session.refresh(indirect)

        resp = client.get(
            f"/employees/{indirect.id}",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_manager_cannot_view_other_department(self, client: TestClient, manager_token, hr_user):
        # hr_user is in HR department, manager is in TECH
        resp = client.get(
            f"/employees/{hr_user.employee_id}",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    def test_admin_can_view_any(self, client: TestClient, admin_token, employee_user):
        resp = client.get(
            f"/employees/{employee_user.employee_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_hr_can_view_any(self, client: TestClient, hr_token, employee_user):
        resp = client.get(
            f"/employees/{employee_user.employee_id}",
            headers={"Authorization": f"Bearer {hr_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_executive_can_view_any(self, client: TestClient, executive_token, employee_user):
        resp = client.get(
            f"/employees/{employee_user.employee_id}",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
