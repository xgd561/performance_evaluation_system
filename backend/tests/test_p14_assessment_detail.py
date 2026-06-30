import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date
from app.models import AssessmentRecord, AssessmentCycle, Employee, Department, Position, ScoreDetail, AppealRecord, InterviewRecord


def _get_or_create_dept(db_session: Session, code: str, name: str):
    dept = db_session.query(Department).filter(Department.code == code).first()
    if not dept:
        dept = Department(name=name, code=code)
        db_session.add(dept)
        db_session.flush()
    return dept


class TestAssessmentRecordDetail:
    """Tests for P1-14: assessment record detail endpoint"""

    def test_employee_can_view_own_detail(self, client: TestClient, employee_user, db_session: Session):
        """Employee should be able to view their own assessment detail"""
        dept = _get_or_create_dept(db_session, "TECH", "技术部")
        pos = db_session.query(Position).filter(Position.name == "Java工程师", Position.department_id == dept.id).first()
        if not pos:
            pos = Position(name="Java工程师", department_id=dept.id)
            db_session.add(pos)
            db_session.flush()
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        emp.department_id = dept.id
        emp.position_id = pos.id
        db_session.commit()

        cycle = AssessmentCycle(
            name="测试周期", type="季度",
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            status="published",
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id, employee_id=emp.id,
            department_id=dept.id, position_id=pos.id,
            self_scores='{"performance": 80, "ability": 85, "attitude": 90}',
            manager_scores='{"performance": 82, "ability": 83, "attitude": 88}',
            peer_scores='{"ability": 84}',
            weighted_performance=82.5,
            weighted_ability=83.5,
            weighted_attitude=88.0,
            total_score=85.0,
            grade="B",
            manager_comment="表现良好，继续努力",
            status="published",
        )
        db_session.add(record)
        db_session.flush()

        sd = ScoreDetail(
            record_id=record.id,
            kpi_name="销售额完成率",
            weight=50,
            target_value="100万",
            self_score=80,
            manager_score=82,
        )
        db_session.add(sd)
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "emp001", "password": "Emp001@123"})
        token = resp.json()["access_token"]

        resp = client.get(
            f"/scores/records/{record.id}/detail",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["record_id"] == record.id
        assert data["total_score"] in ("85.0", "85.00")
        assert data["grade"] == "B"
        assert data["manager_comment"] == "表现良好，继续努力"
        assert len(data["kpi_details"]) == 1
        assert data["kpi_details"][0]["kpi_name"] == "销售额完成率"
        assert data["self_scores"]["performance"] == 80
        assert data["manager_scores"]["performance"] == 82

    def test_employee_cannot_view_other_detail(self, client: TestClient, employee_user, db_session: Session):
        """Employee should not be able to view another employee's detail"""
        dept = _get_or_create_dept(db_session, "TECH", "技术部")
        other_emp = Employee(employee_no="EMP002", name="其他员工", department_id=dept.id)
        db_session.add(other_emp)
        db_session.flush()

        cycle = AssessmentCycle(
            name="测试周期", type="季度",
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            status="published",
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id, employee_id=other_emp.id,
            department_id=dept.id,
            status="published",
        )
        db_session.add(record)
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "emp001", "password": "Emp001@123"})
        token = resp.json()["access_token"]

        resp = client.get(
            f"/scores/records/{record.id}/detail",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403

    def test_manager_can_view_subordinate_detail(self, client: TestClient, manager_user, employee_user, db_session: Session):
        """Manager should be able to view subordinate's assessment detail"""
        dept = _get_or_create_dept(db_session, "TECH", "技术部")
        pos = db_session.query(Position).filter(Position.name == "Java工程师", Position.department_id == dept.id).first()
        if not pos:
            pos = Position(name="Java工程师", department_id=dept.id)
            db_session.add(pos)
            db_session.flush()

        mgr_emp = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        mgr_emp.department_id = dept.id

        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        emp.department_id = dept.id
        emp.position_id = pos.id
        emp.manager_id = mgr_emp.id
        db_session.commit()

        cycle = AssessmentCycle(
            name="测试周期", type="季度",
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            status="published",
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id, employee_id=emp.id,
            department_id=dept.id, position_id=pos.id,
            status="published",
        )
        db_session.add(record)
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "mgr001", "password": "Mgr001@123"})
        token = resp.json()["access_token"]

        resp = client.get(
            f"/scores/records/{record.id}/detail",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["record_id"] == record.id

    def test_manager_cannot_view_other_employee_detail(self, client: TestClient, manager_user, db_session: Session):
        """Manager should not be able to view non-subordinate's detail"""
        dept = _get_or_create_dept(db_session, "TECH", "技术部")
        other_emp = Employee(employee_no="EMP002", name="其他员工", department_id=dept.id)
        db_session.add(other_emp)
        db_session.flush()

        cycle = AssessmentCycle(
            name="测试周期", type="季度",
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            status="published",
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id, employee_id=other_emp.id,
            department_id=dept.id,
            status="published",
        )
        db_session.add(record)
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "mgr001", "password": "Mgr001@123"})
        token = resp.json()["access_token"]

        resp = client.get(
            f"/scores/records/{record.id}/detail",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403

    def test_detail_includes_appeal_and_interview(self, client: TestClient, employee_user, db_session: Session):
        """Detail should include appeal and interview records if present"""
        dept = _get_or_create_dept(db_session, "TECH", "技术部")
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        emp.department_id = dept.id
        db_session.commit()

        cycle = AssessmentCycle(
            name="测试周期", type="季度",
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            status="published",
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id, employee_id=emp.id,
            department_id=dept.id,
            status="published",
        )
        db_session.add(record)
        db_session.flush()

        appeal = AppealRecord(
            record_id=record.id,
            employee_id=emp.id,
            reason="对评分有异议",
            detail="我认为我的业绩分应该更高",
            status="approved",
            review_result="经复核，维持原评分",
        )
        db_session.add(appeal)
        db_session.flush()

        interview = InterviewRecord(
            record_id=record.id,
            interviewer_id=emp.id,
            content="本年度绩效面谈",
            improvement_plan="提升技术能力",
        )
        db_session.add(interview)
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "emp001", "password": "Emp001@123"})
        token = resp.json()["access_token"]

        resp = client.get(
            f"/scores/records/{record.id}/detail",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["appeal"] is not None
        assert data["appeal"]["reason"] == "对评分有异议"
        assert data["appeal"]["status"] == "approved"
        assert data["interview"] is not None
        assert data["interview"]["content"] == "本年度绩效面谈"
        assert data["interview"]["improvement_plan"] == "提升技术能力"

    def test_admin_can_view_any_detail(self, client: TestClient, admin_user, db_session: Session):
        """Admin should be able to view any employee's assessment detail"""
        dept = _get_or_create_dept(db_session, "TECH", "技术部")
        other_emp = Employee(employee_no="EMP002", name="其他员工", department_id=dept.id)
        db_session.add(other_emp)
        db_session.flush()

        cycle = AssessmentCycle(
            name="测试周期", type="季度",
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            status="published",
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id, employee_id=other_emp.id,
            department_id=dept.id,
            status="published",
        )
        db_session.add(record)
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
        token = resp.json()["access_token"]

        resp = client.get(
            f"/scores/records/{record.id}/detail",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200

    def test_pdf_export_employee_own_record(self, client: TestClient, employee_user, db_session: Session):
        """Employee should be able to download PDF of their own record"""
        dept = _get_or_create_dept(db_session, "TECH", "技术部")
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        emp.department_id = dept.id
        db_session.commit()

        cycle = AssessmentCycle(
            name="测试周期", type="季度",
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            status="published",
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id, employee_id=emp.id,
            department_id=dept.id,
            status="published",
        )
        db_session.add(record)
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "emp001", "password": "Emp001@123"})
        token = resp.json()["access_token"]

        resp = client.get(
            f"/reports/record/{record.id}/pdf",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"

    def test_pdf_export_employee_other_record_forbidden(self, client: TestClient, employee_user, db_session: Session):
        """Employee should not be able to download PDF of another employee's record"""
        dept = _get_or_create_dept(db_session, "TECH", "技术部")
        other_emp = Employee(employee_no="EMP002", name="其他员工", department_id=dept.id)
        db_session.add(other_emp)
        db_session.flush()

        cycle = AssessmentCycle(
            name="测试周期", type="季度",
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            status="published",
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id, employee_id=other_emp.id,
            department_id=dept.id,
            status="published",
        )
        db_session.add(record)
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "emp001", "password": "Emp001@123"})
        token = resp.json()["access_token"]

        resp = client.get(
            f"/reports/record/{record.id}/pdf",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403
