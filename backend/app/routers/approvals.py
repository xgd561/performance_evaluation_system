from fastapi import APIRouter, Body, Depends, HTTPException, status, Query
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import (
    AssessmentRecord, Employee, Department, Position, User, ApprovalRecord,
    AssessmentCycle, SystemConfig, PeerReviewTask
)
from app.services.operation_logger import log_operation
from app.routers.employees import _is_in_subordinate_chain, get_all_dept_ids
from app.utils.workflow_state_machine import WorkflowStateMachine
from app.routers.archive_guard import check_record_not_archived

DEFAULT_APPROVAL_CHAIN = ["direct_manager", "dept_head", "hr_head"]


def _get_approval_chain(db: Session):
    cfg = db.query(SystemConfig).filter(SystemConfig.key == "approval_chain").first()
    if cfg and cfg.value:
        try:
            return json.loads(cfg.value)
        except Exception:
            pass
    return DEFAULT_APPROVAL_CHAIN


def _get_next_approver_role(db: Session, record: AssessmentRecord, chain: list):
    """Return the next approver role in the chain, or None if complete."""
    existing = db.query(ApprovalRecord).filter(
        ApprovalRecord.record_id == record.id,
        ApprovalRecord.approval_type == "normal",
        ApprovalRecord.action == "approved",
    ).order_by(ApprovalRecord.step_index.desc()).first()
    current_step = existing.step_index if existing else 0
    if current_step < len(chain):
        return chain[current_step]
    return None


def _can_approve_as_role(user, role: str, record: AssessmentRecord, db: Session):
    """Check if current user can act as the given role for this record."""
    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        return False

    if role == "direct_manager":
        return record.employee_id in [e.id for e in current_employee.subordinates]
    elif role == "dept_head":
        record_emp = db.query(Employee).filter(Employee.id == record.employee_id).first()
        if record_emp and record_emp.department_id:
            dept = db.query(Department).filter(Department.id == record_emp.department_id).first()
            if dept and dept.head_id == current_employee.id:
                return True
        return False
    elif role in ("hr_head", "hr"):
        return user.role in ("hr", "admin")
    elif role == "admin":
        return user.role == "admin"
    return False


def _can_access_approval_detail(user, record: AssessmentRecord, db: Session):
    """Check if user can access the approval detail for this record."""
    if user.role in ("admin", "hr"):
        return True

    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        return False

    # Manager of this employee
    if record.employee_id in [e.id for e in current_employee.subordinates]:
        return True

    # Current approver in chain
    chain = _get_approval_chain(db)
    next_role = _get_next_approver_role(db, record, chain)
    if next_role and _can_approve_as_role(user, next_role, record, db):
        return True

    # Department head with access
    if record.department_id:
        record_dept = db.query(Department).filter(Department.id == record.department_id).first()
        checked_dept_id = record_dept.id if record_dept else None
        while checked_dept_id:
            dept = db.query(Department).filter(Department.id == checked_dept_id).first()
            if dept and dept.head_id == current_employee.id:
                return True
            checked_dept_id = dept.parent_id if dept else None

    return False


from app.utils.json_columns import load_json

router = APIRouter()


@router.get("/chain-config")
def get_chain_config(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "hr", "executive")),
):
    """获取当前审批链配置"""
    return {"chain": _get_approval_chain(db)}


@router.put("/chain-config")
def update_chain_config(
    req: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    """更新审批链配置"""
    chain = req.get("chain")
    if not chain or not isinstance(chain, list):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="chain 必须为列表",
        )
    valid_roles = {"direct_manager", "dept_head", "hr_head", "admin"}
    for role in chain:
        if role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"无效的角色: {role}",
            )

    cfg = db.query(SystemConfig).filter(SystemConfig.key == "approval_chain").first()
    if not cfg:
        cfg = SystemConfig(key="approval_chain", value=json.dumps(chain))
        db.add(cfg)
    else:
        cfg.value = json.dumps(chain)
    db.commit()
    db.refresh(cfg)

    log_operation(
        db=db,
        user_id=user.id,
        action="update_approval_chain",
        target_type="system_config",
        target_id=cfg.id,
        new_value={"chain": chain},
    )

    return {"chain": chain}


