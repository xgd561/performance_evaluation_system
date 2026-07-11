from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from collections import Counter
from datetime import date, datetime
import json

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import (
    AssessmentCycle, Employee, AssessmentRecord, CycleEmployee, KpiTemplate, Position, Department, User,
)
from app.schemas import (
    AssessmentCycleCreate,
    AssessmentCycleUpdate,
    AssessmentCycleOut,
    LaunchCycleRequest,
    AddEmployeesToCycleRequest,
    StandardResponse,
    CycleEmployeeOut,
)

from app.services.operation_logger import log_operation
from app.services.notification_service import create_notification
from app.utils.workflow_state_machine import WorkflowStateMachine
from app.utils.pdf_generator import generate_performance_pdf
from app.services.pdf_archive_generator import generate_archive_pdf
from app.utils.pdf_generator import generate_performance_pdf
from app.utils.pdf_generator import generate_performance_pdf
from app.utils.pdf_generator import generate_performance_pdf
from app.utils.pdf_generator import generate_performance_pdf


def _parse_json_field(value):
    """安全解析 JSON 字段：兼容字符串和已反序列化的 dict/list"""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return value


router = APIRouter()


@router.get("")
def list_cycles(
    status: Optional[str] = Query(None, description="按状态筛选"),
    type: Optional[str] = Query(None, description="按类型筛选"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    page: Optional[int] = Query(None, ge=1, description="页码"),
    size: Optional[int] = Query(None, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    query = db.query(AssessmentCycle).order_by(AssessmentCycle.created_at.desc())
    if status:
        query = query.filter(AssessmentCycle.status == status)
    if type:
        query = query.filter(AssessmentCycle.type == type)
    if start_date:
        query = query.filter(AssessmentCycle.start_date >= start_date)
    if end_date:
        query = query.filter(AssessmentCycle.end_date <= end_date)

    if page and size:
        total = query.count()
        cycles = query.offset((page - 1) * size).limit(size).all()
        items = []
        for c in cycles:
            items.append({
                "id": c.id,
                "name": c.name,
                "type": c.type,
                "start_date": str(c.start_date) if c.start_date else None,
                "end_date": str(c.end_date) if c.end_date else None,
                "self_due_date": str(c.self_due_date) if c.self_due_date else None,
                "manager_due_date": str(c.manager_due_date) if c.manager_due_date else None,
                "peer_due_date": str(c.peer_due_date) if c.peer_due_date else None,
                "status": c.status,
                "weights": _parse_json_field(c.dimension_weights),
                "grade_rules": _parse_json_field(c.grade_rules),
                "is_distribution_enabled": c.is_distribution_enabled,
                "small_dept_exemption": c.small_dept_exemption,
                "peer_review_enabled": c.peer_review_enabled,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            })
        return {"total": total, "page": page, "size": size, "items": items}

    cycles = query.all()
    result = []
    for c in cycles:
        result.append({
            "id": c.id,
            "name": c.name,
            "type": c.type,
            "start_date": str(c.start_date) if c.start_date else None,
            "end_date": str(c.end_date) if c.end_date else None,
            "self_due_date": str(c.self_due_date) if c.self_due_date else None,
            "manager_due_date": str(c.manager_due_date) if c.manager_due_date else None,
            "peer_due_date": str(c.peer_due_date) if c.peer_due_date else None,
            "status": c.status,
            "weights": _parse_json_field(c.dimension_weights),
            "grade_rules": _parse_json_field(c.grade_rules),
            "is_distribution_enabled": c.is_distribution_enabled,
            "small_dept_exemption": c.small_dept_exemption,
            "peer_review_enabled": c.peer_review_enabled,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })
    return result


@router.get("/{cycle_id}")
def get_cycle_detail(
    cycle_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    """查询考核周期详情，含考核对象部门列表"""
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核周期不存在")

    # 获取考核对象部门列表
    cycle_employees = db.query(CycleEmployee).filter(CycleEmployee.cycle_id == cycle_id).all()
    emp_ids = [ce.employee_id for ce in cycle_employees]
    departments = []
    if emp_ids:
        employees = db.query(Employee).filter(Employee.id.in_(emp_ids)).all()
        dept_ids = {emp.department_id for emp in employees if emp.department_id}
        if dept_ids:
            depts = db.query(Department).filter(Department.id.in_(dept_ids)).all()
            departments = [{"id": d.id, "name": d.name, "code": d.code} for d in depts]

    return {
        "id": cycle.id,
        "name": cycle.name,
        "type": cycle.type,
        "start_date": str(cycle.start_date) if cycle.start_date else None,
        "end_date": str(cycle.end_date) if cycle.end_date else None,
        "self_due_date": str(cycle.self_due_date) if cycle.self_due_date else None,
        "manager_due_date": str(cycle.manager_due_date) if cycle.manager_due_date else None,
        "peer_due_date": str(cycle.peer_due_date) if cycle.peer_due_date else None,
        "status": cycle.status,
        "weights": _parse_json_field(cycle.dimension_weights),
        "grade_rules": _parse_json_field(cycle.grade_rules),
        "is_distribution_enabled": cycle.is_distribution_enabled,
        "small_dept_exemption": cycle.small_dept_exemption,
        "peer_review_enabled": cycle.peer_review_enabled,
        "created_at": cycle.created_at.isoformat() if cycle.created_at else None,
        "departments": departments,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_cycle(
    req: AssessmentCycleCreate,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr")),
):
    # Normalize grade_rules to detailed format
    raw_grade_rules = req.grade_rules
    normalized_grade_rules = {}
    for grade, value in raw_grade_rules.items():
        if isinstance(value, dict):
            normalized_grade_rules[grade] = value
        elif isinstance(value, (int, float)):
            if grade == "A":
                normalized_grade_rules[grade] = {"min": value, "max": 100}
            elif grade == "B":
                normalized_grade_rules[grade] = {"min": value, "max": 89.9}
            elif grade == "C":
                normalized_grade_rules[grade] = {"min": value, "max": 79.9}
            elif grade == "D":
                normalized_grade_rules[grade] = {"min": value, "max": 59.9}
            else:
                normalized_grade_rules[grade] = {"min": value, "max": 100}
        else:
            normalized_grade_rules[grade] = {"min": 0, "max": 100}

    # 校验名称唯一性
    existing = db.query(AssessmentCycle).filter(AssessmentCycle.name == req.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="考核周期名称已存在")

    cycle = AssessmentCycle(
        name=req.name,
        type=req.type,
        start_date=req.start_date,
        end_date=req.end_date,
        self_due_date=req.self_due_date,
        manager_due_date=req.manager_due_date,
        peer_due_date=req.peer_due_date,
        status="not_started",
        dimension_weights=json.dumps({"performance": 50, "ability": 30, "attitude": 20}),
        reviewer_weights=json.dumps(req.weights),
        grade_rules=json.dumps(normalized_grade_rules),
        small_dept_exemption=req.small_dept_exemption if req.small_dept_exemption is not None else True,
        peer_review_enabled=req.peer_review_enabled if req.peer_review_enabled is not None else True,
    )
    db.add(cycle)
    db.commit()
    db.refresh(cycle)
    return {
        "id": cycle.id,
        "name": cycle.name,
        "type": cycle.type,
        "start_date": str(cycle.start_date),
        "end_date": str(cycle.end_date),
        "self_due_date": str(cycle.self_due_date) if cycle.self_due_date else None,
        "manager_due_date": str(cycle.manager_due_date) if cycle.manager_due_date else None,
        "peer_due_date": str(cycle.peer_due_date) if cycle.peer_due_date else None,
        "status": "未开始",
        "weights": req.weights,
        "grade_rules": raw_grade_rules,
        "peer_review_enabled": cycle.peer_review_enabled,
        "created_at": cycle.created_at.isoformat() if cycle.created_at else None,
    }


@router.put("/{cycle_id}")
def update_cycle(
    cycle_id: int,
    req: AssessmentCycleUpdate,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr")),
):
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核周期不存在")

    if cycle.status != "not_started":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="已发起的考核周期不可修改")

    for field, value in req.model_dump(exclude_unset=True).items():
        if field == "weights":
            setattr(cycle, "reviewer_weights", json.dumps(value))
        elif field == "grade_rules":
            setattr(cycle, "grade_rules", json.dumps(value))
        elif field == "small_dept_exemption":
            setattr(cycle, "small_dept_exemption", value)
        elif field == "peer_review_enabled":
            setattr(cycle, "peer_review_enabled", value)
        else:
            setattr(cycle, field, value)
    db.commit()
    db.refresh(cycle)

    log_operation(
        db=db,
        user_id=user.id,
        action="update_cycle",
        target_type="assessment_cycle",
        target_id=cycle_id,
        old_value={"name": cycle.name},
        new_value={"name": cycle.name, "status": cycle.status},
    )

    return {
        "id": cycle.id,
        "name": cycle.name,
        "type": cycle.type,
        "start_date": str(cycle.start_date) if cycle.start_date else None,
        "end_date": str(cycle.end_date) if cycle.end_date else None,
        "self_due_date": str(cycle.self_due_date) if cycle.self_due_date else None,
        "manager_due_date": str(cycle.manager_due_date) if cycle.manager_due_date else None,
        "peer_due_date": str(cycle.peer_due_date) if cycle.peer_due_date else None,
        "status": cycle.status,
        "weights": _parse_json_field(cycle.dimension_weights),
        "grade_rules": _parse_json_field(cycle.grade_rules),
        "is_distribution_enabled": cycle.is_distribution_enabled,
        "small_dept_exemption": cycle.small_dept_exemption,
        "peer_review_enabled": cycle.peer_review_enabled,
        "created_at": cycle.created_at.isoformat() if cycle.created_at else None,
    }


@router.delete("/{cycle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cycle(
    cycle_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr")),
):
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核周期不存在")

    if cycle.status != "not_started":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只有未开始的考核周期才能删除")

    records = db.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == cycle_id).first()
    if records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该周期已包含考核数据，不可删除",
        )

    db.delete(cycle)
    db.commit()
    return


@router.post("/launch")
def launch_cycle(
    req: LaunchCycleRequest,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr")),
):
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == req.cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核周期不存在")

    if not req.employee_ids:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="至少选择一名员工")

    employees = db.query(Employee).filter(Employee.id.in_(req.employee_ids), Employee.is_active == True).all()
    if len(employees) != len(req.employee_ids):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="部分员工不存在或已离职")

    created = 0
    for emp in employees:
        # Check if already in cycle
        ce = db.query(CycleEmployee).filter(
            CycleEmployee.cycle_id == cycle.id,
            CycleEmployee.employee_id == emp.id,
        ).first()
        if not ce:
            ce = CycleEmployee(cycle_id=cycle.id, employee_id=emp.id, status="pending")
            db.add(ce)

        # Check if record exists
        record = db.query(AssessmentRecord).filter(
            AssessmentRecord.cycle_id == cycle.id,
            AssessmentRecord.employee_id == emp.id,
        ).first()
        if not record:
            kpi_templates = db.query(KpiTemplate).filter(
                KpiTemplate.position_id == emp.position_id,
                KpiTemplate.is_active == True,
            ).all()

            record = AssessmentRecord(
                cycle_id=cycle.id,
                employee_id=emp.id,
                position_id=emp.position_id,
                department_id=emp.department_id,
                status="pending_self",
                kpi_snapshot=json.dumps([{"name": k.name, "weight": str(k.weight), "target_value": k.target_value} for k in kpi_templates]) if kpi_templates else None,
            )
            db.add(record)
            created += 1

    cycle.status = "pending_self"
    db.commit()

    # 发送通知给相关员工
    for emp in employees:
        emp_user = db.query(User).filter(User.employee_id == emp.id).first()
        if emp_user:
            create_notification(
                db=db,
                user_id=emp_user.id,
                title=f"考核周期「{cycle.name}」已启动",
                content=f"请尽快完成「{cycle.name}」的自评。",
                type="cycle_start",
            )

    log_operation(
        db=db,
        user_id=user.id,
        action="launch_cycle",
        target_type="assessment_cycle",
        target_id=cycle.id,
        old_value={"status": "not_started"},
        new_value={"status": "pending_self", "created_records": created, "employee_ids": req.employee_ids},
    )

    return {"created_records": created, "status": "进行中（自评）"}


