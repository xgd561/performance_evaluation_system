from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import (
    AssessmentRecord, Employee, Department, Position, User, ApprovalRecord,
    AssessmentCycle
)

router = APIRouter()


@router.get("/pending")
def get_pending_approvals(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "hr", "admin")),
):
    """获取当前用户的待审批列表"""
    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工信息不存在")

    # 查询需要当前用户审批的记录
    # 逻辑：该用户是某员工的直属上级，且考核记录状态为 pending_manager 或 pending_approval
    # 简化：查询 manager_id = current_employee.id 的员工的考核记录，状态为 pending_manager
    subordinate_ids = db.query(Employee.id).filter(Employee.manager_id == current_employee.id).all()
    subordinate_ids = [sid[0] for sid in subordinate_ids]

    if not subordinate_ids:
        return []

    records = db.query(AssessmentRecord).filter(
        AssessmentRecord.employee_id.in_(subordinate_ids),
        AssessmentRecord.status.in_([
            "pending_manager", "pending_peer", "pending_summary",
            "pending_approval", "pending_interview"
        ])
    ).all()

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
    """通过审批"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工信息不存在")

    # 权限校验：只能审批自己下属的
    if record.employee_id not in [e.id for e in current_employee.subordinates]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权审批此记录")

    # 创建审批记录
    approval = ApprovalRecord(
        record_id=record_id,
        approver_id=current_employee.id,
        approver_role="manager",
        action="approved",
        comment=comment,
    )
    db.add(approval)

    # 更新考核状态
    if record.status == "pending_manager":
        record.status = "pending_peer"
    elif record.status == "pending_peer":
        record.status = "pending_summary"
    elif record.status == "pending_summary":
        record.status = "pending_approval"
    elif record.status == "pending_approval":
        record.status = "pending_interview"
    elif record.status == "pending_interview":
        record.status = "published"

    db.commit()
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

    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工信息不存在")

    if record.employee_id not in [e.id for e in current_employee.subordinates]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权审批此记录")

    approval = ApprovalRecord(
        record_id=record_id,
        approver_id=current_employee.id,
        approver_role="manager",
        action="rejected",
        comment=reason,
    )
    db.add(approval)

    record.status = "pending_manager"
    db.commit()
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

    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工信息不存在")

    if record.employee_id not in [e.id for e in current_employee.subordinates]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权审批此记录")

    approval = ApprovalRecord(
        record_id=record_id,
        approver_id=current_employee.id,
        approver_role="manager",
        action="rollback",
        comment=reason,
    )
    db.add(approval)

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
            "action": a.action,
            "comment": a.comment,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return result
