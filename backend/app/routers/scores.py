from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import json

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import (
    AssessmentRecord, AssessmentCycle, Employee, Department, Position, ScoreDetail, User, PeerReviewer
)

router = APIRouter()

@router.get("/summary/{cycle_id}")
def get_score_summary(
    cycle_id: int,
    department_id: int = None,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr", "manager")),
):
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核周期不存在")

    query = db.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == cycle_id)
    if department_id:
        query = query.filter(AssessmentRecord.department_id == department_id)
    records = query.all()

    result = []
    for r in records:
        emp = db.query(Employee).filter(Employee.id == r.employee_id).first()
        dept = db.query(Department).filter(Department.id == r.department_id).first()
        pos = db.query(Position).filter(Position.id == r.position_id).first()

        self_scores = json.loads(r.self_scores) if r.self_scores else {}
        manager_scores = json.loads(r.manager_scores) if r.manager_scores else {}
        peer_scores = json.loads(r.peer_scores) if r.peer_scores else {}

        result.append({
            "record_id": r.id,
            "employee_id": r.employee_id,
            "employee_name": emp.name if emp else None,
            "employee_no": emp.employee_no if emp else None,
            "department_id": r.department_id,
            "department_name": dept.name if dept else None,
            "position_id": r.position_id,
            "position_name": pos.name if pos else None,
            "self_scores": self_scores,
            "manager_scores": manager_scores,
            "peer_scores": peer_scores,
            "weighted_performance": str(r.weighted_performance) if r.weighted_performance else None,
            "weighted_ability": str(r.weighted_ability) if r.weighted_ability else None,
            "weighted_attitude": str(r.weighted_attitude) if r.weighted_attitude else None,
            "total_score": str(r.total_score) if r.total_score else None,
            "grade": r.grade,
            "original_grade": r.original_grade,
            "is_distribution_override": r.is_distribution_override,
            "status": r.status,
            "manager_comment": r.manager_comment,
        })
    return result

@router.post("/calculate/{cycle_id}")
def calculate_scores(
    cycle_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr")),
):
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核周期不存在")

    dim_weights = json.loads(cycle.dimension_weights)
    reviewer_weights = json.loads(cycle.reviewer_weights)
    grade_rules = json.loads(cycle.grade_rules)

    records = db.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == cycle_id).all()

    def _map_grade(total):
        for grade, rule in grade_rules.items():
            if isinstance(rule, dict):
                mn = rule.get("min", 0)
                mx = rule.get("max", 100)
                if mn <= total <= mx:
                    return grade
        return "D"

    for r in records:
        self_scores = json.loads(r.self_scores) if r.self_scores else {}
        manager_scores = json.loads(r.manager_scores) if r.manager_scores else {}
        peer_scores = json.loads(r.peer_scores) if r.peer_scores else {}

        weighted_dims = {}
        for dim, dim_weight in dim_weights.items():
            scores = {
                "self": self_scores.get(dim),
                "manager": manager_scores.get(dim),
                "peer": peer_scores.get(dim),
            }
            rw = reviewer_weights.get(dim, {})
            total_w = 0
            weighted_sum = 0
            for reviewer, score in scores.items():
                if score is not None and reviewer in rw:
                    weighted_sum += score * rw[reviewer]
                    total_w += rw[reviewer]
            if total_w > 0 and total_w < 1.0:
                weighted_sum = weighted_sum / total_w
            weighted_dims[dim] = round(weighted_sum, 1)

        total = sum(weighted_dims.get(d, 0) * dim_weights.get(d, 0) for d in dim_weights)
        total = round(total, 1)

        r.weighted_performance = weighted_dims.get("performance", 0)
        r.weighted_ability = weighted_dims.get("ability", 0)
        r.weighted_attitude = weighted_dims.get("attitude", 0)
        r.total_score = total
        r.grade = _map_grade(total)
        r.original_grade = r.grade
        r.status = "pending_summary"

    db.commit()

    return {"calculated": len(records), "status": "pending_summary"}


from pydantic import BaseModel
from typing import Optional, List, Any

class ManagerScoreSubmit(BaseModel):
    performance: float
    ability: float
    attitude: float
    kpi_scores: Optional[List[Any]] = None
    comment: Optional[str] = None