@router.post("/{cycle_id}/start")
def start_cycle(
    cycle_id: int,
    req: LaunchCycleRequest,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr")),
):
    """启动考核周期（RESTful 风格）：验证、创建记录、KPI 快照、发送通知"""
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核周期不存在")

    if not req.employee_ids:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="至少选择一名员工")

    employees = db.query(Employee).filter(Employee.id.in_(req.employee_ids), Employee.is_active == True).all()
    if len(employees) != len(req.employee_ids):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="部分员工不存在或已离职")

    created = 0
    for emp in employees:
        ce = db.query(CycleEmployee).filter(
            CycleEmployee.cycle_id == cycle.id,
            CycleEmployee.employee_id == emp.id,
        ).first()
        if not ce:
            ce = CycleEmployee(cycle_id=cycle.id, employee_id=emp.id, status="pending")
            db.add(ce)

        record = db.query(AssessmentRecord).filter(
            AssessmentRecord.cycle_id == cycle.id,
            AssessmentRecord.employee_id == emp.id,
        ).first()
        if not record:
            kpi_templates = db.query(KpiTemplate).filter(
                KpiTemplate.position_id == emp.position_id,
                KpiTemplate.is_active == True,
            ).all()

            record = AssessmentRecord(
                cycle_id=cycle.id,
                employee_id=emp.id,
                position_id=emp.position_id,
                department_id=emp.department_id,
                status="pending_self",
                kpi_snapshot=json.dumps([{"name": k.name, "weight": str(k.weight), "target_value": k.target_value} for k in kpi_templates]) if kpi_templates else None,
            )
            db.add(record)
            created += 1

    # 使用状态机执行状态转换（自动校验并返回目标状态）
    next_state = WorkflowStateMachine.transition(
        current_state=cycle.status,
        action="start_cycle",
    )
    cycle.status = next_state
    db.commit()

    # 发送通知给相关员工
    for emp in employees:
        emp_user = db.query(User).filter(User.employee_id == emp.id).first()
        if emp_user:
            create_notification(
                db=db,
                user_id=emp_user.id,
                title=f"考核周期「{cycle.name}」已启动",
                content=f"请尽快完成「{cycle.name}」的自评。",
                type="cycle_start",
            )

    log_operation(
        db=db,
        user_id=user.id,
        action="start_cycle",
        target_type="assessment_cycle",
        target_id=cycle.id,
        old_value={"status": "not_started"},
        new_value={"status": next_state, "created_records": created, "employee_ids": req.employee_ids},
    )

    return {"created_records": created, "status": "进行中（自评）"}


