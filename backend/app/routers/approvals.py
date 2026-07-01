from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import (
    AssessmentRecord, Employee, Department, Position, User, ApprovalRecord,
    AssessmentCycle, SystemConfig
)
from app.services.operation_logger import log_operation

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
    # 子查询：每条记录已有的 normal 审批的最大 step_index
    step_counts = db.query(
        ApprovalRecord.record_id,
        func.max(ApprovalRecord.step_index).label("max_step"),
    ).filter(ApprovalRecord.approval_type == "normal").group_by(ApprovalRecord.record_id).subquery()

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
            conditions.append(
                func.coalesce(step_counts.c.max_step, 0) == step_idx
            )
        elif role == "admin" and user.role == "admin":
            conditions.append(
                func.coalesce(step_counts.c.max_step, 0) == step_idx
            )

    if conditions:
        records = db.query(AssessmentRecord).outerjoin(
            step_counts, AssessmentRecord.id == step_counts.c.record_id
        ).filter(
            AssessmentRecord.status == "pending_approval"
        ).filter(
            or_(*conditions)
        ).all()
    else:
        records = []

    # 组装返回数据（与原有逻辑保持一致）
    result = []
    for r in records:
        emp = db.query(Employee).filter(Employee.id == r.employee_id).first()
        dept = db.query(Department).filter(Department.id == r.department_id).first()
        pos = db.query(Position).filter(Position.id == r.position_id).first()
        cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == r.cycle_id).first()

        self_scores = json.loads(r.self_scores) if r.self_scores else {}
        manager_scores = json.loads(r.manager_scores) if r.manager_scores else {}
        total_score = str(r.total_score) if r.total_score else None
        grade = r.grade if r.grade else None

        # 异常标记：强制调整
        is_abnormal = r.is_distribution_override
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
            "is_abnormal": is_abnormal,
            "score_diff_alert": score_diff_alert,
            "manager_comment": r.manager_comment,
            "next_approver_role": next_role,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return result


@router.post("/{record_id}/approve")
def approve_record(
    record_id: int,
    comment: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "hr", "admin")),
):
    """通过审批（支持多级审批链）"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

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
    ).order_by(ApprovalRecord.step_index.desc()).first()
    current_step = existing.step_index if existing else 0

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

    # Check if there are more steps
    if current_step + 1 < len(chain):
        record.status = "pending_approval"
    else:
        record.status = "pending_interview"

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


@router.post("/{record_id}/reject")
def reject_record(
    record_id: int,
    reason: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "hr", "admin")),
):
    """驳回审批（返回上级修改）"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

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
    ).order_by(ApprovalRecord.step_index.desc()).first()
    current_step = existing.step_index if existing else 0

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
    record.status = "pending_manager"
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


@router.post("/{record_id}/rollback")
def rollback_record(
    record_id: int,
    reason: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "hr", "admin")),
):
    """打回重评（清除评分数据，回到自评阶段）"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

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
    ).order_by(ApprovalRecord.step_index.desc()).first()
    current_step = existing.step_index if existing else 0

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

    # 清除评分数据
    record.self_scores = None
    record.manager_scores = None
    record.peer_scores = None
    record.weighted_performance = None
    record.weighted_ability = None
    record.weighted_attitude = None
    record.total_score = None
    record.grade = None
    record.original_grade = None
    record.manager_comment = None
    record.status = "pending_self"

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

    return {"message": "已打回重评，考核回到自评阶段", "record_id": record_id}


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


@router.post("/{record_id}/distribution-override")
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


@router.post("/distribution-overrides/{record_id}/approve")
def approve_distribution_override(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "hr")),
):
    """审批通过强制分布特批"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

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


@router.post("/distribution-overrides/{record_id}/reject")
def reject_distribution_override(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "hr")),
):
    """驳回强制分布特批申请"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

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
