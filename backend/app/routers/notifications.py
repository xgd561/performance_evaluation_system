from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.auth import get_current_user
from app.models import Notification
from app.schemas import NotificationOut
from app.services.notification_service import list_user_notifications, mark_notification_read

router = APIRouter()


@router.get("", response_model=List[NotificationOut])
def get_notifications(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    """获取当前用户的通知列表"""
    items = list_user_notifications(db, user_id=user.id, unread_only=unread_only)
    return items


@router.post("/{notification_id}/read", response_model=NotificationOut)
def read_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    """将通知标记为已读"""
    notif = mark_notification_read(db, notification_id=notification_id, user_id=user.id)
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知不存在")
    return notif
