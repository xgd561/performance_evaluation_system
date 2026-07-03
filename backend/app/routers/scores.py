from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
import json

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import (
    AssessmentRecord, AssessmentCycle, Employee, Department, Position, ScoreDetail, User, PeerReviewer, AppealRecord, InterviewRecord
)

from app.services.operation_logger import log_operation
from app.services.distribution_enforcer import enforce_distribution
from app.routers.employees import _is_in_subordinate_chain, get_all_dept_ids

router = APIRouter()


def _ensure_score_details(db, record):
    """根据 kpi_snapshot 确保 score_details 记录存在，返回 detail 列表"""
    details = db.query(ScoreDetail).filter(ScoreDetail.record_id == record.id).order_by(ScoreDetail.id).all()
    if details:
        return details
    snapshot = json.loads(record.kpi_snapshot) if record.kpi_snapshot else []
    if isinstance(snapshot, dict):
        items = snapshot.get("items", [])
    elif isinstance(snapshot, list):
        items = snapshot
    else:
        items = []
    for item in items:
        sd = ScoreDetail(
            record_id=record.id,
            kpi_name=item.get("name") or item.get("kpi_name"),
            weight=float(item.get("weight", 0) or 0),
            target_value=item.get("target_value") or item.get("target"),
        )
        db.add(sd)
    db.flush()
    return db.query(ScoreDetail).filter(ScoreDetail.record_id == record.id).order_by(ScoreDetail.id).all()


def _update_kpi_scores(db, record_id, kpi_scores, score_type):
    """更新 score_details 的 KPI 评分
    score_type: 'self' 或 'manager'
    """
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        return
    details = _ensure_score_details(db, record)
    if not details or not kpi_scores:
        return
    for i, score in enumerate(kpi_scores):
        if i >= len(details):
            break
        if score is not None:
            if score_type == "self":
                details[i].self_score = score
            elif score_type == "manager":
                details[i].manager_score = score


def _get_kpi_weighted_performance(db, record_id, score_type):
    """根据 KPI 评分计算加权 performance 得分
    score_type: 'self' 或 'manager'
    """
    details = db.query(ScoreDetail).filter(ScoreDetail.record_id == record_id).all()
    if not details:
        return None
    total_weight = 0
    weighted_sum = 0
    has_score = False
    for d in details:
        score = d.self_score if score_type == "self" else d.manager_score if score_type == "manager" else None
        if score is not None:
            weight = float(d.weight or 0)
            weighted_sum += float(score) * weight
            total_weight += weight
            has_score = True
    if not has_score or total_weight == 0:
        return None
    return round(weighted_sum / total_weight, 1)


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

    # 数据隔离：manager 可查看自己下属及本部门及子部门的记录
    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if user.role == "manager" and current_employee:
        subordinate_ids = db.query(Employee.id).filter(
            Employee.manager_id == current_employee.id
        ).all()
        subordinate_ids = [sid[0] for sid in subordinate_ids]
        dept_ids = get_all_dept_ids(db, current_employee.department_id)
        filters = []
        if subordinate_ids:
            filters.append(AssessmentRecord.employee_id.in_(subordinate_ids))
        if dept_ids:
            filters.append(AssessmentRecord.department_id.in_(dept_ids))
        if filters:
            query = query.filter(or_(*filters))
        else:
            return []

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

        # 如有 KPI 评分，按权重加权计算 performance 维度
        self_kpi_perf = _get_kpi_weighted_performance(db, r.id, "self")
        manager_kpi_perf = _get_kpi_weighted_performance(db, r.id, "manager")
        if self_kpi_perf is not None:
            self_scores["performance"] = self_kpi_perf
        if manager_kpi_perf is not None:
            manager_scores["performance"] = manager_kpi_perf

        weighted_dims = {}
        for dim, dim_weight in dim_weights.items():
            scores = {
                "self": self_scores.get(dim),
                "manager": manager_scores.get(dim),
                "peer": peer_scores.get(dim),
            }
            rw = reviewer_weights.get(dim, reviewer_weights)
            if not rw and any(r in reviewer_weights for r in ["self", "manager", "peer"]):
                rw = reviewer_weights
            total_w = 0
            weighted_sum = 0
            for reviewer, score in scores.items():
                if score is not None and reviewer in rw:
                    weighted_sum += score * rw[reviewer]
                    total_w += rw[reviewer]
            if total_w > 0:
                weighted_sum = weighted_sum / total_w
            weighted_dims[dim] = round(weighted_sum, 1)

        dim_weight_factor = 100.0 if sum(dim_weights.values()) > 1 else 1.0
        total = sum(weighted_dims.get(d, 0) * (dim_weights.get(d, 0) / dim_weight_factor) for d in dim_weights)
        total = round(total, 1)

        r.weighted_performance = weighted_dims.get("performance", 0)
        r.weighted_ability = weighted_dims.get("ability", 0)
        r.weighted_attitude = weighted_dims.get("attitude", 0)
        r.total_score = total
        r.grade = _map_grade(total)
        r.original_grade = r.grade
        r.status = "pending_summary"

    # 强制分布：按部门独立核算
    from collections import defaultdict
    dept_records = defaultdict(list)
    for r in records:
        dept_id = r.department_id or 0
        dept_records[dept_id].append(r)

    all_adjustment_logs = []
    all_override_candidates = []

    for dept_id, dept_recs in dept_records.items():
        result = enforce_distribution(
            dept_recs,
            grade_rules,
            len(dept_recs),
            small_dept_exemption=cycle.small_dept_exemption,
        )
        all_adjustment_logs.extend(result["adjustment_log"])
        all_override_candidates.extend(result["override_candidates"])

    db.commit()

    return {
        "calculated": len(records),
        "status": "pending_summary",
        "adjustment_count": len(all_adjustment_logs),
        "override_candidates": len(all_override_candidates),
    }


