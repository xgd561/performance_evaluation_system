from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import (
    AssessmentCycle, Employee, AssessmentRecord, CycleEmployee, ApprovalRecord, AppealRecord, InterviewRecord, User, PeerReviewer
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


@router.get("/manager")
def dashboard_manager(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "admin", "hr")),
):
    """部门负责人仪表盘统计"""
    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        return {"to_review": 0, "pending_approval": 0, "pending_interview": 0, "subordinate_count": 0}

    subordinate_ids = db.query(Employee.id).filter(Employee.manager_id == current_employee.id).all()
    subordinate_ids = [sid[0] for sid in subordinate_ids]

    to_review = 0
    pending_approval = 0
    pending_interview = 0

    if subordinate_ids:
        to_review = db.query(AssessmentRecord).filter(
            AssessmentRecord.employee_id.in_(subordinate_ids),
            AssessmentRecord.status == "pending_manager"
        ).count()

        pending_approval = db.query(AssessmentRecord).filter(
            AssessmentRecord.employee_id.in_(subordinate_ids),
            AssessmentRecord.status.in_(["pending_peer", "pending_summary", "pending_approval"])
        ).count()

        pending_interview = db.query(AssessmentRecord).filter(
            AssessmentRecord.employee_id.in_(subordinate_ids),
            AssessmentRecord.status == "pending_interview"
        ).count()

    return {
        "to_review": to_review,
        "pending_approval": pending_approval,
        "pending_interview": pending_interview,
        "subordinate_count": len(subordinate_ids),
    }


@router.get("/peer")
def dashboard_peer(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("peer")),
):
    """协作人仪表盘统计"""
    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        return {"pending_reviews": 0, "completed_reviews": 0, "total_reviews": 0}

    total = db.query(PeerReviewer).filter(
        PeerReviewer.reviewer_id == current_employee.id
    ).count()

    completed = db.query(PeerReviewer).filter(
        PeerReviewer.reviewer_id == current_employee.id,
        PeerReviewer.status == "completed"
    ).count()

    pending = db.query(PeerReviewer).filter(
        PeerReviewer.reviewer_id == current_employee.id,
        PeerReviewer.status.in_(["pending", "in_progress"])
    ).count()

    return {
        "pending_reviews": pending,
        "completed_reviews": completed,
        "total_reviews": total,
    }


@router.get("/employee")
def dashboard_employee(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("employee")),
):
    """普通员工仪表盘统计"""
    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        return {"current_cycle": None, "self_status": "none", "total_records": 0, "pending_self": 0}

    # 获取当前进行中的考核周期
    current_cycle = db.query(AssessmentCycle).filter(
        AssessmentCycle.status.in_(["pending_self", "pending_manager", "pending_peer", "pending_summary", "pending_approval"])
    ).order_by(AssessmentCycle.created_at.desc()).first()

    total_records = db.query(AssessmentRecord).filter(
        AssessmentRecord.employee_id == current_employee.id
    ).count()

    pending_self = db.query(AssessmentRecord).filter(
        AssessmentRecord.employee_id == current_employee.id,
        AssessmentRecord.status == "pending_self"
    ).count()

    current_record = None
    self_status = "none"
    if current_cycle:
        record = db.query(AssessmentRecord).filter(
            AssessmentRecord.cycle_id == current_cycle.id,
            AssessmentRecord.employee_id == current_employee.id
        ).first()
        if record:
            current_record = {
                "record_id": record.id,
                "cycle_name": current_cycle.name,
                "status": record.status,
                "self_due_date": str(current_cycle.self_due_date) if current_cycle.self_due_date else None,
            }
            self_status = record.status

    return {
        "current_cycle": current_record,
        "self_status": self_status,
        "total_records": total_records,
        "pending_self": pending_self,
    }
