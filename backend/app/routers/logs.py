from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, timedelta

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import OperationLog, User
from app.schemas import OperationLogOut, OperationLogListResponse

router = APIRouter()


@router.get("", response_model=OperationLogListResponse)
def list_logs(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页条数"),
    action: Optional[str] = Query(None, description="操作类型筛选"),
    target_type: Optional[str] = Query(None, description="目标类型筛选"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr")),
):
    """查询操作日志（支持分页、按操作类型/时间筛选）"""
    query = db.query(OperationLog)

    if action:
        query = query.filter(OperationLog.action == action)
    if target_type:
        query = query.filter(OperationLog.target_type == target_type)
    if start_date:
        query = query.filter(OperationLog.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        # Include the entire end_date day
        query = query.filter(OperationLog.created_at < datetime.combine(end_date + timedelta(days=1), datetime.min.time()))

    total = query.count()

    logs = (
        query.order_by(OperationLog.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    # Build user_id -> username map for the logs
    user_ids = {log.user_id for log in logs}
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_map = {u.id: u.username for u in users}

    items = []
    for log in logs:
        items.append(OperationLogOut(
            id=log.id,
            user_id=log.user_id,
            username=user_map.get(log.user_id),
            action=log.action,
            target_type=log.target_type,
            target_id=log.target_id,
            old_value=log.old_value,
            new_value=log.new_value,
            ip_address=log.ip_address,
            created_at=log.created_at,
        ))

    return {"total": total, "items": items}


@router.get("/actions", response_model=List[str])
def list_actions(
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr")),
):
    """获取所有已存在的操作类型（用于前端筛选下拉）"""
    actions = (
        db.query(OperationLog.action)
        .distinct()
        .order_by(OperationLog.action)
        .all()
    )
    return [a[0] for a in actions]
