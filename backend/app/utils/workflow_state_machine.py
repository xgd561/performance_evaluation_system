import json
from typing import Any, Optional, Callable, Union

from sqlalchemy.orm import Session

from app.core.exceptions import BizError
from app.utils.audit_logger import log_operation


class WorkflowStateMachine:
    """
    绩效考核状态机基类。

    定义从考核创建到归档的完整状态流转规则：
    not_started → pending_self → pending_manager → pending_peer →
    pending_summary → pending_distribution_review → pending_approval →
    pending_interview → published → archived

    申诉分支：published → appealed → published
    """

    # 状态常量 → 中文描述
    STATES = {
        "not_started": "未开始",
        "pending_self": "待自评",
        "pending_manager": "待上级评分",
        "pending_peer": "待协作评分",
        "pending_summary": "待汇总",
        "pending_distribution_review": "待强制分布审核",
        "pending_approval": "待审批",
        "pending_interview": "待面谈",
        "published": "已发布",
        "appealed": "申诉中",
        "archived": "已归档",
    }

    # 状态转换规则：当前状态 → {动作: 目标状态或解析函数}
    # 值为 callable 时接收 **kwargs 返回目标状态字符串
    TRANSITIONS = {
        "not_started": {
            "start_cycle": "pending_self",
        },
        "pending_self": {
            "submit_self": "pending_manager",
        },
        "pending_manager": {
            "submit_manager": lambda peer_review_enabled=True, **kwargs: (
                "pending_peer" if peer_review_enabled else "pending_summary"
            ),
        },
        "pending_peer": {
            "complete_peer": "pending_summary",
        },
        "pending_summary": {
            "trigger_summary": lambda is_distribution_triggered=True, **kwargs: (
                "pending_distribution_review" if is_distribution_triggered else "pending_approval"
            ),
        },
        "pending_distribution_review": {
            "confirm_distribution": "pending_approval",
        },
        "pending_approval": {
            "approve_step1": "pending_approval",
            "approve_step2": "pending_interview",
            "reject": "pending_approval",
            "rollback": "pending_manager",
        },
        "pending_interview": {
            "submit_interview": "published",
        },
        "published": {
            "appeal": "appealed",
            "archive": "archived",
        },
        "appealed": {
            "resolve": "published",
        },
    }

    # 可额外注册的校验函数：当前状态 → {动作: callable(current_state, action, **kwargs)}
    _validators: dict[str, dict[str, Callable]] = {}

    @classmethod
    def get_state_label(cls, state: str) -> Optional[str]:
        """获取状态中文描述"""
        return cls.STATES.get(state)

    @classmethod
    def get_allowed_actions(cls, state: str) -> list[str]:
        """获取当前状态允许的所有动作"""
        return list(cls.TRANSITIONS.get(state, {}).keys())

    @classmethod
    def is_valid_state(cls, state: str) -> bool:
        """判断是否为已定义的状态"""
        return state in cls.STATES

    @classmethod
    def is_valid_transition(cls, current_state: str, action: str) -> bool:
        """判断当前状态下是否可以执行指定动作"""
        if not cls.is_valid_state(current_state):
            return False
        return action in cls.TRANSITIONS.get(current_state, {})

    @classmethod
    def transition(
        cls,
        current_state: str,
        action: str,
        db: Optional[Session] = None,
        user_id: Optional[int] = None,
        target_id: Optional[int] = None,
        target_type: str = "assessment_record",
        ip_address: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        执行状态转换。

        Args:
            current_state: 当前状态
            action: 触发动作
            db: 数据库 Session（传入时自动记录操作日志）
            user_id: 操作人 ID
            target_id: 目标对象 ID（如 assessment_record.id）
            target_type: 目标对象类型
            ip_address: 客户端 IP
            **kwargs: 条件参数（如 peer_review_enabled、is_distribution_triggered 等）

        Returns:
            str: 转换后的目标状态

        Raises:
            BizError: 状态不存在或动作不合法
        """
        # 1. 校验当前状态
        if not cls.is_valid_state(current_state):
            raise BizError(
                message=f"未知状态: {current_state}",
                code=1100,
                data={"current_state": current_state},
            )

        # 2. 校验动作是否允许
        allowed = cls.TRANSITIONS.get(current_state, {})
        if action not in allowed:
            raise BizError(
                message=f"状态 '{current_state}' 不允许执行动作 '{action}'",
                code=1101,
                data={
                    "current_state": current_state,
                    "action": action,
                    "allowed_actions": list(allowed.keys()),
                },
            )

        # 3. 执行额外注册的业务校验（如有）
        validators = cls._validators.get(current_state, {})
        if action in validators:
            validators[action](current_state, action, **kwargs)

        # 4. 解析目标状态（支持条件转换）
        target = allowed[action]
        if callable(target):
            next_state = target(**kwargs)
        else:
            next_state = target

        # 5. 记录操作日志
        if db is not None and user_id is not None:
            try:
                log_operation(
                    db=db,
                    user_id=user_id,
                    action=action,
                    target_type=target_type,
                    target_id=target_id,
                    old_value={"state": current_state, "label": cls.get_state_label(current_state)},
                    new_value={"state": next_state, "label": cls.get_state_label(next_state)},
                    ip_address=ip_address,
                )
            except Exception:
                # 日志写入失败不阻断主流程
                pass

        return next_state

    @classmethod
    def register_validator(cls, state: str, action: str, validator: Callable):
        """
        为指定状态和动作注册额外业务校验函数。

        Args:
            state: 当前状态
            action: 触发动作
            validator: 校验函数，签名 validator(current_state, action, **kwargs)，
                       校验失败需自行抛出 BizError
        """
        if state not in cls._validators:
            cls._validators[state] = {}
        cls._validators[state][action] = validator

    @classmethod
    def reset_validators(cls):
        """清空所有已注册的校验函数（主要用于测试）"""
        cls._validators = {}