@router.post("/add-employees")
def add_employees_to_cycle(
    req: AddEmployeesToCycleRequest,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr")),
):
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == req.cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核周期不存在")

    for emp_id in req.employee_ids:
        emp = db.query(Employee).filter(Employee.id == emp_id, Employee.is_active == True).first()
        if not emp:
            continue
        ce = db.query(CycleEmployee).filter(
            CycleEmployee.cycle_id == cycle.id,
            CycleEmployee.employee_id == emp.id,
        ).first()
        if not ce:
            ce = CycleEmployee(cycle_id=cycle.id, employee_id=emp.id, status="pending")
            db.add(ce)
        record = db.query(AssessmentRecord).filter(
            AssessmentRecord.cycle_id == cycle.id,
            AssessmentRecord.employee_id == emp.id,
        ).first()
        if not record:
            record = AssessmentRecord(
                cycle_id=cycle.id,
                employee_id=emp.id,
                position_id=emp.position_id,
                department_id=emp.department_id,
                status="pending_self",
            )
            db.add(record)
    db.commit()

    cycle_employees = db.query(CycleEmployee).filter(CycleEmployee.cycle_id == cycle.id).all()
    return {
        "employees": [
            {"id": ce.employee_id, "status": ce.status}
            for ce in cycle_employees
        ]
    }


