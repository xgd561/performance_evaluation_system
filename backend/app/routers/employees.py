from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
import io
import json

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import Employee, Department, Position, AssessmentRecord, User
from app.services.operation_logger import log_operation
from app.schemas import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeOut,
    EmployeeListResponse,
    StandardResponse,
)

from app.services.operation_logger import log_operation

from app.services.operation_logger import log_operation

from app.services.operation_logger import log_operation

router = APIRouter()


@router.get("/template")
def download_template(
    type: str = Query("empty", description="empty or sample"),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "hr", "executive")),
):
    if not OPENPYXL_AVAILABLE:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="openpyxl未安装")

    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "员工导入模板"
    headers = ["工号", "姓名", "部门", "岗位", "直属上级工号", "是否部门负责人", "入职日期", "状态"]
    ws.append(headers)

    if type == "sample":
        ws.append(["EMP001", "张三", "技术部", "Java工程师", "EMP002", "否", "2023-01-15", "在职"])
        ws.append(["EMP002", "李四", "技术部", "技术经理", "", "是", "2022-06-01", "在职"])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    from fastapi.responses import StreamingResponse
    filename = "employees_template_sample.xlsx" if type == "sample" else "employees_template.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/import")
def import_employees(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "hr")),
):
    if not OPENPYXL_AVAILABLE:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="openpyxl未安装")

    from openpyxl import load_workbook

    contents = file.file.read()
    try:
        wb = load_workbook(io.BytesIO(contents))
        ws = wb.active
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无法解析Excel文件")

    rows = list(ws.iter_rows(min_row=2, values_only=True))
    if not rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Excel文件为空")

    # Filter out completely empty rows (all cells None/empty)
    valid_rows = []
    for idx, row in enumerate(rows, start=2):
        if row and any(cell is not None and str(cell).strip() != "" for cell in row):
            valid_rows.append((idx, row))

    if not valid_rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Excel文件为空")

    # Check for duplicate employee_no within the file
    seen_employee_nos = set()
    for idx, row in valid_rows:
        employee_no_raw = str(row[0]).strip() if row[0] else ""
        if not employee_no_raw:
            continue
        if employee_no_raw in seen_employee_nos:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"文件内存在重复工号: {employee_no_raw}")
        seen_employee_nos.add(employee_no_raw)

    # Pre-validate all rows for missing required fields
    missing_field_errors = []
    for idx, row in valid_rows:
        employee_no = str(row[0]).strip() if row[0] else ""
        name = str(row[1]).strip() if row[1] else ""
        if not employee_no:
            missing_field_errors.append({"row": idx, "error": "工号为必填项"})
        if not name:
            missing_field_errors.append({"row": idx, "error": "姓名为必填项"})

    total_rows = len(valid_rows)
    if missing_field_errors:
        # If error rate > 10% or total rows <= 5, return 400
        error_rate = len(missing_field_errors) / total_rows
        if error_rate > 0.1 or total_rows <= 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"必填字段缺失: {missing_field_errors[0]['error']}",
            )

    success = 0
    failed = 0
    errors = []

    for idx, row in valid_rows:
        try:
            employee_no = str(row[0]).strip() if row[0] else None
            name = str(row[1]).strip() if row[1] else None
            dept_name = str(row[2]).strip() if row[2] else None
            pos_name = str(row[3]).strip() if row[3] else None

            if not employee_no:
                failed += 1
                errors.append({"row": idx, "error": "工号为必填项"})
                continue
            if not name:
                failed += 1
                errors.append({"row": idx, "error": "姓名为必填项"})
                continue

            # Find or create department
            dept = None
            if dept_name:
                dept = db.query(Department).filter(Department.name == dept_name).first()
                if not dept:
                    dept = Department(name=dept_name, code=dept_name)
                    db.add(dept)
                    db.flush()

            # Find or create position
            pos = None
            if pos_name and dept:
                pos = db.query(Position).filter(Position.name == pos_name, Position.department_id == dept.id).first()
                if not pos:
                    pos = Position(name=pos_name, department_id=dept.id)
                    db.add(pos)
                    db.flush()

            # Upsert: check if employee exists
            emp = db.query(Employee).filter(Employee.employee_no == employee_no).first()
            if emp:
                emp.name = name
                emp.department_id = dept.id if dept else emp.department_id
                emp.position_id = pos.id if pos else emp.position_id
                success += 1
            else:
                emp = Employee(
                    employee_no=employee_no,
                    name=name,
                    department_id=dept.id if dept else None,
                    position_id=pos.id if pos else None,
                )
                db.add(emp)
                success += 1
        except Exception as e:
            failed += 1
            errors.append({"row": idx, "error": str(e)})

    db.commit()
    return {"success": success, "failed": failed, "errors": errors}


