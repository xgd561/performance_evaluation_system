from sqlalchemy.orm import Session
from app.models import Notification


def create_notification(db: Session, user_id: int, title: str, content: str = None, type: str = None):
    """创建一条通知记录"""
    notif = Notification(
        user_id=user_id,
        title=title,
        content=content,
        type=type,
        is_read=False,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


def list_user_notifications(db: Session, user_id: int, unread_only: bool = False):
    """查询用户的通知列表"""
    query = db.query(Notification).filter(Notification.user_id == user_id).order_by(Notification.created_at.desc())
    if unread_only:
        query = query.filter(Notification.is_read == False)
    return query.all()


def mark_notification_read(db: Session, notification_id: int, user_id: int):
    """将通知标记为已读"""
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id,
    ).first()
    if notif:
        notif.is_read = True
        db.commit()
        db.refresh(notif)
    return notif