@router.delete("/{cycle_id}/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_employee_from_cycle(
    cycle_id: int,
    employee_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr")),
):
    ce = db.query(CycleEmployee).filter(
        CycleEmployee.cycle_id == cycle_id,
        CycleEmployee.employee_id == employee_id,
    ).first()
    if ce:
        db.delete(ce)
    db.commit()
    return


@router.get("/{cycle_id}/employees", response_model=List[CycleEmployeeOut])
def list_cycle_employees(
    cycle_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr")),
):
    """查询考核周期已参与人员列表"""
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核周期不存在")

    cycle_employees = (
        db.query(CycleEmployee)
        .filter(CycleEmployee.cycle_id == cycle_id)
        .all()
    )

    result = []
    for ce in cycle_employees:
        emp = db.query(Employee).filter(Employee.id == ce.employee_id).first()
        dept_name = emp.department.name if emp and emp.department else None
        pos_name = emp.position.name if emp and emp.position else None
        result.append({
            "id": ce.id,
            "cycle_id": ce.cycle_id,
            "employee_id": ce.employee_id,
            "employee_no": emp.employee_no if emp else None,
            "name": emp.name if emp else None,
            "department_id": emp.department_id if emp else None,
            "department_name": dept_name,
            "position_id": emp.position_id if emp else None,
            "position_name": pos_name,
            "status": ce.status,
            "added_at": ce.added_at,
        })

    return result


