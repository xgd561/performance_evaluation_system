import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import OperationLog


def log_operation(
    db: Session,
    user_id: int,
    action: str,
    target_type: str = None,
    target_id: int = None,
    old_value: dict = None,
    new_value: dict = None,
    ip_address: str = None,
):
    """Write an operation log entry.

    Args:
        db: SQLAlchemy session
        user_id: ID of the user performing the action
        action: Action type string, e.g. 'approve', 'reject', 'score_submit', 'grade_override', 'kpi_adjust'
        target_type: Type of target object, e.g. 'assessment_record', 'approval', 'kpi_adjustment'
        target_id: ID of the target object
        old_value: Snapshot of the object before the change (JSON-serializable dict)
        new_value: Snapshot of the object after the change (JSON-serializable dict)
        ip_address: Client IP address (optional)
    """
    log = OperationLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        old_value=json.dumps(old_value, ensure_ascii=False) if old_value else None,
        new_value=json.dumps(new_value, ensure_ascii=False) if new_value else None,
        ip_address=ip_address,
    )
    db.add(log)
    db.flush()
