from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
import json

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import (
    AssessmentRecord, AssessmentCycle, Employee, Department, Position, ScoreDetail, User, PeerReviewer, AppealRecord, InterviewRecord, Notification, ScoreDraft, PeerReviewTask
)

from app.services.operation_logger import log_operation
from app.services.distribution_enforcer import enforce_distribution
from app.services.score_calculator import calculate_weighted_score, calculate_kpi_weighted_performance
from app.services.notification_service import create_notification
from app.utils.workflow_state_machine import WorkflowStateMachine
from app.routers.employees import (
    _is_in_subordinate_chain,
    get_all_dept_ids,
    get_descendant_dept_ids,
)
from app.routers.archive_guard import check_record_not_archived, check_cycle_not_archived

from app.utils.json_columns import load_json

router = APIRouter()


def _get_subordinate_ids(db, current_employee):
    """获取当前经理的所有下属员工ID列表"""
    subordinate_ids = db.query(Employee.id).filter(Employee.manager_id == current_employee.id).all()
    return [sid[0] for sid in subordinate_ids]


def _ensure_score_details(db, record):
    """根据 kpi_snapshot 确保 score_details 记录存在，返回 detail 列表"""
    details = db.query(ScoreDetail).filter(ScoreDetail.record_id == record.id).order_by(ScoreDetail.id).all()
    if details:
        return details
    snapshot = load_json(record.kpi_snapshot, [])
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

        self_scores = load_json(r.self_scores, {})
        manager_scores = load_json(r.manager_scores, {})
        peer_scores = load_json(r.peer_scores, {})

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

    check_cycle_not_archived(cycle_id, db)

    dim_weights = load_json(cycle.dimension_weights, {})
    reviewer_weights = load_json(cycle.reviewer_weights, {})
    grade_rules = load_json(cycle.grade_rules, {})

    # 1. Weight validation
    dim_sum = sum(dim_weights.values()) if isinstance(dim_weights, dict) else 0.0
    if abs(dim_sum - 1.0) > 0.01 and abs(dim_sum - 100.0) > 0.01:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"维度权重之和必须为100%或1.0，当前为{dim_sum}",
        )

    # reviewer_weights is per-dimension, validate each dimension sums to 1.0 or 100.0
    if isinstance(reviewer_weights, dict):
        for dim, rw in reviewer_weights.items():
            if isinstance(rw, dict):
                rw_sum = sum(rw.values())
                if abs(rw_sum - 1.0) > 0.01 and abs(rw_sum - 100.0) > 0.01:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"评分人权重维度 '{dim}' 之和必须为100%或1.0，当前为{rw_sum}",
                    )

    records = db.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == cycle_id).all()

    # 2. Completion check
    incomplete = []
    for r in records:
        if not r.self_scores or r.self_scores == "{}" or r.self_scores == "":
            incomplete.append({"record_id": r.id, "reason": "缺少自评分"})
        if not r.manager_scores or r.manager_scores == "{}" or r.manager_scores == "":
            incomplete.append({"record_id": r.id, "reason": "缺少上级评分"})

    if cycle.peer_review_enabled:
        peer_tasks = db.query(PeerReviewTask).filter(
            PeerReviewTask.record_id.in_([r.id for r in records])
        ).all()
        task_map = {}
        for t in peer_tasks:
            task_map.setdefault(t.record_id, []).append(t)
        for r in records:
            tasks = task_map.get(r.id, [])
            if tasks and any(t.status != "completed" for t in tasks):
                incomplete.append({"record_id": r.id, "reason": "协作评分未完成"})

    if incomplete:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"存在未完成的评分记录: {incomplete}",
        )

    def _map_grade(total):
        for grade, rule in grade_rules.items():
            if isinstance(rule, dict):
                mn = rule.get("min", 0)
                mx = rule.get("max", 100)
                if mn <= total <= mx:
                    return grade
        return "D"

    for r in records:
        self_scores = load_json(r.self_scores, {})
        manager_scores = load_json(r.manager_scores, {})
        peer_scores = load_json(r.peer_scores, {})

        # 如有 KPI 评分，按权重加权计算 performance 维度
        self_kpi_perf = _get_kpi_weighted_performance(db, r.id, "self")
        manager_kpi_perf = _get_kpi_weighted_performance(db, r.id, "manager")

        result = calculate_weighted_score(
            self_scores=load_json(r.self_scores, {}),
            manager_scores=load_json(r.manager_scores, {}),
            peer_scores=load_json(r.peer_scores, {}),
            dim_weights=dim_weights,
            reviewer_weights=reviewer_weights,
            kpi_weighted_self_performance=self_kpi_perf,
            kpi_weighted_manager_performance=manager_kpi_perf,
        )

        r.weighted_performance = result["weighted_performance"]
        r.weighted_ability = result["weighted_ability"]
        r.weighted_attitude = result["weighted_attitude"]
        r.total_score = result["total_score"]
        r.grade = _map_grade(result["total_score"])
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

    # 强制分布受周期开关控制：关闭时只算分不分级，不做任何降级/特批标记
    if cycle.is_distribution_enabled:
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

    # Build a set of employee IDs that have adjustments or override candidates
    adjusted_employee_ids = set()
    for log in all_adjustment_logs:
        adjusted_employee_ids.add(log["employee_id"])
    for cand in all_override_candidates:
        adjusted_employee_ids.add(cand["employee_id"])

    # 4. State machine transition
    pending_distribution_review_count = 0
    pending_approval_count = 0
    for r in records:
        is_distribution_triggered = (
            r.grade != r.original_grade
            or r.is_distribution_override
            or r.employee_id in adjusted_employee_ids
        )
        new_status = WorkflowStateMachine.transition(
            current_state="pending_summary",
            action="trigger_summary",
            is_distribution_triggered=is_distribution_triggered,
            db=db,
            user_id=user.id,
            target_id=r.id,
            target_type="assessment_record",
        )
        r.status = new_status
        if new_status == "pending_distribution_review":
            pending_distribution_review_count += 1
        elif new_status == "pending_approval":
            pending_approval_count += 1

    db.commit()

    # 5. Abnormal count
    abnormal_count = sum(
        1 for r in records
        if r.total_score is not None and (float(r.total_score) < 60 or float(r.total_score) > 98)
    )

    return {
        "calculated": len(records),
        "abnormal_count": abnormal_count,
        "adjustment_count": len(all_adjustment_logs),
        "override_candidate_count": len(all_override_candidates),
        "distribution_enabled": bool(cycle.is_distribution_enabled),
        "pending_distribution_review_count": pending_distribution_review_count,
        "pending_approval_count": pending_approval_count,
        "status": "completed",
    }


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
    status: str = None,
    department_id: int = None,
    keyword: str = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "admin", "hr")),
):
    """获取当前用户的待评列表（上级评），支持状态、部门、关键词筛选"""
    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工信息不存在")

    # 查询当前用户是直属上级的员工
    subordinate_ids = _get_subordinate_ids(db, current_employee)

    if not subordinate_ids:
        return []

    # 查询下属考核记录
    query = db.query(AssessmentRecord).filter(AssessmentRecord.employee_id.in_(subordinate_ids))

    # 状态筛选：默认 pending_manager，可选 pending_peer / pending_summary
    if status:
        query = query.filter(AssessmentRecord.status == status)
    else:
        query = query.filter(AssessmentRecord.status == "pending_manager")

    if department_id:
        query = query.filter(AssessmentRecord.department_id == department_id)

    records = query.order_by(AssessmentRecord.created_at.desc()).all()

    result = []
    for r in records:
        emp = db.query(Employee).filter(Employee.id == r.employee_id).first()
        if not emp:
            continue

        # 关键词筛选（姓名/工号）
        if keyword:
            kw = keyword.lower()
            name_match = emp.name and kw in emp.name.lower()
            no_match = emp.employee_no and kw in emp.employee_no.lower()
            if not name_match and not no_match:
                continue

        dept = db.query(Department).filter(Department.id == r.department_id).first()
        pos = db.query(Position).filter(Position.id == r.position_id).first()
        cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == r.cycle_id).first()

        self_scores = load_json(r.self_scores, {})
        kpi_snapshot = load_json(r.kpi_snapshot, {})

        result.append({
            "record_id": r.id,
            "cycle_id": r.cycle_id,
            "cycle_name": cycle.name if cycle else None,
            "employee_id": r.employee_id,
            "employee_name": emp.name if emp else None,
            "employee_no": emp.employee_no if emp else None,
            "department_id": r.department_id,
            "department_name": dept.name if dept else None,
            "position_name": pos.name if pos else None,
            "status": r.status,
            "self_scores": self_scores,
            "kpi_snapshot": kpi_snapshot,
            "manager_due_date": str(cycle.manager_due_date) if cycle and cycle.manager_due_date else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return result


@router.get("/manager/score-list")
def get_manager_score_list(
    status: str = None,
    department_id: int = None,
    keyword: str = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("manager", "admin", "hr")),
):
    """P4-06: 上级评分列表接口（与 to-review 同逻辑，支持更广泛的状态筛选）"""
    return get_to_review_list(status=status, department_id=department_id, keyword=keyword, db=db, user=user)


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

    check_record_not_archived(record_id, db)

    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工信息不存在")

    # 权限校验：只能给下属评分
    if record.employee_id not in [e.id for e in current_employee.subordinates]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权为此员工评分")

    # 状态校验
    if record.status != "pending_manager":
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
    self_scores = load_json(record.self_scores, {})
    alerts = []
    for dim in ["performance", "ability", "attitude"]:
        m_score = manager_scores.get(dim)
        s_score = self_scores.get(dim)
        if s_score is not None and m_score is not None and abs(float(m_score) - float(s_score)) > 20:
            alerts.append(f"维度[{dim}]上级评分与自评分差异过大: {m_score} vs {s_score}")

    old_status = record.status
    record.manager_scores = manager_scores
    record.manager_comment = body.comment
    record.manager_submitted = True

    # 根据周期配置决定是否进入协作评分阶段
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == record.cycle_id).first()
    peer_review_enabled = not (cycle and cycle.peer_review_enabled is False)
    record.status = WorkflowStateMachine.transition(
        current_state=old_status,
        action="submit_manager",
        db=db,
        user_id=user.id,
        target_id=record_id,
        target_type="assessment_record",
        peer_review_enabled=peer_review_enabled,
    )
    if peer_review_enabled:
        # 创建协作评分任务（PeerReviewTask）
        peer_reviewers = db.query(PeerReviewer).filter(
            PeerReviewer.cycle_id == record.cycle_id,
            PeerReviewer.employee_id == record.employee_id,
        ).all()
        for pr in peer_reviewers:
            existing_task = db.query(PeerReviewTask).filter(
                PeerReviewTask.record_id == record.id,
                PeerReviewTask.reviewer_id == pr.reviewer_id,
            ).first()
            if not existing_task:
                task = PeerReviewTask(
                    record_id=record.id,
                    reviewer_id=pr.reviewer_id,
                    status="pending",
                )
                db.add(task)

    db.commit()
    db.refresh(record)

    # 发送通知给被评员工
    emp_user = db.query(User).filter(User.employee_id == record.employee_id).first()
    if emp_user:
        create_notification(
            db=db,
            user_id=emp_user.id,
            title="上级评分已完成",
            content=f"您的上级已完成评分，当前状态：{record.status}。",
            type="manager_score",
        )

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

    check_record_not_archived(record_id, db)

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
    peer_scores = load_json(record.peer_scores, {})
    peer_scores["ability"] = body.ability

    record.peer_scores = peer_scores
    peer_relation.status = "completed"

    # 同时更新 PeerReviewTask（如有），保证 calculate_scores 能检测到已完成
    peer_task = db.query(PeerReviewTask).filter(
        PeerReviewTask.record_id == record_id,
        PeerReviewTask.reviewer_id == current_employee.id,
    ).first()
    if peer_task:
        peer_task.ability_score = body.ability
        peer_task.status = "completed"
        peer_task.submitted_at = datetime.utcnow()

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
    user: User = Depends(require_role("employee", "manager")),
):
    """获取当前员工的考核记录列表（P6-01：我的绩效）"""
    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        return {"items": [], "total": 0}

    records = db.query(AssessmentRecord).filter(
        AssessmentRecord.employee_id == current_employee.id
    ).order_by(AssessmentRecord.created_at.desc()).all()

    result = []
    for r in records:
        cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == r.cycle_id).first()
        is_published = r.status in ["published", "archived"]
        self_scores = load_json(r.self_scores, {})
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
            kpi_details = []
            is_distribution_override = None
            override_reason = None
            appeal = None
            published_at = None
        else:
            manager_scores = load_json(r.manager_scores, {})
            peer_scores = load_json(r.peer_scores, {})
            weighted_performance = str(r.weighted_performance) if r.weighted_performance else None
            weighted_ability = str(r.weighted_ability) if r.weighted_ability else None
            weighted_attitude = str(r.weighted_attitude) if r.weighted_attitude else None
            total_score = str(r.total_score) if r.total_score else None
            grade = r.grade
            original_grade = r.original_grade
            manager_comment = r.manager_comment
            # KPI 明细
            kpi_details = []
            score_details = db.query(ScoreDetail).filter(ScoreDetail.record_id == r.id).order_by(ScoreDetail.id).all()
            for d in score_details:
                kpi_details.append({
                    "kpi_name": d.kpi_name,
                    "weight": str(d.weight) if d.weight else None,
                    "target_value": d.target_value,
                    "self_score": str(d.self_score) if d.self_score else None,
                    "manager_score": str(d.manager_score) if d.manager_score else None,
                })
            is_distribution_override = r.is_distribution_override
            override_reason = r.override_reason
            # 申诉状态
            appeal_record = db.query(AppealRecord).filter(AppealRecord.record_id == r.id).first()
            if appeal_record:
                appeal = {
                    "id": appeal_record.id,
                    "reason": appeal_record.reason,
                    "detail": appeal_record.detail,
                    "status": appeal_record.status,
                    "review_result": appeal_record.review_result,
                    "resolved_at": appeal_record.resolved_at.isoformat() if appeal_record.resolved_at else None,
                    "created_at": appeal_record.created_at.isoformat() if appeal_record.created_at else None,
                }
            else:
                appeal = None
            published_at = r.updated_at.isoformat() if r.updated_at else None

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
            "kpi_details": kpi_details,
            "is_distribution_override": is_distribution_override,
            "override_reason": override_reason,
            "appeal": appeal,
            "published_at": published_at,
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

    check_record_not_archived(record_id, db)

    # 权限校验：只能评自己的
    if record.employee_id != user.employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作此考核记录")

    # 状态校验：仅待自评状态可提交；周期未启动时应由 HR 先启动周期
    if record.status != "pending_self":
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
    record.self_scores = self_scores
    # 使用状态机执行转换: pending_self -> submit_self -> pending_manager
    # 状态机日志不重复落库：下方写一条业务语义的 self_score_submit 日志
    record.status = WorkflowStateMachine.transition(
        current_state=old_status,
        action="submit_self",
    )

    log_operation(
        db=db,
        user_id=user.id,
        action="self_score_submit",
        target_type="assessment_record",
        target_id=record_id,
        old_value={"status": old_status},
        new_value={"status": record.status, "self_scores": self_scores},
    )

    db.commit()
    db.refresh(record)

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

    draft = load_json(record.manager_draft_scores, None)
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

    check_record_not_archived(record_id, db)

    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工信息不存在")

    # 权限校验：只能给下属评分
    if record.employee_id not in [e.id for e in current_employee.subordinates]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权为此员工评分")

    draft_data = body.model_dump(exclude_unset=True)
    record.manager_draft_scores = draft_data
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

    check_record_not_archived(record_id, db)

    draft_type = _check_draft_permission(record, user, db)
    column_name = _get_draft_column(draft_type)

    draft_data = body.model_dump(exclude_unset=True)
    setattr(record, column_name, draft_data)
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

    check_record_not_archived(record_id, db)

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
        # 本人、下属链、下级部门成员可见；同部门非下属不属授权范围
        allowed = (
            current_employee.id == record.employee_id
            or _is_in_subordinate_chain(db, current_employee.id, record.employee_id)
            or record.department_id
            in get_descendant_dept_ids(db, current_employee.department_id)
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

    self_scores = load_json(record.self_scores, {})
    manager_scores = load_json(record.manager_scores, {})
    peer_scores = load_json(record.peer_scores, {})

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


@router.get("/self/{record_id}")
def get_self_assessment_data(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("employee")),
):
    """加载自评数据：KPI快照、已有自评分、草稿、周期信息"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    if record.employee_id != user.employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看此考核记录")

    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == record.cycle_id).first()
    emp = db.query(Employee).filter(Employee.id == record.employee_id).first()
    dept = db.query(Department).filter(Department.id == record.department_id).first()
    pos = db.query(Position).filter(Position.id == record.position_id).first()

    kpi_snapshot = load_json(record.kpi_snapshot, [])
    if isinstance(kpi_snapshot, dict):
        kpi_items = kpi_snapshot.get("items", [])
    else:
        kpi_items = kpi_snapshot

    self_scores = load_json(record.self_scores, {})

    # 从 score_drafts 表读取 self 草稿
    from app.models import ScoreDraft
    draft = db.query(ScoreDraft).filter(
        ScoreDraft.record_id == record_id,
        ScoreDraft.draft_type == "self",
    ).order_by(ScoreDraft.updated_at.desc()).first()
    draft_data = draft.draft_data if draft else None

    # 计算已存在的 KPI 自评分
    score_details = db.query(ScoreDetail).filter(ScoreDetail.record_id == record_id).order_by(ScoreDetail.id).all()
    kpi_scores = []
    for d in score_details:
        kpi_scores.append({
            "kpi_name": d.kpi_name,
            "weight": str(d.weight) if d.weight else None,
            "target_value": d.target_value,
            "self_score": str(d.self_score) if d.self_score else None,
        })

    return {
        "record_id": record.id,
        "cycle_id": record.cycle_id,
        "cycle_name": cycle.name if cycle else None,
        "cycle_type": cycle.type if cycle else None,
        "cycle_status": cycle.status if cycle else None,
        "self_due_date": str(cycle.self_due_date) if cycle and cycle.self_due_date else None,
        "employee_id": record.employee_id,
        "employee_name": emp.name if emp else None,
        "employee_no": emp.employee_no if emp else None,
        "department_name": dept.name if dept else None,
        "position_name": pos.name if pos else None,
        "status": record.status,
        "kpi_items": kpi_items,
        "kpi_scores": kpi_scores,
        "self_scores": self_scores,
        "draft": draft_data,
        "has_draft": draft_data is not None,
        "dimension_weights": load_json(cycle.dimension_weights, {}) if cycle and cycle.dimension_weights else None,
        "reviewer_weights": load_json(cycle.reviewer_weights, {}) if cycle and cycle.reviewer_weights else None,
    }



# ── P4-13: 协作人待评列表（基于 PeerReviewTask） ──

@router.get("/peer/review-list")
def get_peer_review_list(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("peer")),
):
    """P4-13: 查询当前协作人的待评列表（基于 PeerReviewTask）"""
    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        return {"items": [], "total": 0}

    tasks = db.query(PeerReviewTask).filter(
        PeerReviewTask.reviewer_id == current_employee.id,
    ).order_by(PeerReviewTask.created_at.desc()).all()

    result = []
    for task in tasks:
        record = db.query(AssessmentRecord).filter(AssessmentRecord.id == task.record_id).first()
        if not record:
            continue

        emp = db.query(Employee).filter(Employee.id == record.employee_id).first()
        dept = db.query(Department).filter(Department.id == record.department_id).first()
        pos = db.query(Position).filter(Position.id == record.position_id).first()
        cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == record.cycle_id).first()

        result.append({
            "task_id": task.id,
            "record_id": record.id,
            "cycle_id": record.cycle_id,
            "cycle_name": cycle.name if cycle else None,
            "employee_id": record.employee_id,
            "employee_name": emp.name if emp else None,
            "employee_no": emp.employee_no if emp else None,
            "department_name": dept.name if dept else None,
            "position_name": pos.name if pos else None,
            "status": task.status,
            "ability_score": str(task.ability_score) if task.ability_score else None,
            "comment": task.comment,
            "submitted_at": task.submitted_at.isoformat() if task.submitted_at else None,
            "peer_due_date": str(cycle.peer_due_date) if cycle and cycle.peer_due_date else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "self_scores": load_json(record.self_scores, {}),
            "manager_scores": load_json(record.manager_scores, {}),
            "peer_scores": load_json(record.peer_scores, {}),
        })

    return {"items": result, "total": len(result)}


class PeerReviewTaskSubmit(BaseModel):
    ability: float
    comment: str


@router.post("/peer/review-tasks/{task_id}/submit")
def submit_peer_review_task(
    task_id: int,
    body: PeerReviewTaskSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("peer")),
):
    """P4-14: 协作评分提交（基于 PeerReviewTask）"""
    task = db.query(PeerReviewTask).filter(PeerReviewTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="协作评分任务不存在")

    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if not current_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="员工信息不存在")

    # 权限校验：必须是当前用户自己的任务
    if task.reviewer_id != current_employee.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作此协作评分任务")

    # 状态校验
    if task.status != "pending":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="当前任务已提交，不可重复评分")

    # 分数校验
    if body.ability < 0 or body.ability > 100:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="能力分数需在0-100之间")

    # 评语校验：不少于20字，不超过500字
    if not body.comment or len(body.comment.strip()) < 20:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="协作评语不少于20字")
    if len(body.comment) > 500:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="协作评语不超过500字")

    # 更新任务
    task.ability_score = body.ability
    task.comment = body.comment
    task.status = "completed"
    task.submitted_at = datetime.utcnow()

    db.commit()
    db.refresh(task)

    # 更新考核记录的 peer_scores
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == task.record_id).first()
    emp = db.query(Employee).filter(Employee.id == record.employee_id).first() if record else None
    if record:
        peer_scores = load_json(record.peer_scores, {})
        # 如果有多位协作人，取平均值
        all_peer_tasks = db.query(PeerReviewTask).filter(
            PeerReviewTask.record_id == record.id,
            PeerReviewTask.status == "completed",
        ).all()
        completed_scores = [float(t.ability_score) for t in all_peer_tasks if t.ability_score is not None]
        if completed_scores:
            peer_scores["ability"] = round(sum(completed_scores) / len(completed_scores), 1)
        record.peer_scores = peer_scores
        db.commit()
        db.refresh(record)

        # 检查是否所有协作任务均已完成
        all_tasks = db.query(PeerReviewTask).filter(PeerReviewTask.record_id == record.id).all()
        if all(t.status == "completed" for t in all_tasks):
            record.status = WorkflowStateMachine.transition(
                current_state=record.status,
                action="complete_peer",
                db=db,
                user_id=user.id,
                target_id=record.id,
                target_type="assessment_record",
            )
            db.commit()

            # 通知 HR
            hr_users = db.query(User).filter(User.role == "hr").all()
            for hr in hr_users:
                create_notification(
                    db=db,
                    user_id=hr.id,
                    title="协作评分已全部完成",
                    content=f"员工 {emp.name if emp else record.employee_id} 的所有协作评分任务已完成，当前状态：{record.status}。",
                    type="peer_completed",
                )

    log_operation(
        db=db,
        user_id=user.id,
        action="peer_review_task_submit",
        target_type="peer_review_task",
        target_id=task_id,
        old_value={"status": "pending"},
        new_value={"status": "completed", "ability": body.ability, "comment": body.comment},
    )

    return {
        "task_id": task_id,
        "ability": body.ability,
        "comment": body.comment,
        "status": "completed",
    }


@router.post("/cycles/{cycle_id}/confirm-distribution")
def confirm_distribution(
    cycle_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr")),
):
    """确认强制分布调整，将考核记录从 pending_distribution_review 推进到 pending_approval"""
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核周期不存在")

    check_cycle_not_archived(cycle_id, db)

    records = (
        db.query(AssessmentRecord)
        .filter(AssessmentRecord.cycle_id == cycle_id)
        .filter(AssessmentRecord.status == "pending_distribution_review")
        .all()
    )

    updated = 0
    skipped = []
    for r in records:
        if r.grade is None:
            skipped.append({"record_id": r.id, "reason": "grade is None"})
            continue
        r.original_grade = r.grade
        new_state = WorkflowStateMachine.transition(
            current_state="pending_distribution_review",
            action="confirm_distribution",
            db=db,
            user_id=user.id,
            target_id=r.id,
            target_type="assessment_record",
        )
        r.status = new_state
        updated += 1

    db.commit()

    if updated > 0:
        log_operation(
            db=db,
            user_id=user.id,
            action="confirm_distribution",
            target_type="assessment_cycle",
            target_id=cycle_id,
            old_value={"status": "pending_distribution_review"},
            new_value={"status": "pending_approval"},
        )

    return {
        "updated": updated,
        "cycle_id": cycle_id,
        "status": "pending_approval",
        "skipped": skipped,
    }
