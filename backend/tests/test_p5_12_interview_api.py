import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models import (
    AssessmentRecord, AssessmentCycle, Employee, Department, Position, User
)
from app.auth import get_password_hash


class TestP5_12InterviewApi:
    """P5-12: 绩效面谈后端 API 测试"""

    def _login(self, client: TestClient, username: str, password: str):
        resp = client.post("/auth/login", json={"username": username, "password": password})
        assert resp.status_code == 200, resp.text
        return resp.json()["access_token"]

    def _create_employee_with_user(self, db_session: Session, username: str, employee_no: str, name: str, role: str, manager_id: int = None):
        dept = db_session.query(Department).filter(Department.code == "TEST").first()
        if not dept:
            dept = Department(name="测试部", code="TEST")
            db_session.add(dept)
            db_session.flush()
        pos = db_session.query(Position).filter(Position.name == "测试岗", Position.department_id == dept.id).first()
        if not pos:
            pos = Position(name="测试岗", department_id=dept.id)
            db_session.add(pos)
            db_session.flush()
        emp = Employee(employee_no=employee_no, name=name, department_id=dept.id, position_id=pos.id, manager_id=manager_id)
        db_session.add(emp)
        db_session.flush()
        user = User(
            username=username,
            password_hash=get_password_hash("Test@123"),
            role=role,
            employee_id=emp.id,
            is_first_login=False,
        )
        db_session.add(user)
        db_session.flush()
        return emp, user

    def _create_cycle(self, db_session: Session):
        cycle = AssessmentCycle(
            name="P5-12测试周期",
            type="annual",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow(),
            status="active",
        )
        db_session.add(cycle)
        db_session.flush()
        return cycle

    def _create_assessment_record(self, db_session: Session, cycle_id: int, employee_id: int, status: str = "pending_interview", grade: str = "B", total_score: float = 75.0):
        emp = db_session.query(Employee).filter(Employee.id == employee_id).first()
        record = AssessmentRecord(
            cycle_id=cycle_id,
            employee_id=employee_id,
            department_id=emp.department_id if emp else None,
            position_id=emp.position_id if emp else None,
            status=status,
            grade=grade,
            total_score=total_score,
        )
        db_session.add(record)
        db_session.flush()
        return record

    def test_success_submit_interview(self, client: TestClient, db_session: Session):
        """1. 成功提交面谈，状态变为 published"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p512_mgr1", "P512_M1", "经理1", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p512_emp1", "P512_E1", "员工1", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_interview", grade="B", total_score=85.0)
        db_session.commit()

        token = self._login(client, "p512_mgr1", "Test@123")
        resp = client.post(
            f"/api/v1/assessment-records/{record.id}/interview",
            json={
                "interview_time": (datetime.now() - timedelta(days=1)).isoformat(),
                "location": "会议室A",
                "content": "a" * 50,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["status"] == "published"
        assert data["interview_record"] is not None
        assert data["interview_record"]["interviewer_id"] == mgr_emp.id

    def test_c_grade_missing_improvement_plan_returns_400(self, client: TestClient, db_session: Session):
        """2. C等级未填改进计划返回 400"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p512_mgr2", "P512_M2", "经理2", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p512_emp2", "P512_E2", "员工2", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_interview", grade="C", total_score=65.0)
        db_session.commit()

        token = self._login(client, "p512_mgr2", "Test@123")
        resp = client.post(
            f"/api/v1/assessment-records/{record.id}/interview",
            json={
                "interview_time": (datetime.now() - timedelta(days=1)).isoformat(),
                "location": "会议室A",
                "content": "a" * 50,
                "improvement_plan": None,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"

    def test_non_pending_interview_status_returns_422(self, client: TestClient, db_session: Session):
        """3. 非 pending_interview 状态返回 422"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p512_mgr3", "P512_M3", "经理3", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p512_emp3", "P512_E3", "员工3", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_self", grade="B")
        db_session.commit()

        token = self._login(client, "p512_mgr3", "Test@123")
        resp = client.post(
            f"/api/v1/assessment-records/{record.id}/interview",
            json={
                "interview_time": (datetime.now() - timedelta(days=1)).isoformat(),
                "location": "会议室A",
                "content": "a" * 50,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    def test_not_direct_manager_returns_403(self, client: TestClient, db_session: Session):
        """4. 非直属上级返回 403"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p512_mgr4", "P512_M4", "经理4", "manager")
        other_mgr, other_mgr_user = self._create_employee_with_user(db_session, "p512_omgr", "P512_OM", "其他经理", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p512_emp4", "P512_E4", "员工4", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_interview", grade="B")
        db_session.commit()

        token = self._login(client, "p512_omgr", "Test@123")
        resp = client.post(
            f"/api/v1/assessment-records/{record.id}/interview",
            json={
                "interview_time": (datetime.now() - timedelta(days=1)).isoformat(),
                "location": "会议室A",
                "content": "a" * 50,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    def test_interview_time_in_future_returns_422(self, client: TestClient, db_session: Session):
        """5. 面谈时间大于当前返回 422"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p512_mgr5", "P512_M5", "经理5", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p512_emp5", "P512_E5", "员工5", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_interview", grade="B")
        db_session.commit()

        token = self._login(client, "p512_mgr5", "Test@123")
        resp = client.post(
            f"/api/v1/assessment-records/{record.id}/interview",
            json={
                "interview_time": (datetime.now() + timedelta(days=1)).isoformat(),
                "location": "会议室A",
                "content": "a" * 50,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    def test_content_too_short_returns_422(self, client: TestClient, db_session: Session):
        """6. 内容少于 50 字返回 422"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p512_mgr6", "P512_M6", "经理6", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p512_emp6", "P512_E6", "员工6", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_interview", grade="B")
        db_session.commit()

        token = self._login(client, "p512_mgr6", "Test@123")
        resp = client.post(
            f"/api/v1/assessment-records/{record.id}/interview",
            json={
                "interview_time": (datetime.now() - timedelta(days=1)).isoformat(),
                "location": "会议室A",
                "content": "太短",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    def test_d_grade_with_improvement_plan_success(self, client: TestClient, db_session: Session):
        """7. D等级填写改进计划后成功提交"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p512_mgr7", "P512_M7", "经理7", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p512_emp7", "P512_E7", "员工7", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_interview", grade="D", total_score=55.0)
        db_session.commit()

        token = self._login(client, "p512_mgr7", "Test@123")
        resp = client.post(
            f"/api/v1/assessment-records/{record.id}/interview",
            json={
                "interview_time": (datetime.now() - timedelta(days=1)).isoformat(),
                "location": "会议室A",
                "content": "a" * 50,
                "improvement_plan": "b" * 30,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["status"] == "published"
        assert data["interview_record"]["improvement_plan"] == "b" * 30

    def test_hr_can_submit_for_any(self, client: TestClient, db_session: Session, hr_user):
        """8. HR 可以提交任意员工的面谈"""
        from app.models import Employee
        hr = db_session.query(User).filter(User.username == "hr001").first()
        hr_emp = db_session.query(Employee).filter(Employee.id == hr.employee_id).first()

        emp_emp, emp_user = self._create_employee_with_user(db_session, "p512_emp8", "P512_E8", "员工8", "employee", manager_id=hr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_interview", grade="B")
        db_session.commit()

        token = self._login(client, "hr001", "Hr001@123")
        resp = client.post(
            f"/api/v1/assessment-records/{record.id}/interview",
            json={
                "interview_time": (datetime.now() - timedelta(days=1)).isoformat(),
                "location": "会议室A",
                "content": "a" * 50,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