@router.get("/pending")
def get_pending_approvals(
    department_id: Optional[int] = Query(None),
    is_abnormal: Optional[bool] = Query(None),
    is_force_adjusted: Optional[bool] = Query(None),
    step: Optional[int] = Query(None, ge=1, le=2),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "hr", "admin")),
):
    """获取当前用户的待审批列表（支持多级审批链）"""
    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工信息不存在")

    chain = _get_approval_chain(db)

    # -----------------------------------------------------------------
    # P1-23: 避免全表遍历
    # 先根据用户身份和审批链角色计算可审批的 record_id 范围，
    # 再用 SQL IN 条件查询，避免一次性加载所有 pending_approval 记录。
    # -----------------------------------------------------------------
    # 子查询：每条记录已有的 normal 审批的最大 step_index（仅限已通过的审批）
    step_counts = db.query(
        ApprovalRecord.record_id,
        func.max(ApprovalRecord.step_index).label("max_step"),
    ).filter(
        ApprovalRecord.approval_type == "normal",
        ApprovalRecord.action == "approved",
    ).group_by(ApprovalRecord.record_id).subquery()

    # 预计算用户的关系数据
    subordinate_ids = [e.id for e in current_employee.subordinates] if current_employee.subordinates else []
    dept_ids = [d.id for d in db.query(Department).filter(Department.head_id == current_employee.id).all()]

    # 根据审批链角色和用户身份构建 OR 条件
    conditions = []
    for step_idx, role in enumerate(chain):
        if role == "direct_manager" and subordinate_ids:
            conditions.append(
                and_(
                    AssessmentRecord.employee_id.in_(subordinate_ids),
                    func.coalesce(step_counts.c.max_step, 0) == step_idx,
                )
            )
        elif role == "dept_head" and dept_ids:
            conditions.append(
                and_(
                    AssessmentRecord.department_id.in_(dept_ids),
                    func.coalesce(step_counts.c.max_step, 0) == step_idx,
                )
            )
        elif role in ("hr_head", "hr") and user.role in ("hr", "admin"):
            if user.role == "admin":
                # 管理员可代任何步骤处理
                conditions.append(AssessmentRecord.status == "pending_approval")
            else:
                # HR 只在轮到 hr_head 步骤时可见，避免提前看到前序步骤的记录
                conditions.append(
                    and_(
                        AssessmentRecord.status == "pending_approval",
                        func.coalesce(step_counts.c.max_step, 0) == step_idx,
                    )
                )
        elif role == "admin" and user.role == "admin":
            conditions.append(
                AssessmentRecord.status == "pending_approval"
            )

    if conditions:
        query = db.query(AssessmentRecord).outerjoin(
            step_counts, AssessmentRecord.id == step_counts.c.record_id
        ).filter(
            AssessmentRecord.status == "pending_approval"
        ).filter(
            or_(*conditions)
        )
    else:
        return []

    # P5-06: Additional query parameter filters
    if department_id is not None:
        query = query.filter(AssessmentRecord.department_id == department_id)

    if is_abnormal is not None:
        query = query.filter(AssessmentRecord.is_distribution_override == is_abnormal)

    if is_force_adjusted is not None:
        if is_force_adjusted:
            query = query.filter(
                and_(
                    AssessmentRecord.original_grade != None,
                    AssessmentRecord.grade != AssessmentRecord.original_grade,
                )
            )
        else:
            query = query.filter(
                or_(
                    AssessmentRecord.original_grade == None,
                    AssessmentRecord.grade == AssessmentRecord.original_grade,
                )
            )

    if step is not None:
        # step=1 means first role in chain (step_idx=0 in DB)
        # step=2 means second role in chain (step_idx=1 in DB)
        target_step_idx = step - 1
        if target_step_idx < len(chain):
            query = query.filter(func.coalesce(step_counts.c.max_step, 0) == target_step_idx)

    records = query.all()

    # 组装返回数据（与原有逻辑保持一致）
    result = []
    for r in records:
        emp = db.query(Employee).filter(Employee.id == r.employee_id).first()
        dept = db.query(Department).filter(Department.id == r.department_id).first()
        pos = db.query(Position).filter(Position.id == r.position_id).first()
        cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == r.cycle_id).first()

        self_scores = load_json(r.self_scores, {})
        manager_scores = load_json(r.manager_scores, {})
        total_score = str(r.total_score) if r.total_score else None
        grade = r.grade if r.grade else None

        # 异常标记：强制调整
        is_abnormal_flag = r.is_distribution_override
        # 异常标记：上级评分与自评分差异超过20分
        score_diff_alert = False
        if manager_scores and self_scores:
            for dim in ["performance", "ability", "attitude"]:
                m_score = manager_scores.get(dim)
                s_score = self_scores.get(dim)
                if m_score is not None and s_score is not None and abs(float(m_score) - float(s_score)) > 20:
                    score_diff_alert = True
                    break

        next_role = _get_next_approver_role(db, r, chain)
        existing_approvals = db.query(ApprovalRecord).filter(
            ApprovalRecord.record_id == r.id,
            ApprovalRecord.approval_type == "normal",
            ApprovalRecord.action == "approved",
        ).order_by(ApprovalRecord.step_index.desc()).first()
        step_index = (existing_approvals.step_index if existing_approvals else 0) + 1

        result.append({
            "record_id": r.id,
            "cycle_id": r.cycle_id,
            "cycle_name": cycle.name if cycle else None,
            "employee_id": r.employee_id,
            "employee_name": emp.name if emp else None,
            "employee_no": emp.employee_no if emp else None,
            "department_name": dept.name if dept else None,
            "position_name": pos.name if pos else None,
            "status": r.status,
            "self_scores": self_scores,
            "manager_scores": manager_scores,
            "total_score": total_score,
            "grade": grade,
            "is_abnormal": is_abnormal_flag,
            "score_diff_alert": score_diff_alert,
            "manager_comment": r.manager_comment,
            "step_index": step_index,
            "next_approver_role": next_role,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return result


@router.get("/distribution-overrides")
def get_distribution_overrides(
    cycle_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "hr", "executive")),
):
    """获取强制分布特批申请列表"""
    query = db.query(AssessmentRecord).filter(
        AssessmentRecord.override_reason != None,
        AssessmentRecord.is_distribution_override == False,
    )
    if cycle_id:
        query = query.filter(AssessmentRecord.cycle_id == cycle_id)
    records = query.all()

    result = []
    for r in records:
        emp = db.query(Employee).filter(Employee.id == r.employee_id).first()
        result.append({
            "record_id": r.id,
            "employee_id": r.employee_id,
            "employee_name": emp.name if emp else None,
            "employee_no": emp.employee_no if emp else None,
            "total_score": str(r.total_score) if r.total_score else None,
            "original_grade": r.original_grade,
            "adjusted_grade": r.grade,
            "override_reason": r.override_reason,
        })

    return result


