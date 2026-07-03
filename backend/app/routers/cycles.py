from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import json

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import (
    AssessmentCycle, Employee, AssessmentRecord, CycleEmployee, KpiTemplate, Position,
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

from app.services.operation_logger import log_operation

router = APIRouter()


@router.get("")
def list_cycles(
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    cycles = db.query(AssessmentCycle).order_by(AssessmentCycle.created_at.desc()).all()
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
            "weights": json.loads(c.dimension_weights) if c.dimension_weights else {},
            "grade_rules": json.loads(c.grade_rules) if c.grade_rules else {},
            "is_distribution_enabled": c.is_distribution_enabled,
            "small_dept_exemption": c.small_dept_exemption,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })
    return result


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
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已发起的考核周期不可修改")

    for field, value in req.model_dump(exclude_unset=True).items():
        if field == "weights":
            setattr(cycle, "reviewer_weights", json.dumps(value))
        elif field == "grade_rules":
            setattr(cycle, "grade_rules", json.dumps(value))
        elif field == "small_dept_exemption":
            setattr(cycle, "small_dept_exemption", value)
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
        "weights": json.loads(cycle.dimension_weights) if cycle.dimension_weights else {},
        "grade_rules": json.loads(cycle.grade_rules) if cycle.grade_rules else {},
        "is_distribution_enabled": cycle.is_distribution_enabled,
        "small_dept_exemption": cycle.small_dept_exemption,
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

    records = db.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == cycle_id).first()
    if records:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
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

    return {
        "cycle_id": cycle_id,
        "status": cycle.status,
        "stages": [
            {"name": "自评", "status": "completed" if cycle.status != "not_started" else "pending"},
            {"name": "上级评", "status": "completed" if cycle.status in ["pending_peer", "pending_summary", "pending_approval", "published", "archived"] else "pending"},
            {"name": "协作评", "status": "completed" if cycle.status in ["pending_summary", "pending_approval", "published", "archived"] else "pending"},
            {"name": "汇总", "status": "completed" if cycle.status in ["pending_approval", "published", "archived"] else "pending"},
            {"name": "审批", "status": "completed" if cycle.status in ["published", "archived"] else "pending"},
        ],
        "overall_progress": progress,
        "total_employees": total,
        "completed": completed,
        "last_updated": cycle.updated_at.isoformat() if cycle.updated_at else cycle.created_at.isoformat() if cycle.created_at else None,
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
    db.commit()

    log_operation(
        db=db,
        user_id=user.id,
        action="archive_cycle",
        target_type="assessment_cycle",
        target_id=cycle_id,
        new_value={"status": "archived", "is_locked": True},
    )

    return {"message": "考核周期已归档", "cycle_id": cycle_id}


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
