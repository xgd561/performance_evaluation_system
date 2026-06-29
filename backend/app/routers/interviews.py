from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import (
    AssessmentRecord, Employee, Department, Position, User, InterviewRecord,
    AssessmentCycle
)

router = APIRouter()

class InterviewCreate(BaseModel):
    interview_time: Optional[str] = None
    location: Optional[str] = None
    content: Optional[str] = None
    improvement_plan: Optional[str] = None

class InterviewUpdate(BaseModel):
    interview_time: Optional[str] = None
    location: Optional[str] = None
    content: Optional[str] = None
    improvement_plan: Optional[str] = None

@router.get("/pending")
def get_pending_interviews(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "hr", "admin")),
):
    """获取待面谈列表（已审批通过的下属）"""
    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工信息不存在")

    subordinate_ids = db.query(Employee.id).filter(Employee.manager_id == current_employee.id).all()
    subordinate_ids = [sid[0] for sid in subordinate_ids]

    if not subordinate_ids:
        return []

    records = db.query(AssessmentRecord).filter(
        AssessmentRecord.employee_id.in_(subordinate_ids),
        AssessmentRecord.status.in_(["pending_interview", "published"])
    ).all()

    result = []
    for r in records:
        emp = db.query(Employee).filter(Employee.id == r.employee_id).first()
        dept = db.query(Department).filter(Department.id == r.department_id).first()
        pos = db.query(Position).filter(Position.id == r.position_id).first()
        cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == r.cycle_id).first()
        interview = db.query(InterviewRecord).filter(InterviewRecord.record_id == r.id).first()

        result.append({
            "record_id": r.id,
            "cycle_id": r.cycle_id,
            "cycle_name": cycle.name if cycle else None,
            "employee_id": r.employee_id,
            "employee_name": emp.name if emp else None,
            "employee_no": emp.employee_no if emp else None,
            "department_name": dept.name if dept else None,
            "position_name": pos.name if pos else None,
            "total_score": str(r.total_score) if r.total_score else None,
            "grade": r.grade,
            "status": r.status,
            "has_interview": interview is not None,
            "interview_time": interview.interview_time.isoformat() if interview and interview.interview_time else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return result


@router.post("/{record_id}")
def create_interview(
    record_id: int,
    body: InterviewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "hr", "admin")),
):
    """创建面谈记录"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工信息不存在")

    if record.employee_id not in [e.id for e in current_employee.subordinates]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权为此员工创建面谈记录")

    grade = record.grade
    if grade in ["C", "D"] and not body.improvement_plan:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="C/D等级必须填写改进计划")

    interview = InterviewRecord(
        record_id=record_id,
        interviewer_id=current_employee.id,
        interview_time=datetime.fromisoformat(body.interview_time) if body.interview_time else None,
        location=body.location,
        content=body.content,
        improvement_plan=body.improvement_plan,
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)

    return {
        "id": interview.id,
        "record_id": interview.record_id,
        "interviewer_id": interview.interviewer_id,
        "interview_time": interview.interview_time.isoformat() if interview.interview_time else None,
        "location": interview.location,
        "content": interview.content,
        "improvement_plan": interview.improvement_plan,
        "created_at": interview.created_at.isoformat() if interview.created_at else None,
    }


@router.get("/{record_id}")
def get_interview(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "hr", "admin", "employee")),
):
    """获取面谈详情"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    interview = db.query(InterviewRecord).filter(InterviewRecord.record_id == record_id).first()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面谈记录不存在")

    return {
        "id": interview.id,
        "record_id": interview.record_id,
        "interviewer_id": interview.interviewer_id,
        "interviewer_name": interview.interviewer.name if interview.interviewer else None,
        "interview_time": interview.interview_time.isoformat() if interview.interview_time else None,
        "location": interview.location,
        "content": interview.content,
        "improvement_plan": interview.improvement_plan,
        "created_at": interview.created_at.isoformat() if interview.created_at else None,
    }


@router.put("/{record_id}")
def update_interview(
    record_id: int,
    body: InterviewUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "hr", "admin")),
):
    """更新面谈记录"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工信息不存在")

    interview = db.query(InterviewRecord).filter(InterviewRecord.record_id == record_id).first()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面谈记录不存在")

    if interview.interviewer_id != current_employee.id and user.role not in ["admin", "hr"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改此面谈记录")

    grade = record.grade
    if grade in ["C", "D"] and not body.improvement_plan and not interview.improvement_plan:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="C/D等级必须填写改进计划")

    if body.interview_time:
        interview.interview_time = datetime.fromisoformat(body.interview_time)
    if body.location is not None:
        interview.location = body.location
    if body.content is not None:
        interview.content = body.content
    if body.improvement_plan is not None:
        interview.improvement_plan = body.improvement_plan

    db.commit()
    db.refresh(interview)

    return {
        "id": interview.id,
        "record_id": interview.record_id,
        "interview_time": interview.interview_time.isoformat() if interview.interview_time else None,
        "location": interview.location,
        "content": interview.content,
        "improvement_plan": interview.improvement_plan,
        "created_at": interview.created_at.isoformat() if interview.created_at else None,
    }


@router.get("/employee/{employee_id}")
def get_employee_interview_history(
    employee_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "hr", "admin", "employee")),
):
    """获取员工面谈历史"""
    if user.role == "employee" and user.employee_id != employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看")

    records = db.query(AssessmentRecord).filter(AssessmentRecord.employee_id == employee_id).all()
    result = []
    for r in records:
        interview = db.query(InterviewRecord).filter(InterviewRecord.record_id == r.id).first()
        if interview:
            cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == r.cycle_id).first()
            result.append({
                "record_id": r.id,
                "cycle_name": cycle.name if cycle else None,
                "total_score": str(r.total_score) if r.total_score else None,
                "grade": r.grade,
                "interview_time": interview.interview_time.isoformat() if interview.interview_time else None,
                "location": interview.location,
                "content": interview.content,
                "improvement_plan": interview.improvement_plan,
                "created_at": interview.created_at.isoformat() if interview.created_at else None,
            })

    return result