@router.post("/import-preview")
def import_preview(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "hr", "executive")),
):
    if not OPENPYXL_AVAILABLE:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="openpyxl未安装")

    from openpyxl import load_workbook

    contents = file.file.read()
    try:
        wb = load_workbook(io.BytesIO(contents))
        ws = wb.active
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无法解析Excel文件")

    rows = list(ws.iter_rows(min_row=2, values_only=True))
    if not rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Excel文件为空")

    total = len([r for r in rows if r and r[0]])
    return {"total": total, "rows": [], "errors": []}


@router.get("/import/status")
def import_status(user: User = Depends(require_role("admin", "hr", "executive"))):
    return {"status": "ready", "progress": 100}


@router.get("")
def list_employees(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    department_id: Optional[int] = None,
    employee_no: Optional[str] = None,
    sort: Optional[str] = Query(None, description="排序字段: created_at, name"),
    order: Optional[str] = Query("asc", description="排序方向: asc, desc"),
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    query = db.query(Employee).filter(Employee.is_active == True)

    # 数据隔离：employee 只能查看自己
    if user.role == "employee":
        query = query.filter(Employee.id == user.employee_id)
    # 数据隔离：manager 只能查看本部门及子部门员工及下属
    elif user.role == "manager":
        current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
        if current_employee and current_employee.department_id:
            dept_ids = get_all_dept_ids(db, current_employee.department_id)
            query = query.filter(
                (Employee.department_id.in_(dept_ids)) |
                (Employee.manager_id == current_employee.id)
            )
        elif current_employee:
            query = query.filter(Employee.manager_id == current_employee.id)

    if employee_no:
        query = query.filter(Employee.employee_no == employee_no)
        return query.all()

    if keyword:
        query = query.filter(
            (Employee.name.contains(keyword)) |
            (Employee.employee_no.contains(keyword))
        )
    if department_id:
        query = query.filter(Employee.department_id == department_id)

    total = query.count()

    if sort == "created_at":
        query = query.order_by(Employee.created_at.asc() if order == "asc" else Employee.created_at.desc())
    elif sort == "name":
        query = query.order_by(Employee.name.asc() if order == "asc" else Employee.name.desc())
    else:
        query = query.order_by(Employee.created_at.desc())

    items = query.offset((page - 1) * size).limit(size).all()

    result = []
    for emp in items:
        dept_name = emp.department.name if emp.department else None
        pos_name = emp.position.name if emp.position else None
        mgr_name = emp.manager.name if emp.manager else None
        mgr_emp_no = emp.manager.employee_no if emp.manager else None
        result.append({
            "id": emp.id,
            "employee_no": emp.employee_no,
            "name": emp.name,
            "department_id": emp.department_id,
            "department_name": dept_name,
            "position_id": emp.position_id,
            "position_name": pos_name,
            "manager_id": emp.manager_id,
            "manager_name": mgr_name,
            "manager_employee_no": mgr_emp_no,
            "is_department_head": emp.is_department_head,
            "is_active": emp.is_active,
            "created_at": emp.created_at.isoformat() if emp.created_at else None,
        })

    return {
        "total": total,
        "page": page,
        "size": size,
        "items": result,
    }


@router.get("/{employee_id}")
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    emp = db.query(Employee).filter(Employee.id == employee_id, Employee.is_active == True).first()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工不存在")

    # P0-7: Data isolation
    if user.role == "peer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问")
    elif user.role == "employee":
        if user.employee_id != employee_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问")
    elif user.role == "manager":
        current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
        if not current_employee:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问")
        dept_ids = get_all_dept_ids(db, current_employee.department_id)
        allowed = (
            emp.department_id in dept_ids
            or emp.manager_id == current_employee.id
            or _is_in_subordinate_chain(db, current_employee.id, employee_id)
        )
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问")
    # admin, hr, executive: allow all

    return {
        "id": emp.id,
        "employee_no": emp.employee_no,
        "name": emp.name,
        "department_id": emp.department_id,
        "department_name": emp.department.name if emp.department else None,
        "position_id": emp.position_id,
        "position_name": emp.position.name if emp.position else None,
        "manager_id": emp.manager_id,
        "manager_name": emp.manager.name if emp.manager else None,
        "manager_employee_no": emp.manager.employee_no if emp.manager else None,
        "is_department_head": emp.is_department_head,
        "is_active": emp.is_active,
        "created_at": emp.created_at.isoformat() if emp.created_at else None,
    }


