from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import (
    AssessmentCycle, Employee, AssessmentRecord, CycleEmployee, ApprovalRecord, AppealRecord, InterviewRecord, User, PeerReviewer, Department
)
from app.routers.employees import get_all_dept_ids

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

    total_cycles = db.query(AssessmentCycle).count()

    stats = {
        "total_cycles": total_cycles,
        "total_employees": 0,
        "pending_approvals": 0,
        "pending_appeals": 0,
    }

    if user.role == "admin":
        stats["employee_count"] = db.query(Employee).filter(Employee.is_active == True).count()
        stats["department_count"] = db.query(Department).count()
        stats["cycle_count"] = total_cycles
        stats["active_cycle_count"] = db.query(AssessmentCycle).filter(
            AssessmentCycle.status.notin_(["not_started", "archived"])
        ).count()
        stats["total_employees"] = stats["employee_count"]
        stats["pending_approvals"] = db.query(ApprovalRecord).filter(ApprovalRecord.action == None).count()
        stats["pending_appeals"] = db.query(AppealRecord).filter(AppealRecord.status == "pending").count()

    elif user.role == "hr":
        stats["cycle_count"] = total_cycles
        stats["to_summary"] = db.query(AssessmentRecord).filter(
            AssessmentRecord.status.in_(["pending_summary", "pending_distribution_review"])
        ).count()
        stats["to_approve"] = db.query(AssessmentRecord).filter(
            AssessmentRecord.status == "pending_approval"
        ).count()
        stats["to_archive"] = db.query(AssessmentRecord).filter(
            AssessmentRecord.status == "published"
        ).count()
        stats["pending_appeals"] = db.query(AppealRecord).filter(
            AppealRecord.status == "pending"
        ).count()
        stats["force_distribution_exceeded"] = 0
        stats["total_employees"] = db.query(Employee).filter(Employee.is_active == True).count()
        stats["pending_approvals"] = stats["to_approve"]

    elif user.role == "executive":
        employee_count = db.query(Employee).filter(Employee.is_active == True).count()
        stats["employee_count"] = employee_count
        stats["total_employees"] = employee_count
        current_cycle = db.query(AssessmentCycle).filter(
            AssessmentCycle.status.notin_(["not_started", "archived"])
        ).order_by(AssessmentCycle.created_at.desc()).first()
        coverage_rate = 0
        if current_cycle and employee_count > 0:
            covered = db.query(AssessmentRecord).filter(
                AssessmentRecord.cycle_id == current_cycle.id
            ).count()
            coverage_rate = round(covered / employee_count * 100, 1)
        stats["coverage_rate"] = coverage_rate
        stats["avg_score"] = 0
        stats["adjusted_count"] = 0
        stats["pending_approvals"] = db.query(ApprovalRecord).filter(ApprovalRecord.action == None).count()
        stats["pending_appeals"] = db.query(AppealRecord).filter(AppealRecord.status == "pending").count()

    elif user.role == "manager":
        current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
        if current_employee:
            subordinate_ids = [sid[0] for sid in db.query(Employee.id).filter(Employee.manager_id == current_employee.id).all()]
            dept_ids = get_all_dept_ids(db, current_employee.department_id)
            dept_emp_ids = [eid[0] for eid in db.query(Employee.id).filter(Employee.department_id.in_(dept_ids)).all()]
            all_visible_ids = set(subordinate_ids) | set(dept_emp_ids) | {current_employee.id}
            stats["total_employees"] = len(all_visible_ids)
            stats["pending_approvals"] = db.query(ApprovalRecord).filter(
                ApprovalRecord.approver_id.in_(list(all_visible_ids)),
                ApprovalRecord.action == None
            ).count()
            stats["pending_appeals"] = db.query(AppealRecord).filter(
                AppealRecord.employee_id.in_(list(all_visible_ids)),
                AppealRecord.status == "pending"
            ).count()
        else:
            stats["total_employees"] = 0
            stats["pending_approvals"] = 0
            stats["pending_appeals"] = 0

    elif user.role in ("employee", "peer"):
        current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
        if current_employee:
            stats["total_employees"] = 1
            stats["pending_approvals"] = db.query(ApprovalRecord).filter(
                ApprovalRecord.approver_id == current_employee.id,
                ApprovalRecord.action == None
            ).count()
            stats["pending_appeals"] = db.query(AppealRecord).filter(
                AppealRecord.employee_id == current_employee.id,
                AppealRecord.status == "pending"
            ).count()
        else:
            stats["total_employees"] = 0
            stats["pending_approvals"] = 0
            stats["pending_appeals"] = 0

    recent_cycles = db.query(AssessmentCycle).order_by(AssessmentCycle.created_at.desc()).limit(5).all()

    return {
        "stats": stats,
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
    user = Depends(require_role("admin", "hr", "executive")),
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
        "to_approve": pending_approval,
        "to_interview": pending_interview,
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

    appeal_count = db.query(AppealRecord).filter(
        AppealRecord.employee_id == current_employee.id
    ).count()

    return {
        "current_cycle": current_record,
        "self_status": self_status,
        "total_records": total_records,
        "pending_self": pending_self,
        "appeal_count": appeal_count,
    }
