from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import json

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import (
    PeerReviewer, PeerReviewTask, AssessmentRecord, AssessmentCycle, Employee, Department, Position, User
)

from app.utils.json_columns import load_json

router = APIRouter()


@router.get("/my-reviews")
def get_my_peer_reviews(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("peer")),
):
    """获取当前协作人的待评分列表"""
    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        return {"items": [], "total": 0}

    # 查询当前员工作为协作评分人的关系（返回所有状态：待办 + 已完成）
    peer_relations = db.query(PeerReviewer).filter(
        PeerReviewer.reviewer_id == current_employee.id,
    ).all()

    result = []
    for rel in peer_relations:
        record = db.query(AssessmentRecord).filter(
            AssessmentRecord.cycle_id == rel.cycle_id,
            AssessmentRecord.employee_id == rel.employee_id
        ).first()

        if not record:
            continue

        # 只返回处于协作评分阶段的记录
        if record.status not in ["pending_peer", "pending_manager", "pending_self"]:
            continue

        emp = db.query(Employee).filter(Employee.id == rel.employee_id).first()
        dept = db.query(Department).filter(Department.id == emp.department_id).first() if emp else None
        pos = db.query(Position).filter(Position.id == emp.position_id).first() if emp else None
        cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == rel.cycle_id).first()

        self_scores = load_json(record.self_scores, {})
        manager_scores = load_json(record.manager_scores, {})
        peer_scores = load_json(record.peer_scores, {})

        result.append({
            "id": rel.id,
            "record_id": record.id,
            "cycle_id": rel.cycle_id,
            "cycle_name": cycle.name if cycle else None,
            "employee_id": rel.employee_id,
            "employee_name": emp.name if emp else None,
            "employee_no": emp.employee_no if emp else None,
            "department_name": dept.name if dept else None,
            "position_name": pos.name if pos else None,
            "status": record.status,
            "peer_relation_status": rel.status,
            "self_scores": self_scores,
            "manager_scores": manager_scores,
            "peer_scores": peer_scores,
            "peer_due_date": str(cycle.peer_due_date) if cycle and cycle.peer_due_date else None,
        })

    result.sort(key=lambda x: (0 if x["peer_relation_status"] != "completed" else 1, x["peer_due_date"] or ""))

    return {"items": result, "total": len(result)}


from pydantic import BaseModel


class PeerReviewerCreate(BaseModel):
    cycle_id: int
    employee_id: int
    peer_id: int


@router.post("")
def assign_peer_reviewer(
    body: PeerReviewerCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "hr")),
):
    """分配协作评分人"""
    # 校验周期和员工是否存在
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == body.cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核周期不存在")

    employee = db.query(Employee).filter(Employee.id == body.employee_id).first()
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="被考核员工不存在")

    peer = db.query(Employee).filter(Employee.id == body.peer_id).first()
    if not peer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="协作评分人不存在")

    # 不能自己评自己
    if body.employee_id == body.peer_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="不能为自己分配协作评分")

    # 检查是否已存在
    existing = db.query(PeerReviewer).filter(
        PeerReviewer.cycle_id == body.cycle_id,
        PeerReviewer.employee_id == body.employee_id,
        PeerReviewer.reviewer_id == body.peer_id,
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该协作评分关系已存在")

    relation = PeerReviewer(
        cycle_id=body.cycle_id,
        employee_id=body.employee_id,
        reviewer_id=body.peer_id,
        reviewer_department_id=peer.department_id,
        status="pending",
    )
    db.add(relation)
    db.commit()
    db.refresh(relation)

    # 同时创建 PeerReviewTask，供 P4-13 / P4-14 使用
    record = db.query(AssessmentRecord).filter(
        AssessmentRecord.cycle_id == body.cycle_id,
        AssessmentRecord.employee_id == body.employee_id
    ).first()
    if record:
        existing_task = db.query(PeerReviewTask).filter(
            PeerReviewTask.record_id == record.id,
            PeerReviewTask.reviewer_id == body.peer_id,
        ).first()
        if not existing_task:
            task = PeerReviewTask(
                record_id=record.id,
                reviewer_id=body.peer_id,
                status="pending",
            )
            db.add(task)
            db.commit()

    return {
        "id": relation.id,
        "cycle_id": relation.cycle_id,
        "employee_id": relation.employee_id,
        "peer_id": relation.reviewer_id,
        "status": relation.status,
    }


@router.delete("/{relation_id}")
def remove_peer_reviewer(
    relation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "hr")),
):
    """移除协作评分人"""
    relation = db.query(PeerReviewer).filter(PeerReviewer.id == relation_id).first()
    if not relation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="协作评分关系不存在")

    db.delete(relation)
    db.commit()
    return {"deleted": True}


@router.get("/cycle/{cycle_id}")
def list_peer_reviewers(
    cycle_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "hr", "executive")),
):
    """获取某周期的协作评分关系列表"""
    relations = db.query(PeerReviewer).filter(PeerReviewer.cycle_id == cycle_id).all()
    result = []
    for rel in relations:
        emp = db.query(Employee).filter(Employee.id == rel.employee_id).first()
        peer = db.query(Employee).filter(Employee.id == rel.reviewer_id).first()
        result.append({
            "id": rel.id,
            "cycle_id": rel.cycle_id,
            "employee_id": rel.employee_id,
            "employee_name": emp.name if emp else None,
            "peer_id": rel.reviewer_id,
            "peer_name": peer.name if peer else None,
            "status": rel.status,
        })
    return result
