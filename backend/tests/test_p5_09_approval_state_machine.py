import pytest
from app.utils.workflow_state_machine import WorkflowStateMachine
from app.core.exceptions import BizError


class TestP5_09ApprovalStateMachine:
    """P5-09: 审批状态机单元测试——审批相关状态转换"""

    def test_approve_step1_pending_approval_stays_pending_approval(self):
        """1. approve_step1 从 pending_approval → pending_approval"""
        next_state = WorkflowStateMachine.transition(
            current_state="pending_approval",
            action="approve_step1",
        )
        assert next_state == "pending_approval"

    def test_approve_step2_pending_approval_to_pending_interview(self):
        """2. approve_step2 从 pending_approval → pending_interview"""
        next_state = WorkflowStateMachine.transition(
            current_state="pending_approval",
            action="approve_step2",
        )
        assert next_state == "pending_interview"

    def test_reject_pending_approval_stays_pending_approval(self):
        """3. reject 从 pending_approval → pending_approval"""
        next_state = WorkflowStateMachine.transition(
            current_state="pending_approval",
            action="reject",
        )
        assert next_state == "pending_approval"

    def test_rollback_pending_approval_to_pending_manager(self):
        """4. rollback 从 pending_approval → pending_manager"""
        next_state = WorkflowStateMachine.transition(
            current_state="pending_approval",
            action="rollback",
        )
        assert next_state == "pending_manager"

    def test_invalid_action_on_pending_approval_raises_biz_error(self):
        """5. 在 pending_approval 上执行非法动作应抛出 BizError(code=1101)"""
        with pytest.raises(BizError) as exc_info:
            WorkflowStateMachine.transition(
                current_state="pending_approval",
                action="submit_self",
            )
        assert exc_info.value.code == 1101
        assert "不允许执行动作" in exc_info.value.message

    def test_invalid_state_raises_biz_error(self):
        """6. 未知状态转换应抛出 BizError(code=1100)"""
        with pytest.raises(BizError) as exc_info:
            WorkflowStateMachine.transition(
                current_state="invalid_state",
                action="approve_step1",
            )
        assert exc_info.value.code == 1100
        assert "未知状态" in exc_info.value.message

    def test_approve_step1_logs_operation_when_db_and_user_id_provided(self, db_session):
        """7. approve_step1 在传入 db 和 user_id 时记录操作日志"""
        from app.models import OperationLog, User, Employee, Department, Position
        # 先 commit 清空任何未提交状态，避免 transition 内部 flush 触发隐式 rollback
        db_session.commit()

        # 创建一个用户用于测试，避免外键约束失败
        dept = Department(name="测试部", code="TEST_SM")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="SM001", name="测试员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
        user = User(username="sm_user", password_hash="fakehash", role="employee", employee_id=emp.id)
        db_session.add(user)
        db_session.flush()
        db_session.commit()

        next_state = WorkflowStateMachine.transition(
            current_state="pending_approval",
            action="approve_step1",
            db=db_session,
            user_id=user.id,
            target_id=100,
        )
        assert next_state == "pending_approval"
        db_session.commit()

        log = db_session.query(OperationLog).filter(
            OperationLog.user_id == user.id,
            OperationLog.action == "approve_step1",
            OperationLog.target_id == 100,
        ).first()
        assert log is not None
        assert log.target_type == "assessment_record"

    def test_rollback_logs_operation_when_db_and_user_id_provided(self, db_session):
        """8. rollback 在传入 db 和 user_id 时记录操作日志"""
        from app.models import OperationLog, User, Employee, Department, Position
        db_session.commit()

        # 创建一个用户用于测试，避免外键约束失败
        dept = Department(name="测试部2", code="TEST_SM2")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="测试岗2", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="SM002", name="测试员工2", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
        user = User(username="sm_user2", password_hash="fakehash", role="employee", employee_id=emp.id)
        db_session.add(user)
        db_session.flush()
        db_session.commit()

        next_state = WorkflowStateMachine.transition(
            current_state="pending_approval",
            action="rollback",
            db=db_session,
            user_id=user.id,
            target_id=200,
        )
        assert next_state == "pending_manager"
        db_session.commit()

        log = db_session.query(OperationLog).filter(
            OperationLog.user_id == user.id,
            OperationLog.action == "rollback",
            OperationLog.target_id == 200,
        ).first()
        assert log is not None
        assert log.target_type == "assessment_record"