@router.get("/{employee_id}/subordinates")
def get_subordinates(
    employee_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "admin", "hr")),
):
    """获取某员工的直属下属列表"""
    emp = db.query(Employee).filter(Employee.id == employee_id, Employee.is_active == True).first()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工不存在")

    subordinates = db.query(Employee).filter(
        Employee.manager_id == employee_id,
        Employee.is_active == True
    ).all()

    result = []
    for sub in subordinates:
        result.append({
            "id": sub.id,
            "employee_no": sub.employee_no,
            "name": sub.name,
            "department_id": sub.department_id,
            "department_name": sub.department.name if sub.department else None,
            "position_id": sub.position_id,
            "position_name": sub.position.name if sub.position else None,
            "is_active": sub.is_active,
            "created_at": sub.created_at.isoformat() if sub.created_at else None,
        })

    return result


def get_all_dept_ids(db: Session, department_id: int, visited: set = None) -> set:
    """Recursively collect the given department and all its sub-department IDs."""
    if department_id is None:
        return set()
    if visited is None:
        visited = set()
    if department_id in visited:
        return set()
    visited.add(department_id)
    dept_ids = {department_id}
    children = db.query(Department.id).filter(Department.parent_id == department_id).all()
    for child_id in children:
        dept_ids.update(get_all_dept_ids(db, child_id[0], visited))
    return dept_ids


def _is_in_subordinate_chain(db: Session, manager_id: int, target_id: int) -> bool:
    """Check if target_id is a direct or indirect subordinate of manager_id."""
    if manager_id == target_id:
        return False
    current = target_id
    max_depth = 20
    for _ in range(max_depth):
        emp = db.query(Employee).filter(Employee.id == current).first()
        if not emp or emp.manager_id is None:
            return False
        if emp.manager_id == manager_id:
            return True
        current = emp.manager_id
    return False


def _resolve_manager_id(db: Session, manager_employee_no: Optional[str], fallback_manager_id: Optional[int] = None) -> Optional[int]:
    """Look up manager_id by employee_no. If manager_employee_no is provided and not empty, return the resolved id. Otherwise return the fallback."""
    if manager_employee_no is not None:
        manager_employee_no = manager_employee_no.strip()
    if manager_employee_no:
        mgr = db.query(Employee).filter(Employee.employee_no == manager_employee_no).first()
        if mgr:
            return mgr.id
    return fallback_manager_id