@router.get("/{record_id:int}")
def get_approval_detail(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "hr", "admin")),
):
    """P5-07: 获取审批详情（包含评分、历史、审批链）"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    if not _can_access_approval_detail(user, record, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看此记录")

    emp = db.query(Employee).filter(Employee.id == record.employee_id).first()
    dept = db.query(Department).filter(Department.id == record.department_id).first()
    pos = db.query(Position).filter(Position.id == record.position_id).first()
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == record.cycle_id).first()

    self_scores = load_json(record.self_scores, {})
    manager_scores = load_json(record.manager_scores, {})
    peer_scores = load_json(record.peer_scores, {})

    # Peer comments from PeerReviewTask
    peer_tasks = db.query(PeerReviewTask).filter(
        PeerReviewTask.record_id == record_id,
        PeerReviewTask.status == "completed",
    ).all()
    peer_comments = []
    for task in peer_tasks:
        reviewer = db.query(Employee).filter(Employee.id == task.reviewer_id).first()
        peer_comments.append({
            "reviewer_name": reviewer.name if reviewer else None,
            "ability_score": str(task.ability_score) if task.ability_score else None,
            "comment": task.comment,
        })

    # History: last 3 cycles excluding current, ordered by cycle start date desc
    history = []
    if emp:
        past_records = db.query(AssessmentRecord).join(AssessmentCycle).filter(
            AssessmentRecord.employee_id == emp.id,
            AssessmentRecord.id != record_id,
        ).order_by(AssessmentCycle.start_date.desc()).limit(3).all()
        for pr in past_records:
            pr_cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == pr.cycle_id).first()
            history.append({
                "cycle_name": pr_cycle.name if pr_cycle else None,
                "total_score": str(pr.total_score) if pr.total_score else None,
                "grade": pr.grade,
            })

    # Approval history
    approval_history = []
    approvals = db.query(ApprovalRecord).filter(
        ApprovalRecord.record_id == record_id,
    ).order_by(ApprovalRecord.step_index.asc()).all()
    for a in approvals:
        approver = db.query(Employee).filter(Employee.id == a.approver_id).first()
        approval_history.append({
            "approver_name": approver.name if approver else None,
            "action": a.action,
            "comment": a.comment,
            "step_index": a.step_index,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })

    # Score diff alert
    score_diff_alert = False
    if manager_scores and self_scores:
        for dim in ["performance", "ability", "attitude"]:
            m_score = manager_scores.get(dim)
            s_score = self_scores.get(dim)
            if m_score is not None and s_score is not None and abs(float(m_score) - float(s_score)) > 20:
                score_diff_alert = True
                break

    return {
        "record_id": record.id,
        "employee_id": record.employee_id,
        "employee_name": emp.name if emp else None,
        "employee_no": emp.employee_no if emp else None,
        "department_name": dept.name if dept else None,
        "position_name": pos.name if pos else None,
        "cycle_name": cycle.name if cycle else None,
        "status": record.status,
        "self_scores": self_scores,
        "manager_scores": manager_scores,
        "manager_comment": record.manager_comment,
        "peer_scores": peer_scores,
        "peer_comments": peer_comments,
        "weighted_performance": str(record.weighted_performance) if record.weighted_performance else None,
        "weighted_ability": str(record.weighted_ability) if record.weighted_ability else None,
        "weighted_attitude": str(record.weighted_attitude) if record.weighted_attitude else None,
        "total_score": str(record.total_score) if record.total_score else None,
        "grade": record.grade,
        "original_grade": record.original_grade,
        "is_distribution_override": record.is_distribution_override,
        "is_abnormal": record.is_distribution_override,
        "score_diff_alert": score_diff_alert,
        "history": history,
        "approval_history": approval_history,
    }


@router.post("/{record_id:int}/approve")
def approve_record(
    record_id: int,
    comment: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "hr", "admin")),
):
    """通过审批（支持多级审批链）"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    check_record_not_archived(record_id, db)

    if record.status != "pending_approval":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="当前状态不允许审批")

    chain = _get_approval_chain(db)
    next_role = _get_next_approver_role(db, record, chain)
    if not next_role:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="该记录已完成所有审批")

    if not _can_approve_as_role(user, next_role, record, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权审批此记录")

    # Determine current step
    existing = db.query(ApprovalRecord).filter(
        ApprovalRecord.record_id == record_id,
        ApprovalRecord.approval_type == "normal",
        ApprovalRecord.action == "approved",
    ).order_by(ApprovalRecord.step_index.desc()).first()
    current_step = existing.step_index if existing else 0

    # Duplicate check: same approver at same step
    dup = db.query(ApprovalRecord).filter(
        ApprovalRecord.record_id == record_id,
        ApprovalRecord.approver_id == user.employee_id,
        ApprovalRecord.step_index == current_step + 1,
        ApprovalRecord.action == "approved",
    ).first()
    if dup:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该记录已审批通过，请勿重复操作")

    # Comment validation
    if comment is not None and len(comment) < 10:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="comment 必须至少 10 个字符")

    # Create approval record
    approval = ApprovalRecord(
        record_id=record_id,
        approver_id=user.employee_id,
        approver_role=next_role,
        step_index=current_step + 1,
        action="approved",
        comment=comment,
    )
    db.add(approval)

    old_status = record.status

    # Use WorkflowStateMachine to determine new status
    action_name = "approve_step1" if current_step + 1 < len(chain) else "approve_step2"
    # 状态机日志不重复落库：本接口末尾会写一条业务语义的 approve 日志
    new_status = WorkflowStateMachine.transition(
        current_state="pending_approval",
        action=action_name,
    )
    record.status = new_status

    db.commit()

    log_operation(
        db=db,
        user_id=user.id,
        action="approve",
        target_type="assessment_record",
        target_id=record_id,
        old_value={"status": old_status, "step": current_step},
        new_value={"status": record.status, "step": current_step + 1},
    )

    return {"message": "审批通过", "record_id": record_id, "status": record.status}


