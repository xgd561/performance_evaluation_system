from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json
import logging
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import (
    AssessmentRecord, Employee, Department, Position, User, InterviewRecord,
    AssessmentCycle
)

from app.routers.employees import _is_in_subordinate_chain, get_descendant_dept_ids
from app.utils.workflow_state_machine import WorkflowStateMachine
from app.routers.archive_guard import check_record_not_archived
from app.services.notification_service import create_notification
from app.core.exceptions import BizError

logger = logging.getLogger(__name__)

router = APIRouter()
record_router = APIRouter()

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

class InterviewSubmit(BaseModel):
    interview_time: str
    location: str
    content: str
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

    check_record_not_archived(record_id, db)

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
    user: User = Depends(require_role("manager", "hr", "admin", "employee", "executive")),
):
    """获取面谈详情"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    interview = db.query(InterviewRecord).filter(InterviewRecord.record_id == record_id).first()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面谈记录不存在")

    # P0-9: Data isolation
    if user.role == "employee":
        if user.employee_id != record.employee_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看")
    elif user.role == "manager":
        current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
        if not current_employee:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问")
        # 本人、下属链、下级部门成员可见；同部门非下属不属授权范围
        allowed = (
            current_employee.id == record.employee_id
            or _is_in_subordinate_chain(db, current_employee.id, record.employee_id)
            or record.department_id in get_descendant_dept_ids(db, current_employee.department_id)
        )
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问")
    # admin, hr, executive: allow all

    interviewer = db.query(Employee).filter(Employee.id == interview.interviewer_id).first()

    return {
        "id": interview.id,
        "record_id": interview.record_id,
        "interviewer_id": interview.interviewer_id,
        "interviewer_name": interviewer.name if interviewer else None,
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

    check_record_not_archived(record_id, db)

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
    user: User = Depends(require_role("manager", "hr", "admin", "employee", "executive")),
):
    """获取员工面谈历史"""
    # P0-10: Data isolation
    if user.role == "employee":
        if user.employee_id != employee_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看")
    elif user.role == "manager":
        current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
        if not current_employee:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问")
        # 本人、下属链、下级部门成员可见；同部门非下属不属授权范围
        target_employee = db.query(Employee).filter(Employee.id == employee_id).first()
        allowed = (
            current_employee.id == employee_id
            or _is_in_subordinate_chain(db, current_employee.id, employee_id)
            or (
                target_employee is not None
                and target_employee.department_id
                in get_descendant_dept_ids(db, current_employee.department_id)
            )
        )
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问")
    # admin, hr, executive: allow all

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


# P5-13: GET /manager/interview-list
@router.get("/manager/interview-list")
def get_manager_interview_list(
    keyword: Optional[str] = Query(None, description="按员工姓名或工号搜索"),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "hr", "admin")),
):
    """
    获取当前经理的面谈列表。
    返回 pending（待面谈）和 completed（已完成）两个分区。
    """
    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工信息不存在")

    # 获取所有直接下属
    subordinates_query = db.query(Employee).filter(Employee.manager_id == current_employee.id)
    if keyword:
        subordinates_query = subordinates_query.filter(
            (Employee.name.ilike(f"%{keyword}%")) | (Employee.employee_no.ilike(f"%{keyword}%"))
        )
    subordinates = subordinates_query.all()
    subordinate_ids = [s.id for s in subordinates]

    if not subordinate_ids:
        return {"pending": [], "completed": []}

    # 查询这些下属的 AssessmentRecord
    records = db.query(AssessmentRecord).filter(
        AssessmentRecord.employee_id.in_(subordinate_ids)
    ).all()

    pending = []
    completed = []

    for r in records:
        emp = db.query(Employee).filter(Employee.id == r.employee_id).first()
        dept = db.query(Department).filter(Department.id == r.department_id).first()
        pos = db.query(Position).filter(Position.id == r.position_id).first()
        cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == r.cycle_id).first()

        is_highlight = r.grade in ["C", "D"]

        item = {
            "record_id": r.id,
            "employee_id": r.employee_id,
            "employee_name": emp.name if emp else None,
            "employee_no": emp.employee_no if emp else None,
            "department_name": dept.name if dept else None,
            "position_name": pos.name if pos else None,
            "cycle_name": cycle.name if cycle else None,
            "total_score": float(r.total_score) if r.total_score is not None else None,
            "grade": r.grade,
            "is_highlight": is_highlight,
            "status": r.status,
        }

        if r.status == "pending_interview":
            pending.append(item)
        elif r.status == "published" and (r.interview_record is not None or db.query(InterviewRecord).filter(InterviewRecord.record_id == r.id).first() is not None):
            completed.append(item)

    return {"pending": pending, "completed": completed}


# P5-12: POST /api/v1/assessment-records/{id}/interview
@record_router.post("/{id}/interview")
def submit_interview(
    id: int,
    body: InterviewSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "hr", "admin")),
):
    """
    提交绩效面谈记录。
    校验状态、权限、面谈时间、沟通内容、改进计划（C/D等级），
    写入 interview_record JSON 字段，更新状态为 published，发送通知。
    """
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    check_record_not_archived(id, db)

    # 1. 校验状态
    if record.status != "pending_interview":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="当前状态不允许提交面谈")

    # 2. 校验权限：当前登录用户必须是该员工的直属上级
    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工信息不存在")

    employee = db.query(Employee).filter(Employee.id == record.employee_id).first()
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工信息不存在")

    if user.role not in ["admin", "hr"] and current_employee.id != employee.manager_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权为此员工提交面谈记录")

    # 3. 校验面谈时间
    try:
        interview_time = datetime.fromisoformat(body.interview_time)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="面谈时间格式错误")

    if interview_time > datetime.now():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="面谈时间不能晚于当前时间")

    # 4. 校验沟通内容长度
    if not body.content or len(body.content) < 50:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="沟通内容至少 50 个字符")

    # 5. 校验改进计划（C/D等级）
    if record.grade in ["C", "D"]:
        if not body.improvement_plan or len(body.improvement_plan) < 30:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="C/D等级必须填写改进计划且至少30个字符")

    # 6. 写入 interview_record JSON 字段
    record.interview_record = {
        "interview_time": body.interview_time,
        "location": body.location,
        "content": body.content,
        "improvement_plan": body.improvement_plan,
        "interviewer_id": current_employee.id,
        "interviewer_name": current_employee.name,
    }

    # 7. 更新状态：使用状态机转换
    try:
        new_status = WorkflowStateMachine.transition(
            current_state="pending_interview",
            action="submit_interview",
            db=db,
            user_id=user.id,
            target_id=id,
        )
    except BizError as e:
        # 回滚 JSON 写入，保持原子性
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message)

    record.status = new_status

    # 8. 发送通知（给员工）
    employee_user = db.query(User).filter(User.employee_id == employee.id).first()
    if employee_user:
        try:
            create_notification(
                db=db,
                user_id=employee_user.id,
                title="绩效结果已发布",
                content=f"您的绩效面谈结果已发布，考核等级：{record.grade}。",
                type="performance",
            )
        except Exception:
            # 通知发送失败不阻断主流程，但保留告警日志便于排查
            logger.warning("面谈结果发布通知发送失败：record_id=%s", record.id, exc_info=True)
    else:
        # 员工尚未开通登录账号，无法投递站内信；记录告警供 HR 补建账号
        logger.warning("员工未绑定系统账号，跳过面谈结果通知：employee_id=%s", employee.id)

    db.commit()
    db.refresh(record)

    # 9. 返回更新后的 AssessmentRecord 详情
    return {
        "id": record.id,
        "cycle_id": record.cycle_id,
        "employee_id": record.employee_id,
        "status": record.status,
        "total_score": float(record.total_score) if record.total_score is not None else None,
        "grade": record.grade,
        "interview_record": record.interview_record,
    }
