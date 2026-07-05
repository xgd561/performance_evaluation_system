import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.models import (
    AssessmentRecord, AssessmentCycle, Employee, Department, Position, User, ApprovalRecord
)


def _create_cycle(db_session: Session, name: str = "高管测试周期", status: str = "published",
                  start_date: date = None, end_date: date = None):
    cycle = AssessmentCycle(
        name=name,
        type="quarterly",
        start_date=start_date or date.today() - timedelta(days=90),
        end_date=end_date or date.today(),
        self_due_date=date.today() - timedelta(days=60),
        manager_due_date=date.today() - timedelta(days=30),
        peer_due_date=date.today() - timedelta(days=15),
        status=status,
        dimension_weights='{"performance":0.6,"ability":0.2,"attitude":0.2}',
        reviewer_weights='{"performance":{"self":0.3,"manager":0.7},"ability":{"self":0.2,"manager":0.6,"peer":0.2},"attitude":{"self":0.2,"manager":0.8}}',
        grade_rules='{"A":{"min":90,"max":100,"ratio_limit":0.2},"B":{"min":80,"max":89.9,"ratio_limit":0.5},"C":{"min":60,"max":79.9,"ratio_limit":0.25},"D":{"min":0,"max":59.9,"ratio_limit":0.05}}',
    )
    db_session.add(cycle)
    db_session.commit()
    db_session.refresh(cycle)
    return cycle


def _create_employee(db_session: Session, employee_no: str, name: str, dept_id: int, pos_id: int, grade: str = "B", is_active: bool = True):
    emp = Employee(employee_no=employee_no, name=name, department_id=dept_id, position_id=pos_id, is_active=is_active)
    db_session.add(emp)
    db_session.commit()
    db_session.refresh(emp)
    return emp