@router.post("/{record_id:int}/reject")
def reject_record(
    record_id: int,
    reason: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "hr", "admin")),
):
    """驳回审批（返回上级修改）"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    check_record_not_archived(record_id, db)

    if record.status != "pending_approval":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="当前状态不允许审批")

    chain = _get_approval_chain(db)
    next_role = _get_next_approver_role(db, record, chain)
    if not next_role:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="该记录已完成所有审批")

    if not _can_approve_as_role(user, next_role, record, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权审批此记录")

    existing = db.query(ApprovalRecord).filter(
        ApprovalRecord.record_id == record_id,
        ApprovalRecord.approval_type == "normal",
        ApprovalRecord.action == "approved",
    ).order_by(ApprovalRecord.step_index.desc()).first()
    current_step = existing.step_index if existing else 0

    # Duplicate check
    dup = db.query(ApprovalRecord).filter(
        ApprovalRecord.record_id == record_id,
        ApprovalRecord.approver_id == user.employee_id,
        ApprovalRecord.action == "rejected",
    ).first()
    if dup:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该记录已驳回，请勿重复操作")

    # Reason validation
    if len(reason) < 10:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="reason 必须至少 10 个字符")

    approval = ApprovalRecord(
        record_id=record_id,
        approver_id=user.employee_id,
        approver_role=next_role,
        step_index=current_step + 1,
        action="rejected",
        comment=reason,
    )
    db.add(approval)

    old_status = record.status

    # Use WorkflowStateMachine to determine new status (should stay pending_approval)
    new_status = WorkflowStateMachine.transition(
        current_state="pending_approval",
        action="reject",
        db=db,
        user_id=user.id,
        target_id=record_id,
    )
    record.status = new_status

    db.commit()

    log_operation(
        db=db,
        user_id=user.id,
        action="reject",
        target_type="assessment_record",
        target_id=record_id,
        old_value={"status": old_status},
        new_value={"status": record.status, "reason": reason},
    )

    return {"message": "已驳回，返回上级修改", "record_id": record_id}


@router.post("/{record_id:int}/rollback")
def rollback_record(
    record_id: int,
    reason: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "hr", "admin")),
):
    """打回重评（清除评分数据，回到自评阶段）"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    check_record_not_archived(record_id, db)

    if record.status != "pending_approval":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="当前状态不允许打回")

    chain = _get_approval_chain(db)
    next_role = _get_next_approver_role(db, record, chain)
    if not next_role:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="该记录已完成所有审批")

    if not _can_approve_as_role(user, next_role, record, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权审批此记录")

    existing = db.query(ApprovalRecord).filter(
        ApprovalRecord.record_id == record_id,
        ApprovalRecord.approval_type == "normal",
        ApprovalRecord.action == "approved",
    ).order_by(ApprovalRecord.step_index.desc()).first()
    current_step = existing.step_index if existing else 0

    # Duplicate check
    dup = db.query(ApprovalRecord).filter(
        ApprovalRecord.record_id == record_id,
        ApprovalRecord.approver_id == user.employee_id,
        ApprovalRecord.action == "rollback",
    ).first()
    if dup:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该记录已打回，请勿重复操作")

    # Reason validation
    if len(reason) < 10:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="reason 必须至少 10 个字符")

    approval = ApprovalRecord(
        record_id=record_id,
        approver_id=user.employee_id,
        approver_role=next_role,
        step_index=current_step + 1,
        action="rollback",
        comment=reason,
    )
    db.add(approval)

    old_scores = {
        "self_scores": record.self_scores,
        "manager_scores": record.manager_scores,
        "peer_scores": record.peer_scores,
        "total_score": str(record.total_score) if record.total_score else None,
        "grade": record.grade,
        "status": record.status,
    }

    # 清除评分数据（仅清除经理相关数据，保留自评和协作评分）
    record.manager_scores = None
    record.manager_draft_scores = None
    record.weighted_performance = None
    record.weighted_ability = None
    record.weighted_attitude = None
    record.total_score = None
    record.grade = None
    record.original_grade = None
    record.manager_comment = None

    # Use WorkflowStateMachine to determine new status (should be pending_manager)
    new_status = WorkflowStateMachine.transition(
        current_state="pending_approval",
        action="rollback",
        db=db,
        user_id=user.id,
        target_id=record_id,
    )
    record.status = new_status

    db.commit()

    log_operation(
        db=db,
        user_id=user.id,
        action="rollback",
        target_type="assessment_record",
        target_id=record_id,
        old_value=old_scores,
        new_value={"status": record.status},
    )

    return {"message": "已打回重评，考核回到上级评分阶段", "record_id": record_id}