from pydantic import BaseModel
from typing import Optional, List, Any

from app.services.operation_logger import log_operation


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
            "manager_due_date": str(cycle.manager_due_date) if cycle and cycle.manager_due_date else None,
            "test_reload": "yes",
            "test_field": "hello",
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

    # 保存 KPI 评分
    if body.kpi_scores:
        _update_kpi_scores(db, record_id, body.kpi_scores, "manager")

    # 校验与自评分差异超过20分的维度
    self_scores = json.loads(record.self_scores) if record.self_scores else {}
    alerts = []
    for dim in ["performance", "ability", "attitude"]:
        m_score = manager_scores.get(dim)
        s_score = self_scores.get(dim)
        if s_score is not None and m_score is not None and abs(float(m_score) - float(s_score)) > 20:
            alerts.append(f"维度[{dim}]上级评分与自评分差异过大: {m_score} vs {s_score}")

    old_status = record.status
    record.manager_scores = json.dumps(manager_scores)
    record.manager_comment = body.comment
    record.status = "pending_peer"

    db.commit()
    db.refresh(record)

    log_operation(
        db=db,
        user_id=user.id,
        action="score_submit",
        target_type="assessment_record",
        target_id=record_id,
        old_value={"status": old_status, "manager_scores": record.manager_scores},
        new_value={"status": record.status, "manager_scores": manager_scores, "comment": body.comment},
    )

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

    log_operation(
        db=db,
        user_id=user.id,
        action="peer_score_submit",
        target_type="assessment_record",
        target_id=record_id,
        old_value={"peer_scores": record.peer_scores},
        new_value={"peer_scores": peer_scores},
    )

    return {
        "record_id": record_id,
        "peer_scores": peer_scores,
        "status": record.status,
    }


class SelfScoreSubmit(BaseModel):
    performance: float
    ability: float
    attitude: float
    kpi_scores: Optional[List[Any]] = None


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
        # P1-18: 员工只能查看已发布/已归档的考核结果
        # 但员工始终有权查看自己提交的自评分数（self_scores），只隐藏上级/协作评和最终分数
        is_published = r.status in ["published", "archived"]
        self_scores = json.loads(r.self_scores) if r.self_scores else {}
        if user.role == "employee" and not is_published:
            manager_scores = {}
            peer_scores = {}
            weighted_performance = None
            weighted_ability = None
            weighted_attitude = None
            total_score = None
            grade = None
            original_grade = None
            manager_comment = None
        else:
            manager_scores = json.loads(r.manager_scores) if r.manager_scores else {}
            peer_scores = json.loads(r.peer_scores) if r.peer_scores else {}
            weighted_performance = str(r.weighted_performance) if r.weighted_performance else None
            weighted_ability = str(r.weighted_ability) if r.weighted_ability else None
            weighted_attitude = str(r.weighted_attitude) if r.weighted_attitude else None
            total_score = str(r.total_score) if r.total_score else None
            grade = r.grade
            original_grade = r.original_grade
            manager_comment = r.manager_comment

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
            "weighted_performance": weighted_performance,
            "weighted_ability": weighted_ability,
            "weighted_attitude": weighted_attitude,
            "total_score": total_score,
            "grade": grade,
            "original_grade": original_grade,
            "status": r.status,
            "manager_comment": manager_comment,
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

    # 保存 KPI 评分
    if body.kpi_scores:
        _update_kpi_scores(db, record_id, body.kpi_scores, "self")

    old_status = record.status
    record.self_scores = json.dumps(self_scores)
    record.status = "pending_manager"

    db.commit()
    db.refresh(record)

    log_operation(
        db=db,
        user_id=user.id,
        action="self_score_submit",
        target_type="assessment_record",
        target_id=record_id,
        old_value={"status": old_status},
        new_value={"status": record.status, "self_scores": self_scores},
    )

    return {
        "record_id": record_id,
        "self_scores": self_scores,
        "status": record.status,
    }


