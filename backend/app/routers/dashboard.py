from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import (
    AssessmentCycle, Employee, AssessmentRecord, CycleEmployee, ApprovalRecord, AppealRecord,
)

router = APIRouter()


@router.get("")
def get_dashboard(
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    if user.is_first_login:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="请先修改初始密码",
        )

    cycle_count = db.query(AssessmentCycle).count()
    employee_count = db.query(Employee).filter(Employee.is_active == True).count()
    pending_approvals = db.query(ApprovalRecord).filter(ApprovalRecord.action == None).count()
    pending_appeals = db.query(AppealRecord).filter(AppealRecord.status == "pending").count()

    recent_cycles = db.query(AssessmentCycle).order_by(AssessmentCycle.created_at.desc()).limit(5).all()

    return {
        "stats": {
            "total_cycles": cycle_count,
            "total_employees": employee_count,
            "pending_approvals": pending_approvals,
            "pending_appeals": pending_appeals,
        },
        "recent_cycles": [
            {
                "id": c.id,
                "name": c.name,
                "status": c.status,
                "start_date": str(c.start_date) if c.start_date else None,
                "end_date": str(c.end_date) if c.end_date else None,
            }
            for c in recent_cycles
        ],
        "pending_tasks": [],
    }


@router.get("/cycles")
def dashboard_cycles(
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr")),
):
    cycles = db.query(AssessmentCycle).all()
    return {
        "total": len(cycles),
        "by_status": {},
    }


@router.get("/approvals")
def dashboard_approvals(
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr", "manager")),
):
    pending = db.query(ApprovalRecord).filter(ApprovalRecord.action == None).count()
    return {"pending": pending}


@router.get("/scores")
def dashboard_scores(
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr", "manager")),
):
    total_records = db.query(AssessmentRecord).count()
    completed = db.query(AssessmentRecord).filter(AssessmentRecord.status == "published").count()
    return {
        "total": total_records,
        "completed": completed,
        "in_progress": total_records - completed,
    }
