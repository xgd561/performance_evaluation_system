import pytest
import json
from fastapi.testclient import TestClient
from datetime import date, timedelta
from app.models import AssessmentCycle, Employee, Department, Position, User, Notification, KpiTemplate, AssessmentRecord
from app.auth import get_password_hash
import json


class TestCycleStart:
    """P3-05: Tests for POST /assessment-cycles/{cycle_id}/start"""

    def test_start_cycle_success(self, client: TestClient, admin_token, db_session):
        """正常启动考核周期应创建记录并发送通知"""
        cycle = AssessmentCycle(
            name="启动周期", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30),
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
        emp = Employee(employee_no="START001", name="员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
        user = User(username="start001", password_hash=get_password_hash("Start001@"), role="employee", employee_id=emp.id)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(cycle)
        db_session.refresh(emp)

        payload = {"cycle_id": cycle.id, "employee_ids": [emp.id]}
        resp = client.post(f"/assessment-cycles/{cycle.id}/start", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["created_records"] == 1
        assert data["status"] == "进行中（自评）"

        # 验证通知已创建
        notif = db_session.query(Notification).filter(Notification.user_id == user.id).first()
        assert notif is not None
        assert "启动周期" in notif.title

    def test_start_cycle_not_found(self, client: TestClient, admin_token):
        payload = {"cycle_id": 99999, "employee_ids": [1]}
        resp = client.post("/assessment-cycles/99999/start", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404

    def test_start_cycle_already_started(self, client: TestClient, admin_token, db_session):
        cycle = AssessmentCycle(
            name="已启动周期", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status="pending_self"
        )
        db_session.add(cycle)
        db_session.commit()
        db_session.refresh(cycle)

        payload = {"cycle_id": cycle.id, "employee_ids": [1]}
        resp = client.post(f"/assessment-cycles/{cycle.id}/start", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 400
        assert "不允许执行动作" in resp.json()["message"]

    def test_start_cycle_no_employees(self, client: TestClient, admin_token, db_session):
        cycle = AssessmentCycle(
            name="空周期", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status="not_started"
        )
        db_session.add(cycle)
        db_session.commit()
        db_session.refresh(cycle)

        payload = {"cycle_id": cycle.id, "employee_ids": []}
        resp = client.post(f"/assessment-cycles/{cycle.id}/start", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 409
        assert "至少选择一名员工" in resp.json()["message"]

    def test_start_cycle_invalid_employee(self, client: TestClient, admin_token, db_session):
        cycle = AssessmentCycle(
            name="无效员工", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status="not_started"
        )
        db_session.add(cycle)
        db_session.commit()
        db_session.refresh(cycle)

        payload = {"cycle_id": cycle.id, "employee_ids": [99999]}
        resp = client.post(f"/assessment-cycles/{cycle.id}/start", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422

    def test_start_cycle_notification_without_user(self, client: TestClient, admin_token, db_session):
        """员工没有对应用户账号时不应报错，只是不创建通知"""
        cycle = AssessmentCycle(
            name="无用户周期", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30),
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
        emp = Employee(employee_no="NOUSER001", name="员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.commit()
        db_session.refresh(cycle)
        db_session.refresh(emp)

        payload = {"cycle_id": cycle.id, "employee_ids": [emp.id]}
        resp = client.post(f"/assessment-cycles/{cycle.id}/start", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["created_records"] == 1

    def test_start_cycle_kpi_snapshot(self, client: TestClient, admin_token, db_session):
        """启动考核时应根据岗位 KPI 模板生成快照"""
        cycle = AssessmentCycle(
            name="KPI快照周期", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30),
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
        emp = Employee(employee_no="KPI001", name="员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
        user = User(username="kpi001", password_hash=get_password_hash("Kpi001@"), role="employee", employee_id=emp.id)
        db_session.add(user)

        # 创建 KPI 模板
        kpi1 = KpiTemplate(name="销售额", weight=50, target_value="100万", position_id=pos.id, is_active=True)
        kpi2 = KpiTemplate(name="客户满意度", weight=50, target_value="90分", position_id=pos.id, is_active=True)
        db_session.add(kpi1)
        db_session.add(kpi2)
        db_session.commit()
        db_session.refresh(cycle)
        db_session.refresh(emp)

        payload = {"cycle_id": cycle.id, "employee_ids": [emp.id]}
        resp = client.post(f"/assessment-cycles/{cycle.id}/start", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200

        record = db_session.query(AssessmentRecord).filter(
            AssessmentRecord.cycle_id == cycle.id,
            AssessmentRecord.employee_id == emp.id,
        ).first()
        assert record is not None
        assert record.kpi_snapshot is not None
        snapshot = record.kpi_snapshot
        if isinstance(snapshot, str):
            snapshot = json.loads(snapshot)
        assert isinstance(snapshot, list)
        assert len(snapshot) == 2
        names = {item["name"] for item in snapshot}
        assert "销售额" in names
        assert "客户满意度" in names

    def test_start_cycle_no_kpi_templates(self, client: TestClient, admin_token, db_session):
        """员工岗位无 KPI 模板时，kpi_snapshot 应为 None"""
        cycle = AssessmentCycle(
            name="无KPI周期", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status="not_started"
        )
        db_session.add(cycle)
        db_session.flush()
        dept = Department(name="测试部", code="TEST")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="空岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="NOKPI001", name="员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
        user = User(username="nokpi001", password_hash=get_password_hash("Nokpi001@"), role="employee", employee_id=emp.id)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(cycle)
        db_session.refresh(emp)

        payload = {"cycle_id": cycle.id, "employee_ids": [emp.id]}
        resp = client.post(f"/assessment-cycles/{cycle.id}/start", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200

        record = db_session.query(AssessmentRecord).filter(
            AssessmentRecord.cycle_id == cycle.id,
            AssessmentRecord.employee_id == emp.id,
        ).first()
        assert record is not None
        assert record.kpi_snapshot is None
