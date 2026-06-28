from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import Department, Position, Employee
from app.schemas import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentOut,
    PositionCreate,
    PositionUpdate,
    PositionOut,
)

router = APIRouter()


@router.get("")
def list_departments(
    db: Session = Depends(get_db),
    user: Employee = Depends(get_current_user),
):
    depts = db.query(Department).all()
    return depts


@router.post("", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
def create_department(
    req: DepartmentCreate,
    db: Session = Depends(get_db),
    user: Employee = Depends(require_role("admin", "hr")),
):
    if req.code:
        existing = db.query(Department).filter(Department.code == req.code).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="部门编码已存在")
    if req.name:
        existing = db.query(Department).filter(Department.name == req.name).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="部门名称已存在")
    dept = Department(**req.model_dump())
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@router.put("/{dept_id}", response_model=DepartmentOut)
def update_department(
    dept_id: int,
    req: DepartmentUpdate,
    db: Session = Depends(get_db),
    user: Employee = Depends(require_role("admin", "hr")),
):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="部门不存在")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(dept, field, value)
    db.commit()
    db.refresh(dept)
    return dept


@router.delete("/{dept_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(
    dept_id: int,
    db: Session = Depends(get_db),
    user: Employee = Depends(require_role("admin", "hr")),
):
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="部门不存在")
    # Check if department has employees
    employees = db.query(Employee).filter(Employee.department_id == dept_id).first()
    if employees:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="部门下存在员工，不可删除")
    # Check if department has positions
    positions = db.query(Position).filter(Position.department_id == dept_id).first()
    if positions:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="部门下存在岗位，不可删除")
    db.delete(dept)
    db.commit()
    return


router_positions = APIRouter()


@router_positions.get("")
def list_positions(
    department_id: int = None,
    db: Session = Depends(get_db),
    user: Employee = Depends(get_current_user),
):
    query = db.query(Position)
    if department_id:
        query = query.filter(Position.department_id == department_id)
    return {"items": query.all()}


@router_positions.post("", response_model=PositionOut, status_code=status.HTTP_201_CREATED)
def create_position(
    req: PositionCreate,
    db: Session = Depends(get_db),
    user: Employee = Depends(require_role("admin", "hr")),
):
    pos = Position(**req.model_dump())
    db.add(pos)
    db.commit()
    db.refresh(pos)
    return pos


@router_positions.put("/{pos_id}", response_model=PositionOut)
def update_position(
    pos_id: int,
    req: PositionUpdate,
    db: Session = Depends(get_db),
    user: Employee = Depends(require_role("admin", "hr")),
):
    pos = db.query(Position).filter(Position.id == pos_id).first()
    if not pos:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="岗位不存在")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(pos, field, value)
    db.commit()
    db.refresh(pos)
    return pos


@router_positions.delete("/{pos_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_position(
    pos_id: int,
    db: Session = Depends(get_db),
    user: Employee = Depends(require_role("admin", "hr")),
):
    pos = db.query(Position).filter(Position.id == pos_id).first()
    if not pos:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="岗位不存在")
    # Check if position has employees
    employees = db.query(Employee).filter(Employee.position_id == pos_id).first()
    if employees:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="岗位下存在员工，不可删除")
    db.delete(pos)
    db.commit()
    return