@router.get("/{cycle_id}/progress")
def cycle_progress(
    cycle_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr", "executive")),
):
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核周期不存在")

    total = db.query(CycleEmployee).filter(CycleEmployee.cycle_id == cycle_id).count()
    completed = db.query(AssessmentRecord).filter(
        AssessmentRecord.cycle_id == cycle_id,
        AssessmentRecord.status.in_(["published", "archived"]),
    ).count()
    progress = round((completed / total * 100), 1) if total > 0 else 0

    records = db.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == cycle_id).all()
    status_counts = Counter(r.status for r in records)
    total_records = len(records)

    def _stage_status(completed_statuses, active_statuses=None):
        if total_records == 0:
            return "pending"
        completed_count = sum(status_counts[s] for s in completed_statuses)
        active_count = sum(status_counts[s] for s in (active_statuses or []))
        if completed_count == total_records:
            return "completed"
        if active_count > 0 or completed_count > 0:
            return "in_progress"
        return "pending"

    stages = [
        {
            "name": "自评",
            "status": _stage_status(
                completed_statuses=["pending_manager", "pending_peer", "pending_summary", "pending_approval", "pending_interview", "published", "archived", "cancelled"],
            ),
        },
        {
            "name": "上级评",
            "status": _stage_status(
                completed_statuses=["pending_peer", "pending_summary", "pending_approval", "pending_interview", "published", "archived", "cancelled"],
                active_statuses=["pending_manager"],
            ),
        },
        {
            "name": "协作评",
            "status": _stage_status(
                completed_statuses=["pending_summary", "pending_approval", "pending_interview", "published", "archived", "cancelled"],
                active_statuses=["pending_peer"],
            ),
        },
        {
            "name": "汇总",
            "status": _stage_status(
                completed_statuses=["pending_approval", "pending_interview", "published", "archived", "cancelled"],
                active_statuses=["pending_summary"],
            ),
        },
        {
            "name": "审批",
            "status": _stage_status(
                completed_statuses=["pending_interview", "published", "archived", "cancelled"],
                active_statuses=["pending_approval"],
            ),
        },
    ]

    # ---------- P3-06: 详细进度监控数据 ----------
    def _rate(completed_statuses):
        if total_records == 0:
            return 0.0
        return round(sum(status_counts[s] for s in completed_statuses) / total_records * 100, 1)

    self_completed_statuses = ["pending_manager", "pending_peer", "pending_summary", "pending_approval", "pending_interview", "published", "archived", "cancelled"]
    manager_completed_statuses = ["pending_peer", "pending_summary", "pending_approval", "pending_interview", "published", "archived", "cancelled"]
    peer_completed_statuses = ["pending_summary", "pending_approval", "pending_interview", "published", "archived", "cancelled"]

    self_completion_rate = _rate(self_completed_statuses)
    manager_completion_rate = _rate(manager_completed_statuses)
    peer_completion_rate = _rate(peer_completed_statuses) if cycle.peer_review_enabled else 100.0

    # 各部门完成率（按自评完成率计算）
    department_stats = {}
    for record in records:
        dept_id = record.department_id
        if dept_id not in department_stats:
            department_stats[dept_id] = {"total": 0, "completed": 0}
        department_stats[dept_id]["total"] += 1
        if record.status in self_completed_statuses:
            department_stats[dept_id]["completed"] += 1

    department_completion = []
    for dept_id, stats in department_stats.items():
        dept = db.query(Department).filter(Department.id == dept_id).first()
        department_completion.append({
            "department_id": dept_id,
            "department_name": dept.name if dept else "未知部门",
            "total": stats["total"],
            "completed": stats["completed"],
            "rate": round(stats["completed"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0.0,
        })

    # 未完成人员名单（当前阶段未完成）
    incomplete_employees = []
    for record in records:
        if record.status in ["pending_self", "pending_manager", "pending_peer", "pending_summary", "pending_approval", "pending_interview"]:
            emp = db.query(Employee).filter(Employee.id == record.employee_id).first()
            dept = db.query(Department).filter(Department.id == record.department_id).first() if emp else None
            stage_map = {
                "pending_self": "自评",
                "pending_manager": "上级评",
                "pending_peer": "协作评",
                "pending_summary": "汇总",
                "pending_approval": "审批",
                "pending_interview": "待发布",
            }
            incomplete_employees.append({
                "employee_id": record.employee_id,
                "employee_name": emp.name if emp else "未知",
                "employee_no": emp.employee_no if emp else "",
                "department_name": dept.name if dept else "",
                "current_stage": stage_map.get(record.status, record.status),
                "status": record.status,
            })

    return {
        "cycle_id": cycle_id,
        "status": cycle.status,
        "stages": stages,
        "overall_progress": progress,
        "total_employees": total,
        "completed": completed,
        "last_updated": cycle.updated_at.isoformat() if cycle.updated_at else cycle.created_at.isoformat() if cycle.created_at else None,
        "self_completion_rate": self_completion_rate,
        "manager_completion_rate": manager_completion_rate,
        "peer_completion_rate": peer_completion_rate,
        "department_completion": department_completion,
        "incomplete_employees": incomplete_employees,
    }


@router.post("/{cycle_id}/cancel")
def cancel_cycle(
    cycle_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr")),
):
    """取消考核周期"""
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核周期不存在")

    cycle.status = "cancelled"
    db.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == cycle_id).update({"status": "cancelled"})
    db.commit()

    log_operation(
        db=db,
        user_id=user.id,
        action="cancel_cycle",
        target_type="assessment_cycle",
        target_id=cycle_id,
        new_value={"status": "cancelled"},
    )

    return {"message": "考核周期已取消", "cycle_id": cycle_id}


@router.post("/{cycle_id}/archive")
def archive_cycle(
    cycle_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr")),
):
    """归档考核周期"""
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核周期不存在")

    if cycle.status not in ["published"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="只有已发布的考核周期才能归档")

    cycle.status = "archived"
    cycle.is_locked = True
    cycle.archived_at = datetime.utcnow()

    # Lock all assessment records in this cycle
    records = db.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == cycle_id).all()
    for record in records:
        record.is_locked = True

    db.commit()

    # Trigger async PDF archive generation for each record
    def _generate_pdfs_task(cid: int):
        from app.database import SessionLocal
        local_db = SessionLocal()
        try:
            recs = local_db.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == cid).all()
            for rec in recs:
                try:
                    path = generate_archive_pdf(rec.id, local_db)
                    if path:
                        rec.archive_pdf_path = path
                except Exception:
                    # 单条记录 PDF 生成失败不应影响其他记录
                    pass
            local_db.commit()
        finally:
            local_db.close()

    background_tasks.add_task(_generate_pdfs_task, cycle_id)

    log_operation(
        db=db,
        user_id=user.id,
        action="archive_cycle",
        target_type="assessment_cycle",
        target_id=cycle_id,
        new_value={"status": "archived", "is_locked": True, "archived_at": cycle.archived_at.isoformat()},
    )

    return {"message": "考核周期已归档", "cycle_id": cycle_id}