def _create_record(db_session: Session, cycle_id: int, employee_id: int, status: str = "published", grade: str = "B", total_score: float = 85.0, is_override: bool = False, override_reason: str = None):
    record = AssessmentRecord(
        cycle_id=cycle_id,
        employee_id=employee_id,
        status=status,
        total_score=total_score,
        grade=grade,
        original_grade=grade,
        is_distribution_override=is_override,
        override_reason=override_reason,
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


class TestExecutiveDashboard:
    """Tests for GET /dashboard/executive"""

    def test_executive_dashboard_success(self, client: TestClient, executive_token, db_session: Session):
        """executive 访问返回正确数据结构"""
        resp = client.get("/dashboard/executive", headers={"Authorization": f"Bearer {executive_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "stats" in data
        assert "grade_distribution" in data
        assert "department_avg" in data
        assert "quarterly_trend" in data
        assert "adjusted_employees" in data
        assert isinstance(data["stats"]["total_employees"], int)
        assert isinstance(data["stats"]["coverage_rate"], float)
        assert isinstance(data["stats"]["avg_total_score"], float)
        assert isinstance(data["stats"]["pending_approvals"], int)

    def test_executive_dashboard_forbidden_employee(self, client: TestClient, employee_token):
        """employee 访问返回 403"""
        resp = client.get("/dashboard/executive", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403

    def test_executive_dashboard_forbidden_manager(self, client: TestClient, manager_token):
        """manager 访问返回 403"""
        resp = client.get("/dashboard/executive", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 403

    def test_executive_dashboard_stats_correct(self, client: TestClient, executive_token, db_session: Session):
        """验证 stats 聚合计算正确"""
        dept = Department(name="高管测试部", code="EXE")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = _create_employee(db_session, "EXE001", "测试员工", dept.id, pos.id)
        cycle = _create_cycle(db_session, status="published")
        _create_record(db_session, cycle.id, emp.id, status="published", grade="B", total_score=85.0)

        resp = client.get("/dashboard/executive", headers={"Authorization": f"Bearer {executive_token}"})
        assert resp.status_code == 200
        data = resp.json()
        stats = data["stats"]
        assert stats["total_employees"] >= 1
        assert stats["coverage_rate"] >= 0.0
        assert stats["avg_total_score"] == 85.0
        assert stats["pending_approvals"] >= 0

    def test_executive_dashboard_grade_distribution(self, client: TestClient, executive_token, db_session: Session):
        """验证 A/B/C/D 分布数据正确"""
        dept = Department(name="分布测试部", code="DIS")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp_a = _create_employee(db_session, "DIS001", "员工A", dept.id, pos.id)
        emp_b = _create_employee(db_session, "DIS002", "员工B", dept.id, pos.id)
        emp_c = _create_employee(db_session, "DIS003", "员工C", dept.id, pos.id)
        cycle = _create_cycle(db_session, name="分布测试周期", status="published")
        _create_record(db_session, cycle.id, emp_a.id, status="published", grade="A", total_score=95.0)
        _create_record(db_session, cycle.id, emp_b.id, status="published", grade="B", total_score=85.0)
        _create_record(db_session, cycle.id, emp_c.id, status="published", grade="C", total_score=70.0)

        resp = client.get("/dashboard/executive", headers={"Authorization": f"Bearer {executive_token}"})
        assert resp.status_code == 200
        dist = resp.json()["grade_distribution"]
        assert dist["A"] >= 1
        assert dist["B"] >= 1
        assert dist["C"] >= 1
        assert dist["D"] >= 0

    def test_executive_dashboard_department_avg(self, client: TestClient, executive_token, db_session: Session):
        """验证部门平均分对比数据"""
        dept1 = Department(name="部门甲", code="D1")
        dept2 = Department(name="部门乙", code="D2")
        db_session.add(dept1)
        db_session.add(dept2)
        db_session.flush()
        pos1 = Position(name="岗1", department_id=dept1.id)
        pos2 = Position(name="岗2", department_id=dept2.id)
        db_session.add(pos1)
        db_session.add(pos2)
        db_session.flush()
        emp1 = _create_employee(db_session, "DA01", "员工甲", dept1.id, pos1.id)
        emp2 = _create_employee(db_session, "DA02", "员工乙", dept2.id, pos2.id)
        cycle = _create_cycle(db_session, name="部门测试周期", status="published")
        _create_record(db_session, cycle.id, emp1.id, status="published", grade="A", total_score=90.0)
        _create_record(db_session, cycle.id, emp2.id, status="published", grade="B", total_score=80.0)

        resp = client.get("/dashboard/executive", headers={"Authorization": f"Bearer {executive_token}"})
        assert resp.status_code == 200
        dept_avg = resp.json()["department_avg"]
        names = [d["name"] for d in dept_avg]
        assert "部门甲" in names
        assert "部门乙" in names
        dept_a = next(d for d in dept_avg if d["name"] == "部门甲")
        dept_b = next(d for d in dept_avg if d["name"] == "部门乙")
        assert dept_a["avg_score"] == 90.0
        assert dept_b["avg_score"] == 80.0

    def test_executive_dashboard_quarterly_trend(self, client: TestClient, executive_token, db_session: Session):
        """验证近 4 季度趋势数据"""
        dept = Department(name="趋势测试部", code="TRD")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = _create_employee(db_session, "TR01", "趋势员工", dept.id, pos.id)
        cycle1 = _create_cycle(db_session, name="Q1周期", status="published",
                               start_date=date.today() - timedelta(days=180), end_date=date.today() - timedelta(days=90))
        cycle2 = _create_cycle(db_session, name="Q2周期", status="published",
                               start_date=date.today() - timedelta(days=90), end_date=date.today())
        _create_record(db_session, cycle1.id, emp.id, status="published", grade="B", total_score=78.0)
        _create_record(db_session, cycle2.id, emp.id, status="published", grade="A", total_score=88.0)

        resp = client.get("/dashboard/executive", headers={"Authorization": f"Bearer {executive_token}"})
        assert resp.status_code == 200
        trend = resp.json()["quarterly_trend"]
        assert len(trend) >= 2
        scores = [t["avg_score"] for t in trend]
        assert 78.0 in scores
        assert 88.0 in scores

    def test_executive_dashboard_adjusted_employees(self, client: TestClient, executive_token, db_session: Session):
        """验证强制调整人员列表"""
        dept = Department(name="调整测试部", code="ADJ")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = _create_employee(db_session, "ADJ01", "被调整员工", dept.id, pos.id)
        cycle = _create_cycle(db_session, name="调整测试周期", status="published")
        _create_record(db_session, cycle.id, emp.id, status="published", grade="B", total_score=85.0,
                       is_override=True, override_reason="强制分布从 A 调整为 B")

        resp = client.get("/dashboard/executive", headers={"Authorization": f"Bearer {executive_token}"})
        assert resp.status_code == 200
        adjusted = resp.json()["adjusted_employees"]
        assert len(adjusted) >= 1
        item = adjusted[0]
        assert item["employee_name"] == "被调整员工"
        assert item["adjusted_grade"] == "B"
        assert "强制分布" in item["override_reason"]