class ManagerDraftSave(BaseModel):
    performance: Optional[float] = None
    ability: Optional[float] = None
    attitude: Optional[float] = None
    kpi_scores: Optional[List[Any]] = None
    comment: Optional[str] = None


@router.get("/manager-draft/{record_id}")
def get_manager_draft(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "admin", "hr")),
):
    """获取上级评分草稿"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工信息不存在")

    # 权限校验：只能给下属评分
    if record.employee_id not in [e.id for e in current_employee.subordinates]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权为此员工评分")

    draft = json.loads(record.manager_draft_scores) if record.manager_draft_scores else None
    return {
        "record_id": record_id,
        "draft": draft,
        "has_draft": draft is not None,
    }


@router.post("/manager-draft/{record_id}")
def save_manager_draft(
    record_id: int,
    body: ManagerDraftSave,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "admin", "hr")),
):
    """保存上级评分草稿"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工信息不存在")

    # 权限校验：只能给下属评分
    if record.employee_id not in [e.id for e in current_employee.subordinates]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权为此员工评分")

    draft_data = body.model_dump(exclude_unset=True)
    record.manager_draft_scores = json.dumps(draft_data, ensure_ascii=False)
    db.commit()
    db.refresh(record)

    return {
        "record_id": record_id,
        "draft": draft_data,
        "message": "草稿保存成功",
    }


class ScoreDraftSave(BaseModel):
    performance: Optional[float] = None
    ability: Optional[float] = None
    attitude: Optional[float] = None
    kpi_scores: Optional[List[Any]] = None
    comment: Optional[str] = None


def _get_draft_column(role: str) -> str:
    """根据角色返回对应的草稿字段名"""
    mapping = {
        "employee": "self_draft_scores",
        "manager": "manager_draft_scores",
        "peer": "peer_draft_scores",
        "admin": "manager_draft_scores",
        "hr": "manager_draft_scores",
    }
    return mapping.get(role, "manager_draft_scores")


def _check_draft_permission(record, user, db):
    """校验评分草稿权限，返回角色对应的草稿类型标识"""
    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工信息不存在")

    if user.role == "employee":
        if record.employee_id != user.employee_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作此考核记录")
        return "self"
    elif user.role in ["admin", "hr"]:
        return "manager"
    elif user.role == "manager":
        if record.employee_id in [e.id for e in current_employee.subordinates]:
            return "manager"
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权为此员工评分")
    elif user.role == "peer":
        peer_relation = db.query(PeerReviewer).filter(
            PeerReviewer.cycle_id == record.cycle_id,
            PeerReviewer.employee_id == record.employee_id,
            PeerReviewer.reviewer_id == current_employee.id,
        ).first()
        if not peer_relation:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您未被分配为当前员工的协作评分人")
        return "peer"
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作此考核记录")