@router.get("/history")
def get_approval_history(
    record_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "hr", "admin")),
):
    """获取审批历史"""
    query = db.query(ApprovalRecord)
    if record_id:
        query = query.filter(ApprovalRecord.record_id == record_id)

    records = query.order_by(ApprovalRecord.created_at.desc()).all()
    result = []
    for a in records:
        approver = db.query(Employee).filter(Employee.id == a.approver_id).first()
        result.append({
            "id": a.id,
            "record_id": a.record_id,
            "approver_id": a.approver_id,
            "approver_name": approver.name if approver else None,
            "approver_role": a.approver_role,
            "step_index": a.step_index,
            "action": a.action,
            "comment": a.comment,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return result


@router.post("/{record_id:int}/distribution-override")
def request_distribution_override(
    record_id: int,
    reason: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "hr", "admin")),
):
    """申请强制分布特批"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    check_record_not_archived(record_id, db)

    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工信息不存在")

    if record.employee_id not in [e.id for e in current_employee.subordinates]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权审批此记录")

    if not record.original_grade or record.original_grade == record.grade:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="该记录未被强制调整，无需特批")

    record.override_reason = reason
    db.commit()

    log_operation(
        db=db,
        user_id=user.id,
        action="request_distribution_override",
        target_type="assessment_record",
        target_id=record_id,
        new_value={"override_reason": reason, "original_grade": record.original_grade, "current_grade": record.grade},
    )

    return {"message": "特批申请已提交", "record_id": record_id}


@router.post("/distribution-overrides/{record_id:int}/approve")
def approve_distribution_override(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "hr")),
):
    """审批通过强制分布特批"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    check_record_not_archived(record_id, db)

    if not record.override_reason:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="该记录未提交特批申请")

    old_grade = record.grade
    record.grade = record.original_grade
    record.is_distribution_override = True
    db.commit()

    log_operation(
        db=db,
        user_id=user.id,
        action="approve_distribution_override",
        target_type="assessment_record",
        target_id=record_id,
        old_value={"grade": old_grade},
        new_value={"grade": record.grade, "is_distribution_override": True},
    )

    return {"message": "特批已通过，等级恢复为原始等级", "record_id": record_id, "grade": record.grade}


