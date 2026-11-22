import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Employee, Department, Position, AssessmentRecord, AssessmentCycle
from app.services.distribution_enforcer import enforce_distribution
from datetime import date


class TestDistributionEnforcer:
    """Tests for forced distribution algorithm"""

    def test_distribution_downgrades_overflow(self, db_session: Session):
        """When A grade exceeds limit, lowest A scorers should be downgraded"""
        # Create 10 employees in same department
        dept = Department(name="技术部", code="TECH")
        db_session.add(dept)
        db_session.flush()

        employees = []
        for i in range(10):
            emp = Employee(employee_no=f"EMP{i:03d}", name=f"员工{i}", department_id=dept.id)
            db_session.add(emp)
            db_session.flush()
            employees.append(emp)

        cycle = AssessmentCycle(
            name="测试周期", type="季度",
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            status="pending_summary",
        )
        db_session.add(cycle)
        db_session.flush()

        # Create records with scores: 3 A's (95, 94, 93), 5 B's, 2 C's
        scores = [95, 94, 93, 88, 87, 86, 85, 84, 75, 70]
        records = []
        for i, emp in enumerate(employees):
            record = AssessmentRecord(
                cycle_id=cycle.id, employee_id=emp.id,
                department_id=dept.id, total_score=scores[i],
                status="pending_summary",
            )
            db_session.add(record)
            records.append(record)
        db_session.commit()

        grade_rules = {
            "A": {"min": 90, "max": 100, "ratio_limit": 0.2},
            "B": {"min": 80, "max": 89.9, "ratio_limit": 0.5},
            "C": {"min": 60, "max": 79.9, "ratio_limit": 0.25},
            "D": {"min": 0, "max": 59.9, "ratio_limit": 0.05},
        }

        result = enforce_distribution(records, grade_rules, 10, small_dept_exemption=True)

        # A_max = floor(10 * 0.2) = 2
        # So the lowest A (93) should be downgraded to B
        # Note: chain reaction may cause B->C and C->D; D may also overflow in edge cases
        final_counts = result["final_counts"]
        assert final_counts.get("A", 0) <= 2
        assert final_counts.get("B", 0) <= 5

        # Check adjustment log
        assert len(result["adjustment_log"]) >= 1
        # The 93 score should be in adjustment log (from A to B)
        adj_93 = [log for log in result["adjustment_log"] if log["total_score"] == 93]
        assert len(adj_93) == 1
        assert adj_93[0]["from_grade"] == "A"
        assert adj_93[0]["to_grade"] == "B"

    def test_small_dept_exemption(self, db_session: Session):
        """Small departments (<=5) should have relaxed rules"""
        dept = Department(name="小部", code="SMALL")
        db_session.add(dept)
        db_session.flush()

        employees = []
        for i in range(3):
            emp = Employee(employee_no=f"S{i:03d}", name=f"小员工{i}", department_id=dept.id)
            db_session.add(emp)
            db_session.flush()
            employees.append(emp)

        cycle = AssessmentCycle(
            name="测试周期", type="季度",
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            status="pending_summary",
        )
        db_session.add(cycle)
        db_session.flush()

        scores = [95, 92, 88]
        records = []
        for i, emp in enumerate(employees):
            record = AssessmentRecord(
                cycle_id=cycle.id, employee_id=emp.id,
                department_id=dept.id, total_score=scores[i],
                status="pending_summary",
            )
            db_session.add(record)
            records.append(record)
        db_session.commit()

        grade_rules = {
            "A": {"min": 90, "max": 100, "ratio_limit": 0.2},
            "B": {"min": 80, "max": 89.9, "ratio_limit": 0.5},
            "C": {"min": 60, "max": 79.9, "ratio_limit": 0.25},
            "D": {"min": 0, "max": 59.9, "ratio_limit": 0.05},
        }

        result = enforce_distribution(records, grade_rules, 3, small_dept_exemption=True)

        # Small dept: A<=1, D<=1, B/C unlimited
        # 3 employees, 2 A's (95, 92) → one should be downgraded
        assert result["is_compliant"] is True
        final_counts = result["final_counts"]
        assert final_counts.get("A", 0) <= 1

    def test_override_candidates(self, db_session: Session):
        """Employees downgraded from A with score >= 90 should be marked as override candidates"""
        dept = Department(name="技术部", code="TECH")
        db_session.add(dept)
        db_session.flush()

        employees = []
        for i in range(10):
            emp = Employee(employee_no=f"EMP{i:03d}", name=f"员工{i}", department_id=dept.id)
            db_session.add(emp)
            db_session.flush()
            employees.append(emp)

        cycle = AssessmentCycle(
            name="测试周期", type="季度",
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            status="pending_summary",
        )
        db_session.add(cycle)
        db_session.flush()

        scores = [95, 94, 93, 88, 87, 86, 85, 84, 75, 70]
        records = []
        for i, emp in enumerate(employees):
            record = AssessmentRecord(
                cycle_id=cycle.id, employee_id=emp.id,
                department_id=dept.id, total_score=scores[i],
                status="pending_summary",
            )
            db_session.add(record)
            records.append(record)
        db_session.commit()

        grade_rules = {
            "A": {"min": 90, "max": 100, "ratio_limit": 0.2},
            "B": {"min": 80, "max": 89.9, "ratio_limit": 0.5},
            "C": {"min": 60, "max": 79.9, "ratio_limit": 0.25},
            "D": {"min": 0, "max": 59.9, "ratio_limit": 0.05},
        }

        result = enforce_distribution(records, grade_rules, 10, small_dept_exemption=True)

        # The 93 score was downgraded from A, and score >= 90
        override_candidates = result["override_candidates"]
        assert len(override_candidates) >= 1
        assert any(c["total_score"] == 93 and c["from_grade"] == "A" for c in override_candidates)

    def test_distribution_api(self, client: TestClient, admin_user, db_session: Session):
        """Test the calculate_scores endpoint triggers distribution"""
        dept = Department(name="技术部", code="TECH")
        db_session.add(dept)
        db_session.flush()

        employees = []
        for i in range(10):
            emp = Employee(employee_no=f"EMP{i:03d}", name=f"员工{i}", department_id=dept.id)
            db_session.add(emp)
            db_session.flush()
            employees.append(emp)

        cycle = AssessmentCycle(
            name="测试周期", type="季度",
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            status="pending_summary",
            is_distribution_enabled=True,
            small_dept_exemption=True,
        )
        db_session.add(cycle)
        db_session.flush()

        scores = [95, 94, 93, 88, 87, 86, 85, 84, 75, 70]
        for i, emp in enumerate(employees):
            record = AssessmentRecord(
                cycle_id=cycle.id, employee_id=emp.id,
                department_id=dept.id,
                self_scores='{"performance": %d, "ability": %d, "attitude": %d}' % (scores[i], scores[i], scores[i]),
                manager_scores='{"performance": %d, "ability": %d, "attitude": %d}' % (scores[i], scores[i], scores[i]),
                status="pending_summary",
            )
            db_session.add(record)
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
        token = resp.json()["access_token"]

        resp = client.post(
            f"/scores/calculate/{cycle.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "adjustment_count" in data
        assert data["adjustment_count"] >= 1

        # Verify distribution adjustments endpoint
        resp = client.get(
            f"/reports/cycle/{cycle.id}/distribution-adjustments",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        adj_data = resp.json()
        assert adj_data["total_adjusted"] >= 1
        assert any(a["original_grade"] == "A" and a["adjusted_grade"] != "A" for a in adj_data["adjustments"])

    def test_distribution_override_api(self, client: TestClient, manager_user, employee_user, hr_user, db_session: Session):
        """Test distribution override request and approval flow"""
        mgr_emp = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        emp.manager_id = mgr_emp.id
        emp.department_id = mgr_emp.department_id
        db_session.commit()

        cycle = AssessmentCycle(
            name="测试周期", type="季度",
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            status="pending_summary",
            is_distribution_enabled=True,
            small_dept_exemption=True,
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id, employee_id=emp.id,
            department_id=dept.id if 'dept' in locals() else mgr_emp.department_id,
            total_score=93,
            grade="B",
            original_grade="A",
            status="pending_summary",
        )
        db_session.add(record)
        db_session.commit()

        # Manager requests override
        resp = client.post("/auth/login", json={"username": "mgr001", "password": "Mgr001@123"})
        token = resp.json()["access_token"]

        resp = client.post(
            f"/approvals/{record.id}/distribution-override",
            params={"reason": "该员工表现优异，应保留A等级"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200

        # HR approves override
        resp = client.post("/auth/login", json={"username": "hr001", "password": "Hr001@123"})
        hr_token = resp.json()["access_token"]

        resp = client.post(
            f"/approvals/distribution-overrides/{record.id}/approve",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["grade"] == "A"

        # Verify record updated
        db_session.refresh(record)
        assert record.is_distribution_override is True
        assert record.grade == "A"


class TestDepartmentDistributionApi:
    """审批工作台底部「部门当前等级分布」接口。"""

    def test_department_distribution_returns_grades(
        self, client: TestClient, admin_user, admin_token, db_session: Session
    ):
        dept = Department(name="分布测试部", code="DIST")
        db_session.add(dept)
        db_session.flush()

        cycle = AssessmentCycle(
            name="分布统计周期", type="季度",
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            status="pending_approval",
            # 数值简写：ratio_limit 应由 A20/B70/C10 默认值补全
            grade_rules={"A": 90, "B": 80, "C": 60, "D": 0},
            small_dept_exemption=False,
        )
        db_session.add(cycle)
        db_session.flush()

        grades = ["A", "A", "A"] + ["B"] * 6 + ["C"]
        for i, grade in enumerate(grades):
            emp = Employee(employee_no=f"DIST{i:03d}", name=f"分布员工{i}", department_id=dept.id)
            db_session.add(emp)
            db_session.flush()
            db_session.add(
                AssessmentRecord(
                    cycle_id=cycle.id,
                    employee_id=emp.id,
                    department_id=dept.id,
                    status="pending_approval",
                    grade=grade,
                    original_grade=grade,
                    total_score=95 - i,
                )
            )
        db_session.commit()

        resp = client.get(
            f"/api/v1/approvals/department-distribution?department_id={dept.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200, resp.text

        data = resp.json()
        assert data["cycle_id"] == cycle.id
        assert data["total"] == 10

        by_grade = {item["grade"]: item for item in data["grades"]}
        assert by_grade["A"]["count"] == 3
        assert by_grade["A"]["ratio"] == 30.0
        # A 上限 int(10 * 0.2) = 2，实际 3 人 → 超限
        assert by_grade["A"]["is_over_limit"] is True
        assert by_grade["B"]["is_over_limit"] is False

    def test_department_distribution_empty_when_no_records(
        self, client: TestClient, admin_user, admin_token, db_session: Session
    ):
        dept = Department(name="空部门分布", code="DIST_EMPTY")
        db_session.add(dept)
        db_session.commit()

        resp = client.get(
            f"/api/v1/approvals/department-distribution?department_id={dept.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["grades"] == []
        assert data["total"] == 0
