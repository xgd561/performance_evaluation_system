from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import AppealRecord, AssessmentRecord, Employee, User
from app.routers.archive_guard import check_record_not_archived

from app.services.notification_service import create_notification
from app.services.operation_logger import log_operation
import json

router = APIRouter()

@router.get("")
def list_appeals(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr", "executive")),
):
    query = db.query(AppealRecord).join(Employee, AppealRecord.employee_id == Employee.id)
    if status:
        query = query.filter(AppealRecord.status == status)
    records = query.order_by(AppealRecord.created_at.desc()).all()
    result = []
    for r in records:
        emp = db.query(Employee).filter(Employee.id == r.employee_id).first()
        reviewer = db.query(Employee).filter(Employee.id == r.reviewer_id).first() if r.reviewer_id else None
        result.append({
            "id": r.id,
            "record_id": r.record_id,
            "employee_id": r.employee_id,
            "employee_name": emp.name if emp else None,
            "employee_no": emp.employee_no if emp else None,
            "reason": r.reason,
            "detail": r.detail,
            "status": r.status,
            "reviewer_id": r.reviewer_id,
            "reviewer_name": reviewer.name if reviewer else None,
            "review_result": r.review_result,
            "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return result

@router.get("/my-appeals")
def list_my_appeals(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("employee")),
):
    """获取我的申诉历史"""
    records = db.query(AppealRecord).filter(
        AppealRecord.employee_id == (user.employee_id or user.id)
    ).order_by(AppealRecord.created_at.desc()).all()

    result = []
    for r in records:
        reviewer = db.query(Employee).filter(Employee.id == r.reviewer_id).first() if r.reviewer_id else None
        result.append({
            "id": r.id,
            "record_id": r.record_id,
            "reason": r.reason,
            "detail": r.detail,
            "status": r.status,
            "reviewer_name": reviewer.name if reviewer else None,
            "review_result": r.review_result,
            "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return result
def list_pending_appeals(
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr", "executive")),
):
    return list_appeals(status="pending", db=db, user=user)

@router.get("/{appeal_id}")
def get_appeal(
    appeal_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    appeal = db.query(AppealRecord).filter(AppealRecord.id == appeal_id).first()
    if not appeal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="申诉记录不存在")

    emp = db.query(Employee).filter(Employee.id == appeal.employee_id).first()
    reviewer = db.query(Employee).filter(Employee.id == appeal.reviewer_id).first() if appeal.reviewer_id else None
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == appeal.record_id).first()

    return {
        "id": appeal.id,
        "record_id": appeal.record_id,
        "employee_id": appeal.employee_id,
        "employee_name": emp.name if emp else None,
        "employee_no": emp.employee_no if emp else None,
        "reason": appeal.reason,
        "detail": appeal.detail,
        "status": appeal.status,
        "reviewer_id": appeal.reviewer_id,
        "reviewer_name": reviewer.name if reviewer else None,
        "review_result": appeal.review_result,
        "resolved_at": appeal.resolved_at.isoformat() if appeal.resolved_at else None,
        "created_at": appeal.created_at.isoformat() if appeal.created_at else None,
        "record": {
            "total_score": str(record.total_score) if record and record.total_score else None,
            "grade": record.grade if record else None,
            "status": record.status if record else None,
        } if record else None,
    }

@router.post("", status_code=status.HTTP_201_CREATED)
def create_appeal(
    req: dict,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    record_id = req.get("record_id")
    reason = req.get("reason")
    detail = req.get("detail")

    if not record_id or not reason:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="record_id 和 reason 必填")

    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    check_record_not_archived(record_id, db)

    # P6-05: 仅 published 状态允许申诉
    if record.status != "published":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅已发布状态的考核记录可发起申诉")

    # P6-05: 申诉理由和详细说明校验
    if not reason or len(reason.strip()) == 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="申诉理由必填")
    if len(reason) > 1000:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="申诉理由不超过1000字")
    if not detail or len(detail.strip()) < 20:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="详细说明不少于20字")

    appeal = AppealRecord(
        record_id=record_id,
        employee_id=user.employee_id or user.id,
        reason=reason,
        detail=detail,
        status="pending",
    )
    db.add(appeal)
    db.commit()
    db.refresh(appeal)

    # P6-05: 更新 AssessmentRecord 的 appeal_record JSON 字段
    record.appeal_record = {
        "appeal_id": appeal.id,
        "reason": reason,
        "detail": detail,
        "status": "pending",
        "created_at": appeal.created_at.isoformat() if appeal.created_at else None,
    }
    record.status = "appealed"
    db.commit()

    # P6-05: 通知 HR
    hr_users = db.query(User).filter(User.role.in_(["hr", "admin"])).all()
    for hr in hr_users:
        create_notification(
            db=db,
            user_id=hr.id,
            title="待处理申诉",
            content=f"员工 {user.username} 对考核记录 #{record_id} 发起了申诉，请尽快复核。",
            type="appeal_created",
        )

    log_operation(
        db=db,
        user_id=user.id,
        action="create_appeal",
        target_type="appeal_record",
        target_id=appeal.id,
        new_value={"record_id": record_id, "reason": reason, "status": "pending"},
    )

    return {
        "id": appeal.id,
        "record_id": appeal.record_id,
        "status": appeal.status,
        "created_at": appeal.created_at.isoformat() if appeal.created_at else None,
    }