@router.post("/distribution-overrides/{record_id:int}/reject")
def reject_distribution_override(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "hr")),
):
    """驳回强制分布特批申请"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    check_record_not_archived(record_id, db)

    if not record.override_reason:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="该记录未提交特批申请")

    record.override_reason = None
    db.commit()

    log_operation(
        db=db,
        user_id=user.id,
        action="reject_distribution_override",
        target_type="assessment_record",
        target_id=record_id,
    )

    return {"message": "特批申请已驳回", "record_id": record_id}


@router.get("/department-distribution")
def get_department_distribution(
    department_id: int = Query(..., description="部门 ID"),
    cycle_id: Optional[int] = Query(None, description="考核周期 ID，缺省取该部门最近一个周期"),
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr", "manager", "executive")),
):
    """部门当前等级分布（审批工作台底部卡片使用）。

    返回 {grades: [{grade, count, ratio, is_over_limit}], total, cycle_id}，
    is_over_limit 按周期 grade_rules 的 ratio_limit（缺省 A20/B70/C10）与小部门豁免规则判定。
    """
    from collections import Counter
    from app.services.distribution_enforcer import _normalize_grade_rules, _small_dept_caps

    if cycle_id is None:
        latest = (
            db.query(AssessmentRecord.cycle_id)
            .filter(AssessmentRecord.department_id == department_id)
            .order_by(AssessmentRecord.cycle_id.desc())
            .first()
        )
        if not latest:
            return {"grades": [], "total": 0, "cycle_id": None}
        cycle_id = latest[0]

    records = (
        db.query(AssessmentRecord)
        .filter(
            AssessmentRecord.department_id == department_id,
            AssessmentRecord.cycle_id == cycle_id,
        )
        .all()
    )
    total = len(records)
    if total == 0:
        return {"grades": [], "total": 0, "cycle_id": cycle_id}

    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == cycle_id).first()
    rules = _normalize_grade_rules(load_json(cycle.grade_rules, {}) if cycle else {})

    if cycle and cycle.small_dept_exemption and total <= 5:
        caps = _small_dept_caps(total)
    else:
        caps = {}
        for grade, rule in rules.items():
            ratio_limit = rule.get("ratio_limit")
            caps[grade] = int(total * ratio_limit) if ratio_limit is not None else total

    counts = Counter(r.grade for r in records if r.grade)
    ordered_grades = list(rules.keys()) + [g for g in counts if g not in rules]

    grades = []
    for grade in ordered_grades:
        count = counts.get(grade, 0)
        grades.append({
            "grade": grade,
            "count": count,
            "ratio": round(count * 100.0 / total, 1),
            "is_over_limit": count > caps.get(grade, total),
        })

    return {
        "grades": grades,
        "total": total,
        "cycle_id": cycle_id,
        "cycle_name": cycle.name if cycle else None,
        "is_distribution_enabled": bool(cycle.is_distribution_enabled) if cycle else False,
    }
