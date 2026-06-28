from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
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
from app.schemas import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeOut,
    EmployeeListResponse,
    StandardResponse,
)

router = APIRouter()


@router.get("/template")
def download_template(
    type: str = Query("empty", description="empty or sample"),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "hr")),
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

    total = len([r for r in rows if r and r[0]])
    return {"total": total, "rows": [], "errors": []}


@router.get("/import/status")
def import_status(user: User = Depends(require_role("admin", "hr"))):
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
    user: User = Depends(get_current_user),
):
    query = db.query(Employee).filter(Employee.is_active == True)

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

    return {
        "total": total,
        "page": page,
        "size": size,
        "items": items,
    }


@router.get("/{employee_id}/subordinates")
def get_subordinates(
    employee_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    subordinates = db.query(Employee).filter(Employee.manager_id == employee_id, Employee.is_active == True).all()
    return subordinates


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    emp = db.query(Employee).filter(Employee.id == employee_id, Employee.is_active == True).first()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工不存在")
    return emp


@router.post("", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
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

    emp = Employee(**req.model_dump())
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


@router.put("/{employee_id}", response_model=EmployeeOut)
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

    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(emp, field, value)
    db.commit()
    db.refresh(emp)
    return emp


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
    return