@router.post("", status_code=status.HTTP_201_CREATED)
def create_employee(
    req: EmployeeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "hr")),
):
    # Check duplicate employee_no
    existing = db.query(Employee).filter(Employee.employee_no == req.employee_no).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="工号已存在",
        )
    # Check foreign keys
    if req.department_id:
        dept = db.query(Department).filter(Department.id == req.department_id).first()
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="部门不存在",
            )
    if req.position_id:
        pos = db.query(Position).filter(Position.id == req.position_id).first()
        if not pos:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="岗位不存在",
            )

    # Resolve manager_id: if manager_employee_no provided, use it; otherwise use manager_id from request
    if req.manager_employee_no is not None and req.manager_employee_no.strip():
        manager_id = _resolve_manager_id(db, req.manager_employee_no)
    else:
        manager_id = req.manager_id

    emp = Employee(
        employee_no=req.employee_no,
        name=req.name,
        department_id=req.department_id,
        position_id=req.position_id,
        manager_id=manager_id,
        is_department_head=req.is_department_head,
        is_active=req.is_active,
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)

    log_operation(
        db=db,
        user_id=user.id,
        action="create_employee",
        target_type="employee",
        target_id=emp.id,
        new_value={"employee_no": emp.employee_no, "name": emp.name},
    )

    return {
        "id": emp.id,
        "employee_no": emp.employee_no,
        "name": emp.name,
        "department_id": emp.department_id,
        "department_name": emp.department.name if emp.department else None,
        "position_id": emp.position_id,
        "position_name": emp.position.name if emp.position else None,
        "manager_id": emp.manager_id,
        "manager_name": emp.manager.name if emp.manager else None,
        "manager_employee_no": emp.manager.employee_no if emp.manager else None,
        "is_department_head": emp.is_department_head,
        "is_active": emp.is_active,
        "created_at": emp.created_at.isoformat() if emp.created_at else None,
    }


@router.put("/{employee_id}")
def update_employee(
    employee_id: int,
    req: EmployeeUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "hr")),
):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工不存在")

    # Check duplicate employee_no
    if req.employee_no:
        existing = db.query(Employee).filter(
            Employee.employee_no == req.employee_no,
            Employee.id != employee_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="工号已存在",
            )

    # Check foreign keys
    if req.department_id:
        dept = db.query(Department).filter(Department.id == req.department_id).first()
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="部门不存在",
            )

    # Resolve manager_id: if manager_employee_no provided, use it; otherwise use manager_id from request
    if req.manager_employee_no is not None and req.manager_employee_no.strip():
        manager_id = _resolve_manager_id(db, req.manager_employee_no)
    elif req.manager_id is not None:
        manager_id = req.manager_id
    else:
        manager_id = None

    if manager_id is not None:
        emp.manager_id = manager_id

    for field, value in req.model_dump(exclude_unset=True).items():
        if field == "manager_employee_no":
            continue  # Already handled above
        if field == "manager_id":
            continue  # Already handled above
        setattr(emp, field, value)
    db.commit()
    db.refresh(emp)

    log_operation(
        db=db,
        user_id=user.id,
        action="update_employee",
        target_type="employee",
        target_id=employee_id,
        new_value={"employee_no": emp.employee_no, "name": emp.name},
    )

    return {
        "id": emp.id,
        "employee_no": emp.employee_no,
        "name": emp.name,
        "department_id": emp.department_id,
        "department_name": emp.department.name if emp.department else None,
        "position_id": emp.position_id,
        "position_name": emp.position.name if emp.position else None,
        "manager_id": emp.manager_id,
        "manager_name": emp.manager.name if emp.manager else None,
        "manager_employee_no": emp.manager.employee_no if emp.manager else None,
        "is_department_head": emp.is_department_head,
        "is_active": emp.is_active,
        "created_at": emp.created_at.isoformat() if emp.created_at else None,
    }


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "hr")),
):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工不存在")

    # Check if employee has assessment records
    records = db.query(AssessmentRecord).filter(AssessmentRecord.employee_id == employee_id).first()
    if records:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该员工已有考核历史数据，不可删除",
        )

    db.delete(emp)
    db.commit()

    log_operation(
        db=db,
        user_id=user.id,
        action="delete_employee",
        target_type="employee",
        target_id=employee_id,
        old_value={"employee_no": emp.employee_no, "name": emp.name},
    )

    return