@router.get("/records/{record_id}/draft")
def get_score_draft(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取评分草稿（统一接口，支持 employee/manager/peer）"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    draft_type = _check_draft_permission(record, user, db)
    column_name = _get_draft_column(draft_type)
    raw_draft = getattr(record, column_name, None)
    draft = json.loads(raw_draft) if raw_draft else None

    return {
        "record_id": record_id,
        "draft": draft,
        "has_draft": draft is not None,
        "draft_type": draft_type,
    }


@router.post("/records/{record_id}/draft")
def save_score_draft(
    record_id: int,
    body: ScoreDraftSave,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """保存评分草稿（统一接口，支持 employee/manager/peer）"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    draft_type = _check_draft_permission(record, user, db)
    column_name = _get_draft_column(draft_type)

    draft_data = body.model_dump(exclude_unset=True)
    setattr(record, column_name, json.dumps(draft_data, ensure_ascii=False))
    db.commit()
    db.refresh(record)

    log_operation(
        db=db,
        user_id=user.id,
        action="save_score_draft",
        target_type="assessment_record",
        target_id=record_id,
        new_value={"draft_type": draft_type, "draft": draft_data},
    )

    return {
        "record_id": record_id,
        "draft": draft_data,
        "draft_type": draft_type,
        "message": "草稿保存成功",
    }


@router.delete("/records/{record_id}/draft")
def delete_score_draft(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除评分草稿（提交评分后调用）"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    draft_type = _check_draft_permission(record, user, db)
    column_name = _get_draft_column(draft_type)

    old_value = getattr(record, column_name, None)
    setattr(record, column_name, None)
    db.commit()
    db.refresh(record)

    log_operation(
        db=db,
        user_id=user.id,
        action="delete_score_draft",
        target_type="assessment_record",
        target_id=record_id,
        old_value={"draft": old_value},
    )

    return {
        "record_id": record_id,
        "draft_type": draft_type,
        "message": "草稿已删除",
    }


@router.get("/records/{record_id}/detail")
def get_assessment_record_detail(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取考核记录详情（包含KPI明细、申诉、面谈）"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    # 权限校验
    if user.role == "employee" and user.employee_id != record.employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看此记录")
    elif user.role == "manager":
        current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
        if not current_employee:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问")
        dept_ids = get_all_dept_ids(db, current_employee.department_id)
        allowed = (
            current_employee.id == record.employee_id
            or _is_in_subordinate_chain(db, current_employee.id, record.employee_id)
            or (record.department_id in dept_ids)
        )
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问")
    # admin, hr, executive: allow all

    # P1-18: 员工只能查看已发布/已归档的考核结果
    if user.role == "employee" and record.status not in ["published", "archived"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="考核结果尚未发布")

    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == record.cycle_id).first()
    emp = db.query(Employee).filter(Employee.id == record.employee_id).first()
    dept = db.query(Department).filter(Department.id == record.department_id).first()
    pos = db.query(Position).filter(Position.id == record.position_id).first()

    self_scores = json.loads(record.self_scores) if record.self_scores else {}
    manager_scores = json.loads(record.manager_scores) if record.manager_scores else {}
    peer_scores = json.loads(record.peer_scores) if record.peer_scores else {}

    # KPI 评分明细
    score_details = db.query(ScoreDetail).filter(ScoreDetail.record_id == record_id).order_by(ScoreDetail.id).all()
    kpi_details = []
    for d in score_details:
        kpi_details.append({
            "kpi_name": d.kpi_name,
            "weight": str(d.weight) if d.weight else None,
            "target_value": d.target_value,
            "self_score": str(d.self_score) if d.self_score else None,
            "manager_score": str(d.manager_score) if d.manager_score else None,
        })

    # 申诉记录
    appeal = db.query(AppealRecord).filter(AppealRecord.record_id == record_id).first()
    appeal_info = None
    if appeal:
        reviewer = db.query(Employee).filter(Employee.id == appeal.reviewer_id).first()
        appeal_info = {
            "id": appeal.id,
            "reason": appeal.reason,
            "detail": appeal.detail,
            "status": appeal.status,
            "review_result": appeal.review_result,
            "reviewer_name": reviewer.name if reviewer else None,
            "resolved_at": appeal.resolved_at.isoformat() if appeal.resolved_at else None,
            "created_at": appeal.created_at.isoformat() if appeal.created_at else None,
        }

    # 面谈记录
    interview = db.query(InterviewRecord).filter(InterviewRecord.record_id == record_id).first()
    interview_info = None
    if interview:
        interviewer = db.query(Employee).filter(Employee.id == interview.interviewer_id).first()
        interview_info = {
            "id": interview.id,
            "interviewer_name": interviewer.name if interviewer else None,
            "interview_time": interview.interview_time.isoformat() if interview.interview_time else None,
            "location": interview.location,
            "content": interview.content,
            "improvement_plan": interview.improvement_plan,
            "created_at": interview.created_at.isoformat() if interview.created_at else None,
        }

    return {
        "record_id": record.id,
        "cycle_id": record.cycle_id,
        "cycle_name": cycle.name if cycle else None,
        "cycle_type": cycle.type if cycle else None,
        "employee_id": record.employee_id,
        "employee_name": emp.name if emp else None,
        "employee_no": emp.employee_no if emp else None,
        "department_name": dept.name if dept else None,
        "position_name": pos.name if pos else None,
        "status": record.status,
        "self_scores": self_scores,
        "manager_scores": manager_scores,
        "peer_scores": peer_scores,
        "weighted_performance": str(record.weighted_performance) if record.weighted_performance else None,
        "weighted_ability": str(record.weighted_ability) if record.weighted_ability else None,
        "weighted_attitude": str(record.weighted_attitude) if record.weighted_attitude else None,
        "total_score": str(record.total_score) if record.total_score else None,
        "grade": record.grade,
        "original_grade": record.original_grade,
        "is_distribution_override": record.is_distribution_override,
        "manager_comment": record.manager_comment,
        "kpi_details": kpi_details,
        "appeal": appeal_info,
        "interview": interview_info,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }
