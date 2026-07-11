from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models import AssessmentRecord, AssessmentCycle


def check_record_not_archived(record_id: int, db: Session) -> None:
    """
    检查考核记录所属周期是否已归档。
    若已归档，抛出 400 HTTPException。
    """
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        return
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == record.cycle_id).first()
    if cycle and cycle.status == "archived":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已归档，不可修改",
        )


def check_cycle_not_archived(cycle_id: int, db: Session) -> None:
    """
    检查考核周期是否已归档。
    若已归档，抛出 400 HTTPException。
    """
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == cycle_id).first()
    if cycle and cycle.status == "archived":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已归档，不可修改",
        )
