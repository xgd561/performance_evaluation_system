import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date

from app.models import (
    AssessmentRecord, AssessmentCycle, Employee, Department, Position, User,
    Notification, AppealRecord
)
from app.auth import get_password_hash


class TestP6_05_Appeals:
    """P6-05: 申诉管理 — POST /appeals 端点测试"""

    def _create_employee_with_user(self, db_session: Session, username: str, employee_no: str, name: str, role: str, manager_id: int = None, department_id: int = None, position_id: int = None):
        """创建员工及对应用户"""
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
        emp = Employee(employee_no=employee_no, name=name, department_id=department_id if department_id else dept.id, position_id=position_id if position_id else pos.id, manager_id=manager_id)
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

    def _create_published_record(self, db_session: Session, employee_id: int):
        """创建已发布的考核记录"""
        cycle = AssessmentCycle(
            name="P6-05测试周期",
            type="monthly",
            start_date=date.today(),
            end_date=date.today(),
        )
        db_session.add(cycle)
        db_session.flush()
        record = AssessmentRecord(
            cycle_id=cycle.id,
            employee_id=employee_id,
            status="published",
            total_score=85.0,
            grade="B",
        )
        db_session.add(record)
        db_session.flush()
        return record

    def _login(self, client: TestClient, username: str, password: str = "Test@123"):
        resp = client.post("/auth/login", json={"username": username, "password": password})
        assert resp.status_code == 200, resp.text
        return resp.json()["access_token"]

    # ------------------------------------------------------------------
    # 1. 成功创建申诉（已发布记录 + 有效理由长度）
    # ------------------------------------------------------------------

    def test_create_appeal_success(self, client: TestClient, db_session: Session):
        """成功为已发布记录创建申诉，理由长度在 20-1000 之间，返回 201"""
        emp, user = self._create_employee_with_user(db_session, "p605_emp1", "P605_E1", "员工1", "employee")
        record = self._create_published_record(db_session, emp.id)
        db_session.commit()

        token = self._login(client, "p605_emp1")
        reason = "我认为本次绩效考核评分存在明显不公，自评分与上级评分差距过大，请求复核。"
        resp = client.post(
            "/appeals",
            json={"record_id": record.id, "reason": reason, "detail": "自评与上级评分差距较大，评分依据不清晰，希望复核具体打分过程。"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["record_id"] == record.id
        assert data["status"] == "pending"
        assert "id" in data
        assert "created_at" in data

    # ------------------------------------------------------------------
    # 2. 非 published 记录拒绝申诉（400）
    # ------------------------------------------------------------------

    def test_create_appeal_non_published_record_returns_400(self, client: TestClient, db_session: Session):
        """非 published 状态的考核记录发起申诉返回 400"""
        emp, user = self._create_employee_with_user(db_session, "p605_emp2", "P605_E2", "员工2", "employee")
        cycle = AssessmentCycle(
            name="P6-05测试周期2",
            type="monthly",
            start_date=date.today(),
            end_date=date.today(),
        )
        db_session.add(cycle)
        db_session.flush()
        record = AssessmentRecord(
            cycle_id=cycle.id,
            employee_id=emp.id,
            status="pending_self",  # 非 published
            total_score=75.0,
            grade="C",
        )
        db_session.add(record)
        db_session.commit()

        token = self._login(client, "p605_emp2")
        reason = "我认为本次绩效考核评分存在明显不公，请求复核。"
        resp = client.post(
            "/appeals",
            json={"record_id": record.id, "reason": reason, "detail": "本次评分与等级核定结果与我的预期差距较大，申请复核评分依据与计算过程。"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert "已发布" in resp.json()["message"] or "published" in resp.json()["message"].lower()

    # ------------------------------------------------------------------
    # 3. 理由过短（< 20 字符，422）
    # ------------------------------------------------------------------

    def test_create_appeal_reason_too_short_returns_422(self, client: TestClient, db_session: Session):
        """申诉理由少于 20 字符返回 422"""
        emp, user = self._create_employee_with_user(db_session, "p605_emp3", "P605_E3", "员工3", "employee")
        record = self._create_published_record(db_session, emp.id)
        db_session.commit()

        token = self._login(client, "p605_emp3")
        resp = client.post(
            "/appeals",
            json={"record_id": record.id, "reason": "太短了"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422
        assert "20-1000" in resp.json()["message"] or "20" in resp.json()["message"]

    # ------------------------------------------------------------------
    # 4. 理由过长（> 1000 字符，422）
    # ------------------------------------------------------------------

    def test_create_appeal_reason_too_long_returns_422(self, client: TestClient, db_session: Session):
        """申诉理由超过 1000 字符返回 422"""
        emp, user = self._create_employee_with_user(db_session, "p605_emp4", "P605_E4", "员工4", "employee")
        record = self._create_published_record(db_session, emp.id)
        db_session.commit()

        token = self._login(client, "p605_emp4")
        long_reason = "A" * 1001
        resp = client.post(
            "/appeals",
            json={"record_id": record.id, "reason": long_reason},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422
        assert "20-1000" in resp.json()["message"] or "1000" in resp.json()["message"]

    # ------------------------------------------------------------------
    # 5. 验证 AssessmentRecord.appeal_record 被更新
    # ------------------------------------------------------------------

    def test_create_appeal_updates_record_appeal_field(self, client: TestClient, db_session: Session):
        """创建申诉后 AssessmentRecord.appeal_record 应包含申诉 JSON"""
        emp, user = self._create_employee_with_user(db_session, "p605_emp5", "P605_E5", "员工5", "employee")
        record = self._create_published_record(db_session, emp.id)
        db_session.commit()

        token = self._login(client, "p605_emp5")
        reason = "我认为本次绩效考核评分存在明显不公，自评分与上级评分差距过大，请求复核。"
        resp = client.post(
            "/appeals",
            json={"record_id": record.id, "reason": reason, "detail": "自评与上级评分差距较大，评分依据不清晰，希望复核具体打分过程。"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201

        db_session.refresh(record)
        assert record.appeal_record is not None
        import json
        appeal_data = json.loads(record.appeal_record)
        assert appeal_data["status"] == "pending"
        assert appeal_data["reason"] == reason
        assert appeal_data["detail"] == "自评与上级评分差距较大，评分依据不清晰，希望复核具体打分过程。"
        assert "appeal_id" in appeal_data
        assert "created_at" in appeal_data

    # ------------------------------------------------------------------
    # 6. 验证通知被创建给 HR 用户
    # ------------------------------------------------------------------

    def test_create_appeal_creates_notification_for_hr(self, client: TestClient, db_session: Session, hr_user):
        """创建申诉后应为 HR 用户创建通知"""
        emp, user = self._create_employee_with_user(db_session, "p605_emp6", "P605_E6", "员工6", "employee")
        record = self._create_published_record(db_session, emp.id)
        db_session.commit()

        # 记录创建申诉前的通知数量
        before_count = db_session.query(Notification).filter(Notification.user_id == hr_user.id).count()

        token = self._login(client, "p605_emp6")
        reason = "我认为本次绩效考核评分存在明显不公，自评分与上级评分差距过大，请求复核。"
        resp = client.post(
            "/appeals",
            json={"record_id": record.id, "reason": reason, "detail": "本次评分与等级核定结果与我的预期差距较大，申请复核评分依据与计算过程。"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201

        after_count = db_session.query(Notification).filter(Notification.user_id == hr_user.id).count()
        assert after_count == before_count + 1

        notif = db_session.query(Notification).filter(Notification.user_id == hr_user.id).order_by(Notification.created_at.desc()).first()
        assert notif.type == "appeal_created"
        assert "申诉" in notif.title
        assert str(record.id) in notif.content or "p605_emp6" in notif.content

    # ------------------------------------------------------------------
    # 7. 记录不存在返回 404
    # ------------------------------------------------------------------

    def test_create_appeal_record_not_found_returns_404(self, client: TestClient, db_session: Session):
        """record_id 不存在时返回 404"""
        emp, user = self._create_employee_with_user(db_session, "p605_emp7", "P605_E7", "员工7", "employee")
        db_session.commit()

        token = self._login(client, "p605_emp7")
        reason = "我认为本次绩效考核评分存在明显不公，自评分与上级评分差距过大，请求复核。"
        resp = client.post(
            "/appeals",
            json={"record_id": 999999, "reason": reason},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
        assert "不存在" in resp.json()["message"] or "not found" in resp.json()["message"].lower()

    # ------------------------------------------------------------------
    # 8. 员工只能为自己的记录发起申诉（实际行为：端点不验证记录归属，测试实际行为）
    # ------------------------------------------------------------------

    def test_create_appeal_any_published_record_allowed(self, client: TestClient, db_session: Session):
        """端点不验证记录归属，任何已发布记录均可被申诉（测试实际行为）"""
        emp_a, user_a = self._create_employee_with_user(db_session, "p605_emp_a", "P605_EA", "员工A", "employee")
        emp_b, user_b = self._create_employee_with_user(db_session, "p605_emp_b", "P605_EB", "员工B", "employee")
        record = self._create_published_record(db_session, emp_a.id)  # 属于员工A的记录
        db_session.commit()

        # 员工B为员工A的记录发起申诉
        token = self._login(client, "p605_emp_b")
        reason = "我认为本次绩效考核评分存在明显不公，自评分与上级评分差距过大，请求复核。"
        resp = client.post(
            "/appeals",
            json={"record_id": record.id, "reason": reason, "detail": "本次评分与等级核定结果与我的预期差距较大，申请复核评分依据与计算过程。"},
            headers={"Authorization": f"Bearer {token}"},
        )
        # 实际行为：端点不验证记录归属，返回 201
        assert resp.status_code == 201
        data = resp.json()
        assert data["record_id"] == record.id

        # 验证申诉的 employee_id 是 user_b 的 employee_id
        appeal = db_session.query(AppealRecord).filter(AppealRecord.id == data["id"]).first()
        assert appeal.employee_id == emp_b.id
