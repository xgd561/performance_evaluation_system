import pytest
from app.utils.workflow_state_machine import WorkflowStateMachine
from app.core.exceptions import BizError


class TestP5_15StateMachineComplete:
    """P5-15: 状态机完整注册与测试——覆盖所有状态转换"""

    def test_not_started_start_cycle_pending_self(self):
        """1. not_started + start_cycle → pending_self"""
        next_state = WorkflowStateMachine.transition(
            current_state="not_started",
            action="start_cycle",
        )
        assert next_state == "pending_self"

    def test_pending_self_submit_self_pending_manager(self):
        """2. pending_self + submit_self → pending_manager"""
        next_state = WorkflowStateMachine.transition(
            current_state="pending_self",
            action="submit_self",
        )
        assert next_state == "pending_manager"

    def test_pending_manager_submit_manager_peer_review_enabled(self):
        """3. pending_manager + submit_manager(peer_review_enabled=True) → pending_peer"""
        next_state = WorkflowStateMachine.transition(
            current_state="pending_manager",
            action="submit_manager",
            peer_review_enabled=True,
        )
        assert next_state == "pending_peer"

    def test_pending_manager_submit_manager_peer_review_disabled(self):
        """4. pending_manager + submit_manager(peer_review_enabled=False) → pending_summary"""
        next_state = WorkflowStateMachine.transition(
            current_state="pending_manager",
            action="submit_manager",
            peer_review_enabled=False,
        )
        assert next_state == "pending_summary"

    def test_pending_peer_complete_peer_pending_summary(self):
        """5. pending_peer + complete_peer → pending_summary"""
        next_state = WorkflowStateMachine.transition(
            current_state="pending_peer",
            action="complete_peer",
        )
        assert next_state == "pending_summary"

    def test_pending_summary_trigger_summary_distribution_triggered(self):
        """6. pending_summary + trigger_summary(is_distribution_triggered=True) → pending_distribution_review"""
        next_state = WorkflowStateMachine.transition(
            current_state="pending_summary",
            action="trigger_summary",
            is_distribution_triggered=True,
        )
        assert next_state == "pending_distribution_review"

    def test_pending_summary_trigger_summary_not_triggered(self):
        """7. pending_summary + trigger_summary(is_distribution_triggered=False) → pending_approval"""
        next_state = WorkflowStateMachine.transition(
            current_state="pending_summary",
            action="trigger_summary",
            is_distribution_triggered=False,
        )
        assert next_state == "pending_approval"

    def test_pending_distribution_review_confirm_distribution_pending_approval(self):
        """8. pending_distribution_review + confirm_distribution → pending_approval"""
        next_state = WorkflowStateMachine.transition(
            current_state="pending_distribution_review",
            action="confirm_distribution",
        )
        assert next_state == "pending_approval"

    def test_pending_approval_approve_step1_stays_pending_approval(self):
        """9. pending_approval + approve_step1 → pending_approval"""
        next_state = WorkflowStateMachine.transition(
            current_state="pending_approval",
            action="approve_step1",
        )
        assert next_state == "pending_approval"

    def test_pending_approval_approve_step2_pending_interview(self):
        """10. pending_approval + approve_step2 → pending_interview"""
        next_state = WorkflowStateMachine.transition(
            current_state="pending_approval",
            action="approve_step2",
        )
        assert next_state == "pending_interview"

    def test_pending_approval_reject_stays_pending_approval(self):
        """11. pending_approval + reject → pending_approval"""
        next_state = WorkflowStateMachine.transition(
            current_state="pending_approval",
            action="reject",
        )
        assert next_state == "pending_approval"

    def test_pending_approval_rollback_pending_manager(self):
        """12. pending_approval + rollback → pending_manager"""
        next_state = WorkflowStateMachine.transition(
            current_state="pending_approval",
            action="rollback",
        )
        assert next_state == "pending_manager"

    def test_pending_interview_submit_interview_published(self):
        """13. pending_interview + submit_interview → published"""
        next_state = WorkflowStateMachine.transition(
            current_state="pending_interview",
            action="submit_interview",
        )
        assert next_state == "published"

    def test_published_appeal_appealed(self):
        """14. published + appeal → appealed"""
        next_state = WorkflowStateMachine.transition(
            current_state="published",
            action="appeal",
        )
        assert next_state == "appealed"

    def test_published_archive_archived(self):
        """15. published + archive → archived"""
        next_state = WorkflowStateMachine.transition(
            current_state="published",
            action="archive",
        )
        assert next_state == "archived"

    def test_appealed_resolve_published(self):
        """16. appealed + resolve → published"""
        next_state = WorkflowStateMachine.transition(
            current_state="appealed",
            action="resolve",
        )
        assert next_state == "published"

    def test_invalid_state_raises_biz_error_1100(self):
        """17. 未知状态转换抛出 BizError(code=1100)"""
        with pytest.raises(BizError) as exc_info:
            WorkflowStateMachine.transition(
                current_state="unknown_state",
                action="start_cycle",
            )
        assert exc_info.value.code == 1100
        assert "未知状态" in exc_info.value.message

    def test_invalid_action_raises_biz_error_1101(self):
        """18. 非法动作转换抛出 BizError(code=1101)"""
        with pytest.raises(BizError) as exc_info:
            WorkflowStateMachine.transition(
                current_state="pending_approval",
                action="submit_self",
            )
        assert exc_info.value.code == 1101
        assert "不允许执行动作" in exc_info.value.message

    def test_transition_with_db_logs_operation(self, db_session):
        """19. 带 db 和 user_id 的 transition 会记录操作日志"""
        from app.models import OperationLog, User, Employee, Department, Position

        db_session.commit()

        dept = Department(name="测试部", code="TEST_SM")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="SM003", name="测试员工3", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
        user = User(username="sm_user3", password_hash="fakehash", role="employee", employee_id=emp.id)
        db_session.add(user)
        db_session.flush()
        db_session.commit()

        next_state = WorkflowStateMachine.transition(
            current_state="pending_approval",
            action="approve_step2",
            db=db_session,
            user_id=user.id,
            target_id=300,
        )
        assert next_state == "pending_interview"
        db_session.commit()

        log = db_session.query(OperationLog).filter(
            OperationLog.user_id == user.id,
            OperationLog.action == "approve_step2",
            OperationLog.target_id == 300,
        ).first()
        assert log is not None
        assert log.target_type == "assessment_record"
