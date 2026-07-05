import pytest
from fastapi.testclient import TestClient
from datetime import date, timedelta
from app.models import AssessmentCycle, Employee, Department, Position, User, Notification
from app.auth import get_password_hash
from app.utils.workflow_state_machine import WorkflowStateMachine
from app.core.exceptions import BizError


class TestWorkflowStateMachineUnit:
    """P3-10: 状态机单元测试"""

    def test_start_cycle_from_not_started(self):
        """从 not_started 执行 start_cycle 应返回 pending_self"""
        next_state = WorkflowStateMachine.transition(
            current_state="not_started",
            action="start_cycle",
        )
        assert next_state == "pending_self"

    def test_start_cycle_from_pending_self_raises(self):
        """从 pending_self 执行 start_cycle 应抛出 BizError"""
        with pytest.raises(BizError) as exc_info:
            WorkflowStateMachine.transition(
                current_state="pending_self",
                action="start_cycle",
            )
        assert exc_info.value.code == 1101
        assert "不允许执行动作" in exc_info.value.message

    def test_start_cycle_from_archived_raises(self):
        """从 archived 执行 start_cycle 应抛出 BizError"""
        with pytest.raises(BizError) as exc_info:
            WorkflowStateMachine.transition(
                current_state="archived",
                action="start_cycle",
            )
        assert exc_info.value.code == 1101

    def test_invalid_state_raises(self):
        """未知状态应抛出 BizError(code=1100)"""
        with pytest.raises(BizError) as exc_info:
            WorkflowStateMachine.transition(
                current_state="unknown_state",
                action="start_cycle",
            )
        assert exc_info.value.code == 1100
        assert "未知状态" in exc_info.value.message

    def test_is_valid_transition(self):
        """is_valid_transition 应正确判断"""
        assert WorkflowStateMachine.is_valid_transition("not_started", "start_cycle") is True
        assert WorkflowStateMachine.is_valid_transition("pending_self", "start_cycle") is False
        assert WorkflowStateMachine.is_valid_transition("not_started", "submit_self") is False

    def test_get_allowed_actions(self):
        """get_allowed_actions 应返回当前状态允许的动作"""
        assert "start_cycle" in WorkflowStateMachine.get_allowed_actions("not_started")
        assert "submit_self" in WorkflowStateMachine.get_allowed_actions("pending_self")
        assert WorkflowStateMachine.get_allowed_actions("archived") == []

    def test_register_validator(self):
        """register_validator 应注册并执行自定义校验"""
        def dummy_validator(current_state, action, **kwargs):
            raise BizError(message="自定义校验失败", code=9999)

        WorkflowStateMachine.register_validator("not_started", "start_cycle", dummy_validator)
        try:
            with pytest.raises(BizError) as exc_info:
                WorkflowStateMachine.transition(
                    current_state="not_started",
                    action="start_cycle",
                )
            assert exc_info.value.code == 9999
            assert "自定义校验失败" in exc_info.value.message
        finally:
            WorkflowStateMachine.reset_validators()

    def test_reset_validators(self):
        """reset_validators 应清空所有已注册校验器"""
        def dummy_validator(current_state, action, **kwargs):
            raise BizError(message="fail", code=9999)

        WorkflowStateMachine.register_validator("not_started", "start_cycle", dummy_validator)
        WorkflowStateMachine.reset_validators()
        # 不应再抛出异常
        next_state = WorkflowStateMachine.transition(
            current_state="not_started",
            action="start_cycle",
        )
        assert next_state == "pending_self"


class TestWorkflowStateMachineIntegration:
    """P3-10: 状态机与启动端点集成测试"""

    def test_start_cycle_uses_state_machine(self, client: TestClient, admin_token, db_session):
        """start_cycle 端点应通过状态机完成状态转换"""
        cycle = AssessmentCycle(
            name="状态机测试周期", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30),
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
        emp = Employee(employee_no="SM001", name="员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
        user = User(username="sm001", password_hash=get_password_hash("Sm001@"), role="employee", employee_id=emp.id)
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

        # 验证状态已更新
        db_session.refresh(cycle)
        assert cycle.status == "pending_self"

    def test_start_cycle_rejected_by_state_machine(self, client: TestClient, admin_token, db_session):
        """状态机应拒绝非法状态转换"""
        cycle = AssessmentCycle(
            name="非法启动周期", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status="pending_manager"
        )
        db_session.add(cycle)
        db_session.commit()
        db_session.refresh(cycle)

        payload = {"cycle_id": cycle.id, "employee_ids": [1]}
        resp = client.post(f"/assessment-cycles/{cycle.id}/start", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 400
        assert resp.json()["code"] == 1101
        assert "不允许执行动作" in resp.json()["message"]

    def test_start_cycle_from_archived(self, client: TestClient, admin_token, db_session):
        """从 archived 状态启动应被状态机拒绝"""
        cycle = AssessmentCycle(
            name="归档周期", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30),
            status="archived"
        )
        db_session.add(cycle)
        db_session.commit()
        db_session.refresh(cycle)

        payload = {"cycle_id": cycle.id, "employee_ids": [1]}
        resp = client.post(f"/assessment-cycles/{cycle.id}/start", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 400
        assert resp.json()["code"] == 1101
