from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, text

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
    tree: bool = False,
    db: Session = Depends(get_db),
    user: Employee = Depends(get_current_user),
):
    if tree:
        # 使用递归 CTE 查询所有部门及其层级
        stmt = text("""
            WITH RECURSIVE dept_tree AS (
                SELECT id, name, code, parent_id, head_id, created_at, 0 AS level
                FROM departments
                WHERE parent_id IS NULL
                UNION ALL
                SELECT d.id, d.name, d.code, d.parent_id, d.head_id, d.created_at, dt.level + 1
                FROM departments d
                INNER JOIN dept_tree dt ON d.parent_id = dt.id
            )
            SELECT * FROM dept_tree ORDER BY level, id
        """)
        rows = db.execute(stmt).mappings().all()
        nodes = {}
        roots = []
        for row in rows:
            node = {
                "id": row["id"],
                "name": row["name"],
                "code": row["code"],
                "parent_id": row["parent_id"],
                "head_id": row["head_id"],
                "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else row["created_at"],
                "level": row["level"],
                "children": []
            }
            nodes[row["id"]] = node
        for row in rows:
            node = nodes[row["id"]]
            if row["parent_id"] is None:
                roots.append(node)
            else:
                parent = nodes.get(row["parent_id"])
                if parent:
                    parent["children"].append(node)
        return roots

    depts = db.query(Department).all()
    # Build a map for parent lookup
    dept_map = {d.id: d for d in depts}
    result = []
    for d in depts:
        position_count = db.query(Position).filter(Position.department_id == d.id).count()
        employee_count = db.query(Employee).filter(Employee.department_id == d.id, Employee.is_active == True).count()
        parent_name = dept_map.get(d.parent_id).name if d.parent_id and d.parent_id in dept_map else None
        result.append({
            "id": d.id,
            "name": d.name,
            "code": d.code,
            "parent_id": d.parent_id,
            "parent_name": parent_name,
            "head_id": d.head_id,
            "position_count": position_count,
            "employee_count": employee_count,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        })
    return result


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
    # Check if department has children departments
    children = db.query(Department).filter(Department.parent_id == dept_id).first()
    if children:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="部门下存在子部门，不可删除")
    # Check if department has employees
    employees = db.query(Employee).filter(Employee.department_id == dept_id).first()
    if employees:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="部门下存在员工，不可删除")
    # Check if department has positions
    positions = db.query(Position).filter(Position.department_id == dept_id).first()
    if positions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="部门下存在岗位，不可删除")
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
