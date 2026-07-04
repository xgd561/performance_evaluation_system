import os
import sys
import pytest
import json
import unittest.mock as mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import BizError
from app.models import Base, OperationLog
from app.utils.workflow_state_machine import WorkflowStateMachine

# 创建测试用内存数据库
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
Base.metadata.create_all(bind=test_engine)


class TestStateConstants:
    """测试状态常量定义"""

    def test_all_states_defined(self):
        expected_states = [
            "not_started",
            "pending_self",
            "pending_manager",
            "pending_peer",
            "pending_summary",
            "pending_distribution_review",
            "pending_approval",
            "pending_interview",
            "published",
            "appealed",
            "archived",
        ]
        for state in expected_states:
            assert state in WorkflowStateMachine.STATES

    def test_state_labels_are_chinese(self):
        assert WorkflowStateMachine.get_state_label("not_started") == "未开始"
        assert WorkflowStateMachine.get_state_label("pending_self") == "待自评"
        assert WorkflowStateMachine.get_state_label("pending_manager") == "待上级评分"
        assert WorkflowStateMachine.get_state_label("pending_peer") == "待协作评分"
        assert WorkflowStateMachine.get_state_label("pending_summary") == "待汇总"
        assert WorkflowStateMachine.get_state_label("pending_distribution_review") == "待强制分布审核"
        assert WorkflowStateMachine.get_state_label("pending_approval") == "待审批"
        assert WorkflowStateMachine.get_state_label("pending_interview") == "待面谈"
        assert WorkflowStateMachine.get_state_label("published") == "已发布"
        assert WorkflowStateMachine.get_state_label("appealed") == "申诉中"
        assert WorkflowStateMachine.get_state_label("archived") == "已归档"

    def test_unknown_state_label(self):
        assert WorkflowStateMachine.get_state_label("unknown") is None


class TestStateValidation:
    """测试状态与动作校验"""

    def test_is_valid_state(self):
        assert WorkflowStateMachine.is_valid_state("not_started") is True
        assert WorkflowStateMachine.is_valid_state("pending_self") is True
        assert WorkflowStateMachine.is_valid_state("archived") is True
        assert WorkflowStateMachine.is_valid_state("invalid_state") is False

    def test_is_valid_transition(self):
        assert WorkflowStateMachine.is_valid_transition("not_started", "start_cycle") is True
        assert WorkflowStateMachine.is_valid_transition("pending_self", "submit_self") is True
        assert WorkflowStateMachine.is_valid_transition("not_started", "submit_self") is False
        assert WorkflowStateMachine.is_valid_transition("invalid_state", "start_cycle") is False

    def test_get_allowed_actions(self):
        actions = WorkflowStateMachine.get_allowed_actions("pending_approval")
        assert "approve_step1" in actions
        assert "approve_step2" in actions
        assert "reject" in actions
        assert "rollback" in actions
        assert "submit_self" not in actions

        assert WorkflowStateMachine.get_allowed_actions("invalid_state") == []


class TestSimpleTransitions:
    """测试无条件转换"""

    def test_not_started_to_pending_self(self):
        result = WorkflowStateMachine.transition("not_started", "start_cycle")
        assert result == "pending_self"

    def test_pending_self_to_pending_manager(self):
        result = WorkflowStateMachine.transition("pending_self", "submit_self")
        assert result == "pending_manager"

    def test_pending_peer_to_pending_summary(self):
        result = WorkflowStateMachine.transition("pending_peer", "complete_peer")
        assert result == "pending_summary"

    def test_pending_distribution_review_to_pending_approval(self):
        result = WorkflowStateMachine.transition(
            "pending_distribution_review", "confirm_distribution"
        )
        assert result == "pending_approval"

    def test_approve_step1_keeps_pending_approval(self):
        result = WorkflowStateMachine.transition("pending_approval", "approve_step1")
        assert result == "pending_approval"

    def test_approve_step2_to_pending_interview(self):
        result = WorkflowStateMachine.transition("pending_approval", "approve_step2")
        assert result == "pending_interview"

    def test_reject_keeps_pending_approval(self):
        result = WorkflowStateMachine.transition("pending_approval", "reject")
        assert result == "pending_approval"

    def test_rollback_to_pending_manager(self):
        result = WorkflowStateMachine.transition("pending_approval", "rollback")
        assert result == "pending_manager"

    def test_pending_interview_to_published(self):
        result = WorkflowStateMachine.transition("pending_interview", "submit_interview")
        assert result == "published"

    def test_published_to_appealed(self):
        result = WorkflowStateMachine.transition("published", "appeal")
        assert result == "appealed"

    def test_published_to_archived(self):
        result = WorkflowStateMachine.transition("published", "archive")
        assert result == "archived"

    def test_appealed_to_published(self):
        result = WorkflowStateMachine.transition("appealed", "resolve")
        assert result == "published"


