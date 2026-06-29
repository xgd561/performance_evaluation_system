from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from collections import Counter
import json

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import (
    AssessmentRecord, AssessmentCycle, Employee, Department, User
)

router = APIRouter()


@router.get("/cycle/{cycle_id}/distribution")
def get_distribution(
    cycle_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr", "manager")),
):
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核周期不存在")

    records = db.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == cycle_id).all()

    # Group by department
    dept_stats = {}
    for r in records:
        dept_id = r.department_id or 0
        if dept_id not in dept_stats:
            dept = db.query(Department).filter(Department.id == dept_id).first()
            dept_stats[dept_id] = {
                "department_name": dept.name if dept else "未分配",
                "total": 0,
                "grades": Counter(),
                "avg_score": 0,
                "scores": [],
            }
        dept_stats[dept_id]["total"] += 1
        dept_stats[dept_id]["grades"][r.grade or "未评级"] += 1
        if r.total_score:
            dept_stats[dept_id]["scores"].append(float(r.total_score))

    for d in dept_stats.values():
        if d["scores"]:
            d["avg_score"] = round(sum(d["scores"]) / len(d["scores"]), 1)
        del d["scores"]

    overall_grades = Counter(r.grade or "未评级" for r in records)

    return {
        "cycle_id": cycle_id,
        "cycle_name": cycle.name,
        "total_records": len(records),
        "overall_distribution": dict(overall_grades),
        "department_stats": [
            {
                "department_id": k,
                "department_name": v["department_name"],
                "total": v["total"],
                "grades": dict(v["grades"]),
                "avg_score": v["avg_score"],
            }
            for k, v in dept_stats.items()
        ],
    }


@router.get("/cycle/{cycle_id}/export")
def export_cycle_report(
    cycle_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr")),
):
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核周期不存在")

    records = db.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == cycle_id).all()

    rows = []
    for r in records:
        emp = db.query(Employee).filter(Employee.id == r.employee_id).first()
        dept = db.query(Department).filter(Department.id == r.department_id).first()
        rows.append({
            "工号": emp.employee_no if emp else "",
            "姓名": emp.name if emp else "",
            "部门": dept.name if dept else "",
            "总分": str(r.total_score) if r.total_score else "",
            "等级": r.grade or "",
            "原始等级": r.original_grade or "",
            "业绩分": str(r.weighted_performance) if r.weighted_performance else "",
            "能力分": str(r.weighted_ability) if r.weighted_ability else "",
            "态度分": str(r.weighted_attitude) if r.weighted_attitude else "",
            "状态": r.status or "",
            "是否特批": "是" if r.is_distribution_override else "否",
        })

    return {
        "cycle_id": cycle_id,
        "cycle_name": cycle.name,
        "total": len(rows),
        "rows": rows,
    }

@router.get("/employee/{employee_id}/trend")
def get_employee_trend(
    employee_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取员工历史绩效趋势"""
    # 权限校验：只能查看自己或下属（上级/hr/admin）
    if user.role == "employee":
        if user.employee_id != employee_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能查看本人的绩效趋势")

    records = db.query(AssessmentRecord).filter(
        AssessmentRecord.employee_id == employee_id
    ).order_by(AssessmentRecord.created_at.asc()).limit(8).all()

    result = []
    for r in records:
        cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == r.cycle_id).first()
        self_scores = json.loads(r.self_scores) if r.self_scores else {}
        manager_scores = json.loads(r.manager_scores) if r.manager_scores else {}
        peer_scores = json.loads(r.peer_scores) if r.peer_scores else {}

        result.append({
            "record_id": r.id,
            "cycle_id": r.cycle_id,
            "cycle_name": cycle.name if cycle else None,
            "cycle_type": cycle.type if cycle else None,
            "self_scores": self_scores,
            "manager_scores": manager_scores,
            "peer_scores": peer_scores,
            "weighted_performance": str(r.weighted_performance) if r.weighted_performance else None,
            "weighted_ability": str(r.weighted_ability) if r.weighted_ability else None,
            "weighted_attitude": str(r.weighted_attitude) if r.weighted_attitude else None,
            "total_score": str(r.total_score) if r.total_score else None,
            "grade": r.grade,
            "original_grade": r.original_grade,
            "status": r.status,
            "manager_comment": r.manager_comment,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return {"items": result, "total": len(result)}
