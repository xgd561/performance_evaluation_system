import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime

from app.models import (
    AssessmentRecord, AssessmentCycle, Employee, Department, Position, User
)
from app.auth import get_password_hash


class TestP5_13InterviewList:
    """P5-13: 绩效面谈列表后端接口测试"""

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
            name="P5-13测试周期",
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

    def test_manager_login_returns_pending_list(self, client: TestClient, db_session: Session):
        """1. 经理登录返回待面谈列表"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p513_mgr1", "P513_M1", "李建国", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p513_emp1", "P513_E1", "员工1", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_interview", grade="B", total_score=75.0)
        db_session.commit()

        token = self._login(client, "p513_mgr1", "Test@123")
        resp = client.get(
            "/interviews/manager/interview-list",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "pending" in data
        assert "completed" in data
        assert len(data["pending"]) == 1
        assert data["pending"][0]["employee_name"] == "员工1"

    def test_cd_grade_marked_highlight(self, client: TestClient, db_session: Session):
        """2. C/D 等级员工标记 is_highlight: true"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p513_mgr2", "P513_M2", "经理2", "manager")
        emp_c, _ = self._create_employee_with_user(db_session, "p513_emp_c", "P513_EC", "员工C", "employee", manager_id=mgr_emp.id)
        emp_d, _ = self._create_employee_with_user(db_session, "p513_emp_d", "P513_ED", "员工D", "employee", manager_id=mgr_emp.id)
        emp_b, _ = self._create_employee_with_user(db_session, "p513_emp_b", "P513_EB", "员工B", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        self._create_assessment_record(db_session, cycle.id, emp_c.id, status="pending_interview", grade="C", total_score=65.0)
        self._create_assessment_record(db_session, cycle.id, emp_d.id, status="pending_interview", grade="D", total_score=55.0)
        self._create_assessment_record(db_session, cycle.id, emp_b.id, status="pending_interview", grade="B", total_score=85.0)
        db_session.commit()

        token = self._login(client, "p513_mgr2", "Test@123")
        resp = client.get(
            "/interviews/manager/interview-list",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        pending = data["pending"]
        assert len(pending) == 3
        for item in pending:
            if item["grade"] in ["C", "D"]:
                assert item["is_highlight"] is True
            else:
                assert item["is_highlight"] is False

    def test_search_filter_by_name(self, client: TestClient, db_session: Session):
        """3. 搜索过滤按员工姓名"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p513_mgr3", "P513_M3", "经理3", "manager")
        emp_a, _ = self._create_employee_with_user(db_session, "p513_emp_a", "P513_EA", "张三", "employee", manager_id=mgr_emp.id)
        emp_b, _ = self._create_employee_with_user(db_session, "p513_emp_b2", "P513_EB2", "李四", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        self._create_assessment_record(db_session, cycle.id, emp_a.id, status="pending_interview", grade="B")
        self._create_assessment_record(db_session, cycle.id, emp_b.id, status="pending_interview", grade="B")
        db_session.commit()

        token = self._login(client, "p513_mgr3", "Test@123")
        resp = client.get(
            "/interviews/manager/interview-list?keyword=张三",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert len(data["pending"]) == 1
        assert data["pending"][0]["employee_name"] == "张三"

    def test_search_filter_by_employee_no(self, client: TestClient, db_session: Session):
        """4. 搜索过滤按员工工号"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p513_mgr4", "P513_M4", "经理4", "manager")
        emp_a, _ = self._create_employee_with_user(db_session, "p513_emp_a2", "P513_EA2", "张三", "employee", manager_id=mgr_emp.id)
        emp_b, _ = self._create_employee_with_user(db_session, "p513_emp_b3", "P513_EB3", "李四", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        self._create_assessment_record(db_session, cycle.id, emp_a.id, status="pending_interview", grade="B")
        self._create_assessment_record(db_session, cycle.id, emp_b.id, status="pending_interview", grade="B")
        db_session.commit()

        token = self._login(client, "p513_mgr4", "Test@123")
        resp = client.get(
            "/interviews/manager/interview-list?keyword=P513_EB3",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert len(data["pending"]) == 1
        assert data["pending"][0]["employee_no"] == "P513_EB3"

    def test_hr_can_access(self, client: TestClient, db_session: Session, hr_user):
        """5. HR 也能访问面谈列表"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p513_mgr5", "P513_M5", "经理5", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p513_emp5", "P513_E5", "员工5", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_interview", grade="B")
        db_session.commit()

        token = self._login(client, "hr001", "Hr001@123")
        resp = client.get(
            "/interviews/manager/interview-list",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_completed_list_contains_published_with_interview(self, client: TestClient, db_session: Session):
        """6. completed 列表包含已发布且有面谈记录的数据"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p513_mgr6", "P513_M6", "经理6", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p513_emp6", "P513_E6", "员工6", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="published", grade="B")
        record.interview_record = {
            "interview_time": "2024-01-01T10:00:00",
            "location": "会议室",
            "content": "面谈内容",
        }
        db_session.commit()

        token = self._login(client, "p513_mgr6", "Test@123")
        resp = client.get(
            "/interviews/manager/interview-list",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert len(data["completed"]) == 1
        assert data["completed"][0]["record_id"] == record.id
