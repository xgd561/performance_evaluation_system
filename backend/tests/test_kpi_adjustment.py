import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Employee, Department, Position, AssessmentRecord, AssessmentCycle, KpiTemplate, KpiAdjustment
from datetime import date


class TestKpiAdjustment:
    """Tests for KPI adjustment snapshot and approval"""

    def test_request_kpi_adjustment_stores_snapshot(self, client: TestClient, manager_user, employee_user, db_session: Session):
        """KPI adjustment request should store original and adjusted snapshots"""
        dept = db_session.query(Department).filter(Department.code == "TECH").first()
        if not dept:
            dept = Department(name="技术部", code="TECH")
            db_session.add(dept)
            db_session.flush()
        pos = db_session.query(Position).filter(Position.name == "Java工程师").first()
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

        # Create KPI template
        kpi = KpiTemplate(
            position_id=pos.id,
            name="销售额完成率",
            weight=50,
            target_value="100万",
            scoring_method="percentage",
            description="季度销售额目标",
        )
        db_session.add(kpi)
        db_session.flush()

        cycle = AssessmentCycle(
            name="测试周期", type="季度",
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            status="pending_self",
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id, employee_id=emp.id,
            department_id=dept.id, position_id=pos.id,
            kpi_snapshot='[{"name": "销售额完成率", "weight": "50", "target_value": "100万"}]',
            status="pending_self",
        )
        db_session.add(record)
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "mgr001", "password": "Mgr001@123"})
        token = resp.json()["access_token"]

        resp = client.post(
            f"/kpi-templates/{record.id}/adjust",
            json={"kpi_id": kpi.id, "new_target": "120万", "reason": "市场情况变化"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        adj_id = resp.json()["id"]

        # Verify snapshot stored
        adj = db_session.query(KpiAdjustment).filter(KpiAdjustment.id == adj_id).first()
        assert adj is not None
        assert adj.original_kpi is not None
        assert "100万" in adj.original_kpi
        assert adj.adjusted_kpi is not None
        assert "120万" in adj.adjusted_kpi

    def test_approve_kpi_adjustment_updates_snapshot(self, client: TestClient, manager_user, hr_user, employee_user, db_session: Session):
        """Approving KPI adjustment should update the record's kpi_snapshot"""
        dept = db_session.query(Department).filter(Department.code == "TECH").first()
        if not dept:
            dept = Department(name="技术部", code="TECH")
            db_session.add(dept)
            db_session.flush()

        pos = db_session.query(Position).filter(Position.name == "Java工程师").first()
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
            status="pending_self",
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id, employee_id=emp.id,
            department_id=dept.id, position_id=pos.id,
            kpi_snapshot='[{"name": "销售额完成率", "weight": "50", "target_value": "100万"}]',
            status="pending_self",
        )
        db_session.add(record)
        db_session.flush()

        adj = KpiAdjustment(
            record_id=record.id,
            original_kpi=record.kpi_snapshot,
            adjusted_kpi='[{"name": "销售额完成率", "weight": "50", "target_value": "120万"}]',
            reason="市场变化",
            status="pending",
        )
        db_session.add(adj)
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "hr001", "password": "Hr001@123"})
        hr_token = resp.json()["access_token"]

        resp = client.post(
            f"/kpi-templates/kpi-adjustments/{adj.id}/approve",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert resp.status_code == 200

        # Verify record updated
        db_session.refresh(record)
        assert "120万" in record.kpi_snapshot

    def test_reject_kpi_adjustment_keeps_original(self, client: TestClient, hr_user, db_session: Session):
        """Rejecting KPI adjustment should not change the record's kpi_snapshot"""
        adj = KpiAdjustment(
            record_id=1,
            original_kpi='[{"name": "销售额完成率", "weight": "50", "target_value": "100万"}]',
            adjusted_kpi='[{"name": "销售额完成率", "weight": "50", "target_value": "120万"}]',
            reason="测试",
            status="pending",
        )
        db_session.add(adj)
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "hr001", "password": "Hr001@123"})
        hr_token = resp.json()["access_token"]

        resp = client.post(
            f"/kpi-templates/kpi-adjustments/{adj.id}/reject",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert resp.status_code == 200

        adj = db_session.query(KpiAdjustment).filter(KpiAdjustment.id == adj.id).first()
        assert adj.status == "rejected"

    def test_manager_can_list_pending_adjustments_of_subordinate(self, client: TestClient, manager_user, employee_user, db_session: Session):
        """Manager should only see pending adjustments for their subordinates"""
        dept = db_session.query(Department).filter(Department.code == "TECH").first()
        if not dept:
            dept = Department(name="技术部", code="TECH")
            db_session.add(dept)
            db_session.flush()

        pos = db_session.query(Position).filter(Position.name == "Java工程师").first()
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
            status="pending_self",
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id, employee_id=emp.id,
            department_id=dept.id, position_id=pos.id,
            kpi_snapshot='[{"name": "销售额完成率", "weight": "50", "target_value": "100万"}]',
            status="pending_self",
        )
        db_session.add(record)
        db_session.flush()

        adj = KpiAdjustment(
            record_id=record.id,
            original_kpi=record.kpi_snapshot,
            adjusted_kpi='{"kpi_id": 1, "new_target": "120万"}',
            reason="市场变化",
            status="pending",
        )
        db_session.add(adj)
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "mgr001", "password": "Mgr001@123"})
        token = resp.json()["access_token"]

        resp = client.get(
            "/kpi-templates/kpi-adjustments/pending",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["record_id"] == record.id

    def test_manager_cannot_list_pending_adjustments_of_other_manager(self, client: TestClient, manager_user, db_session: Session):
        """Manager should not see pending adjustments for employees not under them"""
        # Create another manager and employee
        dept = db_session.query(Department).filter(Department.code == "TECH").first()
        if not dept:
            dept = Department(name="技术部", code="TECH")
            db_session.add(dept)
            db_session.flush()

        other_mgr = Employee(employee_no="MGR002", name="其他经理", department_id=dept.id)
        db_session.add(other_mgr)
        db_session.flush()

        other_emp = Employee(employee_no="EMP002", name="其他员工", department_id=dept.id, manager_id=other_mgr.id)
        db_session.add(other_emp)
        db_session.flush()

        cycle = AssessmentCycle(
            name="测试周期", type="季度",
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            status="pending_self",
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id, employee_id=other_emp.id,
            department_id=dept.id,
            kpi_snapshot='[{"name": "销售额完成率", "weight": "50", "target_value": "100万"}]',
            status="pending_self",
        )
        db_session.add(record)
        db_session.flush()

        adj = KpiAdjustment(
            record_id=record.id,
            original_kpi=record.kpi_snapshot,
            adjusted_kpi='{"kpi_id": 1, "new_target": "120万"}',
            reason="市场变化",
            status="pending",
        )
        db_session.add(adj)
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "mgr001", "password": "Mgr001@123"})
        token = resp.json()["access_token"]

        resp = client.get(
            "/kpi-templates/kpi-adjustments/pending",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 0

    def test_manager_can_approve_subordinate_adjustment(self, client: TestClient, manager_user, employee_user, db_session: Session):
        """Manager should be able to approve their subordinate's KPI adjustment"""
        dept = db_session.query(Department).filter(Department.code == "TECH").first()
        if not dept:
            dept = Department(name="技术部", code="TECH")
            db_session.add(dept)
            db_session.flush()

        pos = db_session.query(Position).filter(Position.name == "Java工程师").first()
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
            status="pending_self",
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id, employee_id=emp.id,
            department_id=dept.id, position_id=pos.id,
            kpi_snapshot='[{"name": "销售额完成率", "weight": "50", "target_value": "100万"}]',
            status="pending_self",
        )
        db_session.add(record)
        db_session.flush()

        adj = KpiAdjustment(
            record_id=record.id,
            original_kpi=record.kpi_snapshot,
            adjusted_kpi='[{"name": "销售额完成率", "weight": "50", "target_value": "120万"}]',
            reason="市场变化",
            status="pending",
        )
        db_session.add(adj)
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "mgr001", "password": "Mgr001@123"})
        token = resp.json()["access_token"]

        resp = client.post(
            f"/kpi-templates/kpi-adjustments/{adj.id}/approve",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        db_session.refresh(record)
        assert "120万" in record.kpi_snapshot

    def test_manager_cannot_approve_other_manager_adjustment(self, client: TestClient, manager_user, db_session: Session):
        """Manager should not be able to approve another manager's subordinate adjustment"""
        dept = db_session.query(Department).filter(Department.code == "TECH").first()
        if not dept:
            dept = Department(name="技术部", code="TECH")
            db_session.add(dept)
            db_session.flush()

        other_mgr = Employee(employee_no="MGR002", name="其他经理", department_id=dept.id)
        db_session.add(other_mgr)
        db_session.flush()

        other_emp = Employee(employee_no="EMP002", name="其他员工", department_id=dept.id, manager_id=other_mgr.id)
        db_session.add(other_emp)
        db_session.flush()

        cycle = AssessmentCycle(
            name="测试周期", type="季度",
            start_date=date(2026, 1, 1), end_date=date(2026, 3, 31),
            status="pending_self",
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id, employee_id=other_emp.id,
            department_id=dept.id,
            kpi_snapshot='[{"name": "销售额完成率", "weight": "50", "target_value": "100万"}]',
            status="pending_self",
        )
        db_session.add(record)
        db_session.flush()

        adj = KpiAdjustment(
            record_id=record.id,
            original_kpi=record.kpi_snapshot,
            adjusted_kpi='[{"name": "销售额完成率", "weight": "50", "target_value": "120万"}]',
            reason="市场变化",
            status="pending",
        )
        db_session.add(adj)
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "mgr001", "password": "Mgr001@123"})
        token = resp.json()["access_token"]

        resp = client.post(
            f"/kpi-templates/kpi-adjustments/{adj.id}/approve",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403

    def test_manager_can_reject_subordinate_adjustment(self, client: TestClient, manager_user, employee_user, db_session: Session):
        """Manager should be able to reject their subordinate's KPI adjustment"""
        dept = db_session.query(Department).filter(Department.code == "TECH").first()
        if not dept:
            dept = Department(name="技术部", code="TECH")
            db_session.add(dept)
            db_session.flush()

        pos = db_session.query(Position).filter(Position.name == "Java工程师").first()
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
            status="pending_self",
        )
        db_session.add(cycle)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id, employee_id=emp.id,
            department_id=dept.id, position_id=pos.id,
            kpi_snapshot='[{"name": "销售额完成率", "weight": "50", "target_value": "100万"}]',
            status="pending_self",
        )
        db_session.add(record)
        db_session.flush()

        adj = KpiAdjustment(
            record_id=record.id,
            original_kpi=record.kpi_snapshot,
            adjusted_kpi='{"kpi_id": 1, "new_target": "120万"}',
            reason="市场变化",
            status="pending",
        )
        db_session.add(adj)
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "mgr001", "password": "Mgr001@123"})
        token = resp.json()["access_token"]

        resp = client.post(
            f"/kpi-templates/kpi-adjustments/{adj.id}/reject",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200

        adj = db_session.query(KpiAdjustment).filter(KpiAdjustment.id == adj.id).first()
        assert adj.status == "rejected"
