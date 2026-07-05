from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import AssessmentRecord, ScoreDraft, User
from app.schemas import ScoreDraftCreate, ScoreDraftOut
from app.services.operation_logger import log_operation

score_drafts_router = APIRouter()


@score_drafts_router.post("")
def create_score_draft(
    body: ScoreDraftCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """保存评分草稿（同一 record_id + draft_type 仅保留最新一条）"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == body.record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    # 权限校验：员工只能操作自己的记录
    if user.role == "employee" and record.employee_id != user.employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作此考核记录")

    # 查找是否已有同类型草稿
    existing = db.query(ScoreDraft).filter(
        ScoreDraft.record_id == body.record_id,
        ScoreDraft.draft_type == body.draft_type,
    ).first()

    if existing:
        existing.draft_data = body.draft_data
        db.commit()
        db.refresh(existing)
        draft = existing
    else:
        draft = ScoreDraft(
            record_id=body.record_id,
            draft_type=body.draft_type,
            draft_data=body.draft_data,
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)

    log_operation(
        db=db,
        user_id=user.id,
        action="save_score_draft",
        target_type="assessment_record",
        target_id=body.record_id,
        new_value={"draft_type": body.draft_type, "draft_data": body.draft_data},
    )

    return draft


@score_drafts_router.get("/{record_id}")
def get_score_draft(
    record_id: int,
    draft_type: str = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """读取评分草稿"""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    if user.role == "employee" and record.employee_id != user.employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看此考核记录")

    query = db.query(ScoreDraft).filter(ScoreDraft.record_id == record_id)
    if draft_type:
        query = query.filter(ScoreDraft.draft_type == draft_type)
    drafts = query.order_by(ScoreDraft.updated_at.desc()).all()

    if draft_type and drafts:
        return drafts[0]
    return drafts
