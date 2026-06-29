from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import AppealRecord, AssessmentRecord, Employee, User

router = APIRouter()

@router.get("")
def list_appeals(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr")),
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
    user = Depends(require_role("admin", "hr")),
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
    appeal = db.query(AppealRecord).filter(AppealRecord.id == appeal_id).first()
    if not appeal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="申诉记录不存在")

    action = req.get("action")
    review_result = req.get("review_result")

    if action not in ("approve", "reject"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="action 必须是 approve 或 reject")

    appeal.status = "resolved" if action == "approve" else "rejected"
    appeal.review_result = review_result
    appeal.reviewer_id = user.employee_id or user.id
    from datetime import datetime
    appeal.resolved_at = datetime.utcnow()

    db.commit()
    db.refresh(appeal)
    return {
        "id": appeal.id,
        "status": appeal.status,
        "review_result": appeal.review_result,
        "resolved_at": appeal.resolved_at.isoformat() if appeal.resolved_at else None,
    }