class TestConditionalTransitions:
    """测试条件转换"""

    def test_submit_manager_with_peer_enabled(self):
        result = WorkflowStateMachine.transition(
            "pending_manager", "submit_manager", peer_review_enabled=True
        )
        assert result == "pending_peer"

    def test_submit_manager_with_peer_disabled(self):
        result = WorkflowStateMachine.transition(
            "pending_manager", "submit_manager", peer_review_enabled=False
        )
        assert result == "pending_summary"

    def test_submit_manager_default_peer_enabled(self):
        # 默认 peer_review_enabled=True
        result = WorkflowStateMachine.transition("pending_manager", "submit_manager")
        assert result == "pending_peer"

    def test_trigger_summary_with_distribution(self):
        result = WorkflowStateMachine.transition(
            "pending_summary", "trigger_summary", is_distribution_triggered=True
        )
        assert result == "pending_distribution_review"

    def test_trigger_summary_without_distribution(self):
        result = WorkflowStateMachine.transition(
            "pending_summary", "trigger_summary", is_distribution_triggered=False
        )
        assert result == "pending_approval"

    def test_trigger_summary_default_distribution(self):
        # 默认 is_distribution_triggered=True
        result = WorkflowStateMachine.transition("pending_summary", "trigger_summary")
        assert result == "pending_distribution_review"


class TestInvalidTransitions:
    """测试非法转换抛出异常"""

    def test_invalid_action_from_state(self):
        with pytest.raises(BizError) as exc_info:
            WorkflowStateMachine.transition("not_started", "submit_self")
        assert exc_info.value.code == 1101
        assert "not_started" in exc_info.value.message
        assert "submit_self" in exc_info.value.message
        assert "allowed_actions" in exc_info.value.data

    def test_unknown_state(self):
        with pytest.raises(BizError) as exc_info:
            WorkflowStateMachine.transition("unknown_state", "start_cycle")
        assert exc_info.value.code == 1100
        assert "unknown_state" in exc_info.value.message

    def test_transition_from_archived(self):
        # archived 状态没有定义任何转换动作
        with pytest.raises(BizError) as exc_info:
            WorkflowStateMachine.transition("archived", "start_cycle")
        assert exc_info.value.code == 1101


class TestAuditLog:
    """测试状态转换时自动写入操作日志"""

    def test_transition_writes_to_operation_log(self):
        db = TestSessionLocal()
        # 清空测试日志
        db.query(OperationLog).delete()
        db.commit()

        result = WorkflowStateMachine.transition(
            "not_started",
            "start_cycle",
            db=db,
            user_id=1,
            target_id=42,
            target_type="assessment_record",
            ip_address="127.0.0.1",
        )
        assert result == "pending_self"

        # 验证数据库写入
        logs = db.query(OperationLog).all()
        assert len(logs) == 1
        log = logs[0]
        assert log.user_id == 1
        assert log.action == "start_cycle"
        assert log.target_type == "assessment_record"
        assert log.target_id == 42
        assert log.ip_address == "127.0.0.1"
        assert log.old_value is not None
        assert log.new_value is not None

        old = json.loads(log.old_value)
        new = json.loads(log.new_value)
        assert old["state"] == "not_started"
        assert old["label"] == "未开始"
        assert new["state"] == "pending_self"
        assert new["label"] == "待自评"

    def test_transition_without_db_does_not_log(self):
        # 不传 db 时不报错也不写入日志
        result = WorkflowStateMachine.transition(
            "not_started", "start_cycle", user_id=1
        )
        assert result == "pending_self"

    def test_transition_without_user_id_does_not_log(self):
        db = TestSessionLocal()
        # 不传 user_id 时不写入日志
        result = WorkflowStateMachine.transition(
            "not_started", "start_cycle", db=db
        )
        assert result == "pending_self"

    def test_log_failure_does_not_block_transition(self):
        """日志写入失败不阻断主流程"""
        db = mock.Mock()
        db.add.side_effect = Exception("DB error")

        result = WorkflowStateMachine.transition(
            "not_started",
            "start_cycle",
            db=db,
            user_id=1,
        )
        assert result == "pending_self"