@router.get("/to-review")
def get_to_review_list(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "admin", "hr")),
):
    """获取当前用户的待评列表（上级评）"""
    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工信息不存在")

    # 查询当前用户是直属上级的员工
    subordinate_ids = db.query(Employee.id).filter(Employee.manager_id == current_employee.id).all()
    subordinate_ids = [sid[0] for sid in subordinate_ids]

    if not subordinate_ids:
        return []

    # 查询待上级评分的记录：状态为 pending_manager
    records = db.query(AssessmentRecord).filter(
        AssessmentRecord.employee_id.in_(subordinate_ids),
        AssessmentRecord.status == "pending_manager"
    ).all()

    result = []
    for r in records:
        emp = db.query(Employee).filter(Employee.id == r.employee_id).first()
        dept = db.query(Department).filter(Department.id == r.department_id).first()
        pos = db.query(Position).filter(Position.id == r.position_id).first()
        cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == r.cycle_id).first()

        self_scores = json.loads(r.self_scores) if r.self_scores else {}
        kpi_snapshot = json.loads(r.kpi_snapshot) if r.kpi_snapshot else {}

        result.append({
            "record_id": r.id,
            "cycle_id": r.cycle_id,
            "cycle_name": cycle.name if cycle else None,
            "employee_id": r.employee_id,
            "employee_name": emp.name if emp else None,
            "employee_no": emp.employee_no if emp else None,
            "department_name": dept.name if dept else None,
            "position_name": pos.name if pos else None,
            "status": r.status,
            "self_scores": self_scores,
            "kpi_snapshot": kpi_snapshot,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return result


@router.post("/manager/{record_id}")
def submit_manager_score(
    record_id: int,
    body: ManagerScoreSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "admin", "hr")),
):
    """提交上级评分"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工信息不存在")

    # 权限校验：只能给下属评分
    if record.employee_id not in [e.id for e in current_employee.subordinates]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权为此员工评分")

    # 状态校验
    if record.status not in ["pending_manager", "pending_self"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="当前状态不允许提交上级评分")

    # 分数校验
    for dim, score in [("performance", body.performance), ("ability", body.ability), ("attitude", body.attitude)]:
        if score < 0 or score > 100:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{dim}分数需在0-100之间")

    # 评语校验：不少于20字
    if not body.comment or len(body.comment.strip()) < 20:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="综合评语不少于20字")

    manager_scores = {
        "performance": body.performance,
        "ability": body.ability,
        "attitude": body.attitude,
    }

    # 校验与自评分差异超过20分的维度
    self_scores = json.loads(record.self_scores) if record.self_scores else {}
    alerts = []
    for dim in ["performance", "ability", "attitude"]:
        m_score = manager_scores.get(dim)
        s_score = self_scores.get(dim)
        if s_score is not None and m_score is not None and abs(float(m_score) - float(s_score)) > 20:
            alerts.append(f"维度[{dim}]上级评分与自评分差异过大: {m_score} vs {s_score}")

    record.manager_scores = json.dumps(manager_scores)
    record.manager_comment = body.comment
    record.status = "pending_peer"

    db.commit()
    db.refresh(record)

    return {
        "record_id": record_id,
        "manager_scores": manager_scores,
        "comment": body.comment,
        "alerts": alerts,
        "status": record.status,
    }


class PeerScoreSubmit(BaseModel):
    ability: float


@router.post("/peer/{record_id}")
def submit_peer_score(
    record_id: int,
    body: PeerScoreSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("peer")),
):
    """提交协作评分"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工信息不存在")

    # 权限校验：必须是该员工的分配协作人
    peer_relation = db.query(PeerReviewer).filter(
        PeerReviewer.cycle_id == record.cycle_id,
        PeerReviewer.employee_id == record.employee_id,
        PeerReviewer.reviewer_id == current_employee.id,
    ).first()
    if not peer_relation:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您未被分配为当前员工的协作评分人")

    # 分数校验
    if body.ability < 0 or body.ability > 100:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="能力分数需在0-100之间")

    # 协作人只评"工作能力"维度
    peer_scores = json.loads(record.peer_scores) if record.peer_scores else {}
    peer_scores["ability"] = body.ability

    record.peer_scores = json.dumps(peer_scores)
    peer_relation.status = "completed"

    db.commit()
    db.refresh(record)

    return {
        "record_id": record_id,
        "peer_scores": peer_scores,
        "status": record.status,
    }


class SelfScoreSubmit(BaseModel):
    performance: float
    ability: float
    attitude: float


@router.get("/my-assessment")
def get_my_assessment(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("employee")),
):
    """获取当前员工的考核记录列表"""
    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        return {"items": [], "total": 0}

    records = db.query(AssessmentRecord).filter(
        AssessmentRecord.employee_id == current_employee.id
    ).order_by(AssessmentRecord.created_at.desc()).all()

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
            "cycle_status": cycle.status if cycle else None,
            "self_due_date": str(cycle.self_due_date) if cycle and cycle.self_due_date else None,
            "manager_due_date": str(cycle.manager_due_date) if cycle and cycle.manager_due_date else None,
            "peer_due_date": str(cycle.peer_due_date) if cycle and cycle.peer_due_date else None,
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


@router.post("/self/{record_id}")
def submit_self_score(
    record_id: int,
    body: SelfScoreSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("employee")),
):
    """提交自评"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    # 权限校验：只能评自己的
    if record.employee_id != user.employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作此考核记录")

    # 状态校验：只能待自评时提交
    if record.status not in ["pending_self", "not_started"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="当前状态不允许提交自评")

    # 分数校验
    for dim, score in [("performance", body.performance), ("ability", body.ability), ("attitude", body.attitude)]:
        if score < 0 or score > 100:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{dim}分数需在0-100之间")

    self_scores = {
        "performance": body.performance,
        "ability": body.ability,
        "attitude": body.attitude,
    }

    record.self_scores = json.dumps(self_scores)
    record.status = "pending_manager"

    db.commit()
    db.refresh(record)

    return {
        "record_id": record_id,
        "self_scores": self_scores,
        "status": record.status,
    }
