import pytest
from fastapi.testclient import TestClient
from datetime import date, timedelta
from app.models import AssessmentCycle, Employee, Department, Position, AssessmentRecord, CycleEmployee


class TestCycleProgressP306:
    """P3-06: 仪表盘进度监控聚合接口测试"""

    def test_progress_returns_completion_rates(self, client: TestClient, admin_token, db_session):
        """进度接口应返回自评、上级评、协作评完成率"""
        cycle = AssessmentCycle(
            name="进度测试周期", type="monthly",
            start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status="pending_self", peer_review_enabled=True
        )
        db_session.add(cycle)
        db_session.flush()
        dept = Department(name="测试部", code="TEST")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()

        # 3 名员工
        emp1 = Employee(employee_no="P301", name="员工A", department_id=dept.id, position_id=pos.id)
        emp2 = Employee(employee_no="P302", name="员工B", department_id=dept.id, position_id=pos.id)
        emp3 = Employee(employee_no="P303", name="员工C", department_id=dept.id, position_id=pos.id)
        db_session.add_all([emp1, emp2, emp3])
        db_session.flush()

        db_session.add_all([
            CycleEmployee(cycle_id=cycle.id, employee_id=emp1.id),
            CycleEmployee(cycle_id=cycle.id, employee_id=emp2.id),
            CycleEmployee(cycle_id=cycle.id, employee_id=emp3.id),
        ])

        # 1 人待自评，1 人待上级评，1 人待协作评
        db_session.add_all([
            AssessmentRecord(cycle_id=cycle.id, employee_id=emp1.id, status="pending_self", department_id=dept.id, position_id=pos.id),
            AssessmentRecord(cycle_id=cycle.id, employee_id=emp2.id, status="pending_manager", department_id=dept.id, position_id=pos.id),
            AssessmentRecord(cycle_id=cycle.id, employee_id=emp3.id, status="pending_peer", department_id=dept.id, position_id=pos.id),
        ])
        db_session.commit()

        resp = client.get(f"/assessment-cycles/{cycle.id}/progress", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()

        assert data["self_completion_rate"] == 66.7  # 2/3 (pending_manager + pending_peer)
        assert data["manager_completion_rate"] == 33.3  # 1/3 (pending_peer)
        assert data["peer_completion_rate"] == 0.0  # 0/3 (no one past pending_peer)
        assert data["total_employees"] == 3
        assert "department_completion" in data
        assert "incomplete_employees" in data

    def test_department_completion_grouped_correctly(self, client: TestClient, admin_token, db_session):
        """各部门完成率应正确分组"""
        cycle = AssessmentCycle(
            name="部门分组周期", type="monthly",
            start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status="pending_self"
        )
        db_session.add(cycle)
        db_session.flush()

        dept1 = Department(name="研发部", code="RD")
        dept2 = Department(name="市场部", code="MK")
        db_session.add_all([dept1, dept2])
        db_session.flush()
        pos1 = Position(name="研发岗", department_id=dept1.id)
        pos2 = Position(name="市场岗", department_id=dept2.id)
        db_session.add_all([pos1, pos2])
        db_session.flush()

        emp1 = Employee(employee_no="D101", name="研发A", department_id=dept1.id, position_id=pos1.id)
        emp2 = Employee(employee_no="D102", name="研发B", department_id=dept1.id, position_id=pos1.id)
        emp3 = Employee(employee_no="D103", name="市场A", department_id=dept2.id, position_id=pos2.id)
        db_session.add_all([emp1, emp2, emp3])
        db_session.flush()

        db_session.add_all([
            CycleEmployee(cycle_id=cycle.id, employee_id=emp1.id),
            CycleEmployee(cycle_id=cycle.id, employee_id=emp2.id),
            CycleEmployee(cycle_id=cycle.id, employee_id=emp3.id),
        ])

        db_session.add_all([
            AssessmentRecord(cycle_id=cycle.id, employee_id=emp1.id, status="pending_manager", department_id=dept1.id, position_id=pos1.id),
            AssessmentRecord(cycle_id=cycle.id, employee_id=emp2.id, status="pending_self", department_id=dept1.id, position_id=pos1.id),
            AssessmentRecord(cycle_id=cycle.id, employee_id=emp3.id, status="pending_manager", department_id=dept2.id, position_id=pos2.id),
        ])
        db_session.commit()

        resp = client.get(f"/assessment-cycles/{cycle.id}/progress", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()

        dept_map = {d["department_name"]: d for d in data["department_completion"]}
        assert "研发部" in dept_map
        assert "市场部" in dept_map
        assert dept_map["研发部"]["total"] == 2
        assert dept_map["研发部"]["completed"] == 1
        assert dept_map["研发部"]["rate"] == 50.0
        assert dept_map["市场部"]["total"] == 1
        assert dept_map["市场部"]["completed"] == 1
        assert dept_map["市场部"]["rate"] == 100.0

    def test_incomplete_employees_list(self, client: TestClient, admin_token, db_session):
        """未完成人员名单应包含当前阶段信息"""
        cycle = AssessmentCycle(
            name="未完成名单周期", type="monthly",
            start_date=date.today(), end_date=date.today() + timedelta(days=30),
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

        emp1 = Employee(employee_no="IN001", name="已完成", department_id=dept.id, position_id=pos.id)
        emp2 = Employee(employee_no="IN002", name="未完成", department_id=dept.id, position_id=pos.id)
        db_session.add_all([emp1, emp2])
        db_session.flush()

        db_session.add_all([
            CycleEmployee(cycle_id=cycle.id, employee_id=emp1.id),
            CycleEmployee(cycle_id=cycle.id, employee_id=emp2.id),
        ])

        db_session.add_all([
            AssessmentRecord(cycle_id=cycle.id, employee_id=emp1.id, status="pending_manager", department_id=dept.id, position_id=pos.id),
            AssessmentRecord(cycle_id=cycle.id, employee_id=emp2.id, status="pending_self", department_id=dept.id, position_id=pos.id),
        ])
        db_session.commit()

        resp = client.get(f"/assessment-cycles/{cycle.id}/progress", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()

        incomplete = data["incomplete_employees"]
        assert len(incomplete) == 2
        names = {e["employee_name"] for e in incomplete}
        assert "已完成" in names
        assert "未完成" in names
        # emp2 处于自评阶段
        emp2_data = next(e for e in incomplete if e["employee_name"] == "未完成")
        assert emp2_data["current_stage"] == "自评"
        assert emp2_data["status"] == "pending_self"

    def test_progress_large_scale_rates(self, client: TestClient, admin_token, db_session):
        """大规模数据：28 人参与，10 人已自评，自评完成率 35.7%"""
        cycle = AssessmentCycle(
            name="大规模周期", type="monthly",
            start_date=date.today(), end_date=date.today() + timedelta(days=30),
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

        emps = []
        for i in range(28):
            emp = Employee(
                employee_no=f"LARGE{i:03d}",
                name=f"员工{i}",
                department_id=dept.id,
                position_id=pos.id
            )
            db_session.add(emp)
            emps.append(emp)
        db_session.flush()

        for emp in emps:
            db_session.add(CycleEmployee(cycle_id=cycle.id, employee_id=emp.id))

        for i, emp in enumerate(emps):
            status = "pending_manager" if i < 10 else "pending_self"
            db_session.add(AssessmentRecord(
                cycle_id=cycle.id, employee_id=emp.id,
                status=status, department_id=dept.id, position_id=pos.id
            ))
        db_session.commit()

        resp = client.get(f"/assessment-cycles/{cycle.id}/progress", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_employees"] == 28
        assert data["self_completion_rate"] == 35.7
        assert data["manager_completion_rate"] == 0.0
        assert data["peer_completion_rate"] == 0.0
        assert len(data["incomplete_employees"]) == 28

    def test_progress_peer_disabled(self, client: TestClient, admin_token, db_session):
        """协作评关闭时协作评完成率应为 100%"""
        cycle = AssessmentCycle(
            name="无协作评周期", type="monthly",
            start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status="pending_self", peer_review_enabled=False
        )
        db_session.add(cycle)
        db_session.flush()
        dept = Department(name="测试部", code="TEST")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="NP001", name="员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()

        db_session.add(CycleEmployee(cycle_id=cycle.id, employee_id=emp.id))
        db_session.add(AssessmentRecord(cycle_id=cycle.id, employee_id=emp.id, status="pending_self", department_id=dept.id, position_id=pos.id))
        db_session.commit()

        resp = client.get(f"/assessment-cycles/{cycle.id}/progress", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["peer_completion_rate"] == 100.0

    def test_progress_not_found(self, client: TestClient, admin_token):
        resp = client.get("/assessment-cycles/99999/progress", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404