class TestValidators:
    """测试自定义校验器注册"""

    def setup_method(self):
        WorkflowStateMachine.reset_validators()

    def teardown_method(self):
        WorkflowStateMachine.reset_validators()

    def test_register_validator(self):
        def validate_scores(current_state, action, **kwargs):
            if not kwargs.get("scores_complete"):
                raise BizError(message="评分未完成", code=1102)

        WorkflowStateMachine.register_validator("pending_self", "submit_self", validate_scores)

        # 校验通过
        result = WorkflowStateMachine.transition(
            "pending_self", "submit_self", scores_complete=True
        )
        assert result == "pending_manager"

        # 校验失败
        with pytest.raises(BizError) as exc_info:
            WorkflowStateMachine.transition(
                "pending_self", "submit_self", scores_complete=False
            )
        assert exc_info.value.message == "评分未完成"
        assert exc_info.value.code == 1102

    def test_reset_validators(self):
        def dummy_validator(*args, **kwargs):
            raise BizError(message="dummy")

        WorkflowStateMachine.register_validator("pending_self", "submit_self", dummy_validator)
        WorkflowStateMachine.reset_validators()

        # 重置后校验器不再生效
        result = WorkflowStateMachine.transition("pending_self", "submit_self")
        assert result == "pending_manager"


class TestFullWorkflowPath:
    """测试完整工作流路径"""

    def test_full_cycle_with_peer_and_distribution(self):
        """完整路径：协作开启 + 强制分布"""
        sm = WorkflowStateMachine
        state = sm.transition("not_started", "start_cycle")
        assert state == "pending_self"

        state = sm.transition("pending_self", "submit_self")
        assert state == "pending_manager"

        state = sm.transition("pending_manager", "submit_manager", peer_review_enabled=True)
        assert state == "pending_peer"

        state = sm.transition("pending_peer", "complete_peer")
        assert state == "pending_summary"

        state = sm.transition("pending_summary", "trigger_summary", is_distribution_triggered=True)
        assert state == "pending_distribution_review"

        state = sm.transition("pending_distribution_review", "confirm_distribution")
        assert state == "pending_approval"

        state = sm.transition("pending_approval", "approve_step1")
        assert state == "pending_approval"

        state = sm.transition("pending_approval", "approve_step2")
        assert state == "pending_interview"

        state = sm.transition("pending_interview", "submit_interview")
        assert state == "published"

        state = sm.transition("published", "archive")
        assert state == "archived"

    def test_full_cycle_without_peer_without_distribution(self):
        """完整路径：协作关闭 + 不触发强制分布"""
        sm = WorkflowStateMachine
        state = sm.transition("not_started", "start_cycle")
        state = sm.transition("pending_self", "submit_self")
        state = sm.transition("pending_manager", "submit_manager", peer_review_enabled=False)
        assert state == "pending_summary"

        state = sm.transition("pending_summary", "trigger_summary", is_distribution_triggered=False)
        assert state == "pending_approval"

        state = sm.transition("pending_approval", "approve_step2")
        assert state == "pending_interview"

        state = sm.transition("pending_interview", "submit_interview")
        assert state == "published"

    def test_appeal_path(self):
        """申诉路径：published → appealed → published → archive"""
        sm = WorkflowStateMachine
        state = sm.transition("published", "appeal")
        assert state == "appealed"

        state = sm.transition("appealed", "resolve")
        assert state == "published"

        state = sm.transition("published", "archive")
        assert state == "archived"

    def test_rollback_path(self):
        """打回路径：pending_approval → rollback → pending_manager"""
        state = WorkflowStateMachine.transition("pending_approval", "rollback")
        assert state == "pending_manager"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