@router.post("/{appeal_id}/review")
def review_appeal(
    appeal_id: int,
    req: dict,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr")),
):
    """复核申诉（支持修改结果）"""
    appeal = db.query(AppealRecord).filter(AppealRecord.id == appeal_id).first()
    if not appeal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="申诉记录不存在")

    if appeal.record_id:
        check_record_not_archived(appeal.record_id, db)

    action = req.get("action")
    review_result = req.get("review_result")
    new_total_score = req.get("total_score")
    new_grade = req.get("grade")

    if action not in ("approve", "reject"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="action 必须是 approve 或 reject")

    # 终审只允许一次：已处理（resolved/rejected）的申诉不可重复复核
    if appeal.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"该申诉已完成终审（当前状态：{appeal.status}），不可重复复核",
        )

    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == appeal.record_id).first()
    old_values = {}
    if record:
        old_values = {
            "total_score": str(record.total_score) if record.total_score else None,
            "grade": record.grade,
            "status": record.status,
        }

    from datetime import datetime
    resolved_at = datetime.utcnow()

    appeal.status = "resolved" if action == "approve" else "rejected"
    appeal.review_result = review_result
    appeal.reviewer_id = user.employee_id or user.id
    appeal.resolved_at = resolved_at

    # 如果复核通过且传入了新分数/等级，更新考核记录
    if action == "approve" and record:
        if new_total_score is not None:
            record.total_score = new_total_score
        if new_grade is not None:
            record.grade = new_grade

    # 终审即结束申诉：考核记录从 appealed 回写为 published，避免记录滞留在申诉中
    if record and record.status == "appealed":
        record.status = "published"
        record.appeal_record = {
            "appeal_id": appeal.id,
            "action": action,
            "review_result": review_result,
            "resolved_at": resolved_at.isoformat(),
        }

    db.commit()
    db.refresh(appeal)

    # 通知申诉人复核结果
    employee_user = db.query(User).filter(User.employee_id == appeal.employee_id).first()
    if employee_user:
        create_notification(
            db=db,
            user_id=employee_user.id,
            title="申诉复核结果",
            content=f"您的申诉已完成终审，结果：{'复核通过' if action == 'approve' else '复核驳回'}。{review_result or ''}",
            type="appeal_resolved",
        )

    log_operation(
        db=db,
        user_id=user.id,
        action="review_appeal",
        target_type="appeal_record",
        target_id=appeal_id,
        old_value=old_values,
        new_value={
            "status": appeal.status,
            "action": action,
            "review_result": review_result,
            "total_score": str(record.total_score) if record else None,
            "grade": record.grade if record else None,
            "record_status": record.status if record else None,
        },
    )

    return {
        "id": appeal.id,
        "status": appeal.status,
        "review_result": appeal.review_result,
        "resolved_at": appeal.resolved_at.isoformat() if appeal.resolved_at else None,
    }


@router.post("/{appeal_id}/resolve")
def resolve_appeal(
    appeal_id: int,
    req: dict,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr")),
):
    """申诉复核（维持原结果或调整等级）"""
    appeal = db.query(AppealRecord).filter(AppealRecord.id == appeal_id).first()
    if not appeal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="申诉记录不存在")

    if appeal.record_id:
        check_record_not_archived(appeal.record_id, db)

    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == appeal.record_id).first()
    if not record or record.status != "appealed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该记录当前不处于申诉状态")

    resolution = req.get("resolution")
    new_grade = req.get("new_grade")
    comment = req.get("comment")

    if resolution not in ("maintain", "adjust"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="resolution 必须是 maintain 或 adjust")

    if resolution == "adjust" and not new_grade:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="adjust 时必须提供 new_grade")

    from datetime import datetime

    # 更新申诉记录
    appeal.status = "resolved"
    appeal.review_result = comment
    appeal.reviewer_id = user.employee_id or user.id
    appeal.resolved_at = datetime.utcnow()

    # 更新考核记录状态回 published
    record.status = "published"
    if resolution == "adjust":
        record.grade = new_grade
        record.appeal_record = {
            "appeal_id": appeal.id,
            "resolution": "adjust",
            "new_grade": new_grade,
            "comment": comment,
            "resolved_at": appeal.resolved_at.isoformat() if appeal.resolved_at else None,
        }
    else:
        record.appeal_record = {
            "appeal_id": appeal.id,
            "resolution": "maintain",
            "comment": comment,
            "resolved_at": appeal.resolved_at.isoformat() if appeal.resolved_at else None,
        }

    db.commit()
    db.refresh(appeal)

    # 通知员工复核结果
    create_notification(
        db=db,
        user_id=appeal.employee_id,
        title="申诉复核结果",
        content=f"您的申诉已复核，结果：{'维持原结果' if resolution == 'maintain' else '等级调整为 ' + new_grade}。",
        type="appeal_resolved",
    )

    log_operation(
        db=db,
        user_id=user.id,
        action="resolve_appeal",
        target_type="appeal_record",
        target_id=appeal_id,
        old_value={"status": "appealed", "grade": record.grade if resolution == "adjust" else None},
        new_value={"status": "published", "resolution": resolution, "grade": record.grade},
    )

    return {
        "id": appeal.id,
        "status": appeal.status,
        "resolution": resolution,
        "new_grade": record.grade if resolution == "adjust" else None,
        "resolved_at": appeal.resolved_at.isoformat() if appeal.resolved_at else None,
    }