@router.post("/{cycle_id}/unarchive")
def unarchive_cycle(
    cycle_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin")),
):
    """解冻考核周期（仅 admin）"""
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核周期不存在")

    if cycle.status != "archived":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="只有已归档的考核周期才能解冻")

    cycle.status = "published"
    cycle.is_locked = False

    # Unlock all assessment records in this cycle
    records = db.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == cycle_id).all()
    for record in records:
        record.is_locked = False

    db.commit()

    log_operation(
        db=db,
        user_id=user.id,
        action="unarchive_cycle",
        target_type="assessment_cycle",
        target_id=cycle_id,
        old_value={"status": "archived", "is_locked": True},
        new_value={"status": "published", "is_locked": False},
    )

    return {"message": "考核周期已解冻", "cycle_id": cycle_id}


@router.get("/{cycle_id}/export-excel")
def export_cycle_excel(
    cycle_id: int,
    department_id: Optional[int] = Query(None, description="按部门筛选"),
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr", "executive")),
):
    """导出考核周期汇总报表 Excel"""
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核周期不存在")

    query = db.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == cycle_id)
    if department_id is not None:
        query = query.filter(AssessmentRecord.department_id == department_id)
    records = query.all()

    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    from io import BytesIO
    from urllib.parse import quote

    wb = Workbook()
    ws = wb.active
    ws.title = "考核汇总"

    headers = ["工号", "姓名", "部门", "总分", "等级", "原始等级", "业绩分", "能力分", "态度分", "强制调整标记", "状态"]
    ws.append(headers)

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin")
    )

    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    for r in records:
        emp = db.query(Employee).filter(Employee.id == r.employee_id).first()
        dept = db.query(Department).filter(Department.id == r.department_id).first()
        ws.append([
            emp.employee_no if emp else "",
            emp.name if emp else "",
            dept.name if dept else "",
            str(r.total_score) if r.total_score else "",
            r.grade or "",
            r.original_grade or "",
            str(r.weighted_performance) if r.weighted_performance else "",
            str(r.weighted_ability) if r.weighted_ability else "",
            str(r.weighted_attitude) if r.weighted_attitude else "",
            "是" if r.is_distribution_override else "否",
            r.status or "",
        ])

    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=len(headers)):
        for cell in row:
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center", vertical="center")

    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except Exception:
                pass
        adjusted_width = min(max_length + 2, 30)
        ws.column_dimensions[column].width = adjusted_width

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"{cycle.name}_考核汇总.xlsx"
    filename_encoded = quote(filename)

    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename_encoded}"
        },
    )


@router.post("/{cycle_id}/publish")
def publish_cycle(
    cycle_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr")),
):
    """发布考核周期结果（pending_interview → published）"""
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核周期不存在")

    # 校验该周期下是否还有未到达 pending_interview 状态的记录
    unfinished = db.query(AssessmentRecord).filter(
        AssessmentRecord.cycle_id == cycle_id,
        AssessmentRecord.status.notin_(["pending_interview", "published", "archived"]),
    ).count()
    if unfinished > 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"该周期尚有 {unfinished} 条考核记录未完成审批，无法发布",
        )

    # 批量将 pending_interview 记录改为 published
    pending_count = db.query(AssessmentRecord).filter(
        AssessmentRecord.cycle_id == cycle_id,
        AssessmentRecord.status == "pending_interview",
    ).count()

    db.query(AssessmentRecord).filter(
        AssessmentRecord.cycle_id == cycle_id,
        AssessmentRecord.status == "pending_interview",
    ).update({"status": "published"})

    # 更新周期状态
    old_cycle_status = cycle.status
    cycle.status = "published"
    db.commit()

    log_operation(
        db=db,
        user_id=user.id,
        action="publish_cycle",
        target_type="assessment_cycle",
        target_id=cycle_id,
        old_value={"status": old_cycle_status},
        new_value={"status": "published", "updated_records": pending_count},
    )

    return {"message": "考核结果已发布", "cycle_id": cycle_id, "updated_records": pending_count}


@router.post("/{cycle_id}/advance-to-approval")
def advance_to_approval(
    cycle_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr")),
):
    """测试辅助：将周期下所有记录推进到 pending_approval 状态（用于 E2E 测试）"""
    records = db.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == cycle_id).all()
    for r in records:
        r.status = "pending_approval"
    db.commit()
    return {"updated": len(records)}


@router.post("/{cycle_id}/advance-to-interview")
def advance_to_interview(
    cycle_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr")),
):
    """测试辅助：将周期下所有记录推进到 pending_interview 状态（用于 E2E 测试）"""
    records = db.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == cycle_id).all()
    for r in records:
        r.status = "pending_interview"
    db.commit()
    return {"updated": len(records)}
