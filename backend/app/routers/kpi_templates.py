from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
import json

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import KpiTemplate, KpiAdjustment, AssessmentRecord, Employee
from app.services.operation_logger import log_operation
from app.schemas import (
    KpiTemplateCreate,
    KpiTemplateSingleCreate,
    KpiTemplateSingleUpdate,
    KpiTemplateUpdate,
    KpiTemplateOut,
    KpiAdjustmentCreate,
    StandardResponse,
)

router = APIRouter()


@router.get("")
def list_kpi_templates(
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    templates = db.query(KpiTemplate).options(joinedload(KpiTemplate.position)).filter(KpiTemplate.is_active == True).all()
    return [
        {
            "id": t.id,
            "position_id": t.position_id,
            "position_name": t.position.name if t.position else None,
            "name": t.name,
            "weight": t.weight,
            "target_value": t.target_value,
            "scoring_method": t.scoring_method,
            "description": t.description,
            "is_active": t.is_active,
            "created_at": t.created_at,
        }
        for t in templates
    ]


@router.post("/single", status_code=status.HTTP_201_CREATED)
def create_kpi_template_single(
    req: KpiTemplateSingleCreate,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin")),
):
    tmpl = KpiTemplate(
        position_id=req.position_id,
        name=req.name,
        weight=req.weight,
        target_value=req.target_value,
        scoring_method=req.scoring_method,
        description=req.description,
    )
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.put("/single/{template_id}")
def update_kpi_template_single(
    template_id: int,
    req: KpiTemplateSingleUpdate,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin")),
):
    tmpl = db.query(KpiTemplate).filter(KpiTemplate.id == template_id).first()
    if not tmpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KPI模板不存在")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(tmpl, field, value)
    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.post("", status_code=status.HTTP_201_CREATED)
def create_kpi_template(
    req: KpiTemplateCreate,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin")),
):
    created_items = []
    for item in req.items:
        tmpl = KpiTemplate(
            position_id=req.position_id,
            name=item.name,
            weight=item.weight,
            target_value=item.target_value,
            scoring_method=item.scoring_method,
            description=item.description,
        )
        db.add(tmpl)
        created_items.append(tmpl)
    db.commit()
    for item in created_items:
        db.refresh(item)
    return {
        "id": created_items[0].id if created_items else None,
        "position_id": req.position_id,
        "items": created_items,
    }


@router.put("/{template_id}")
def update_kpi_template(
    template_id: int,
    req: KpiTemplateUpdate,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin")),
):
    # Deactivate existing templates for this position (simplified approach)
    existing = db.query(KpiTemplate).filter(KpiTemplate.id == template_id).first()
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KPI模板不存在")

    position_id = existing.position_id

    # Deactivate all existing for position
    db.query(KpiTemplate).filter(
        KpiTemplate.position_id == position_id,
    ).update({"is_active": False})

    # Create new items
    created_items = []
    for item in req.items:
        tmpl = KpiTemplate(
            position_id=position_id,
            name=item.name,
            weight=item.weight,
            target_value=item.target_value,
            scoring_method=item.scoring_method,
            description=item.description,
        )
        db.add(tmpl)
        created_items.append(tmpl)
    db.commit()
    for item in created_items:
        db.refresh(item)
    return {
        "id": template_id,
        "position_id": position_id,
        "items": created_items,
    }


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_kpi_template(
    template_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin")),
):
    tmpl = db.query(KpiTemplate).filter(KpiTemplate.id == template_id).first()
    if not tmpl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KPI模板不存在")
    db.delete(tmpl)
    db.commit()
    return


@router.post("/{record_id}/adjust")
def request_kpi_adjustment(
    record_id: int,
    req: KpiAdjustmentCreate,
    db: Session = Depends(get_db),
    user = Depends(require_role("manager", "admin")),
):
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    adj = KpiAdjustment(
        record_id=record_id,
        original_kpi=record.kpi_snapshot or "",
        adjusted_kpi=json.dumps({"kpi_id": req.kpi_id, "new_target": req.new_target}, ensure_ascii=False),
        reason=req.reason,
        status="pending",
    )
    db.add(adj)
    db.commit()
    db.refresh(adj)
    return {"id": adj.id, "status": "待审批", "message": "KPI调整申请已提交"}


def _is_manager_of_record(db: Session, user, adj: KpiAdjustment) -> bool:
    """检查当前用户是否是该调整申请对应员工的直接上级"""
    if not user.employee_id:
        return False
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == adj.record_id).first()
    if not record:
        return False
    emp = db.query(Employee).filter(Employee.id == record.employee_id).first()
    if not emp:
        return False
    return emp.manager_id == user.employee_id


@router.get("/kpi-adjustments/pending")
def list_pending_kpi_adjustments(
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr", "executive", "manager")),
):
    query = db.query(KpiAdjustment).filter(KpiAdjustment.status == "pending")
    if user.role == "manager":
        if not user.employee_id:
            return []
        query = query.join(AssessmentRecord, KpiAdjustment.record_id == AssessmentRecord.id).join(Employee, AssessmentRecord.employee_id == Employee.id).filter(Employee.manager_id == user.employee_id)
    adjustments = query.all()
    return adjustments


@router.post("/kpi-adjustments/{adj_id}/approve")
def approve_kpi_adjustment(
    adj_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr", "manager")),
):
    adj = db.query(KpiAdjustment).filter(KpiAdjustment.id == adj_id).first()
    if not adj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="调整申请不存在")
    if user.role == "manager" and not _is_manager_of_record(db, user, adj):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权审批此调整申请")

    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == adj.record_id).first()
    old_kpi = record.kpi_snapshot if record else None

    adj.status = "approved"
    if record and adj.adjusted_kpi:
        record.kpi_snapshot = adj.adjusted_kpi

    db.commit()

    log_operation(
        db=db,
        user_id=user.id,
        action="approve_kpi_adjustment",
        target_type="kpi_adjustment",
        target_id=adj_id,
        old_value={"kpi_snapshot": old_kpi},
        new_value={"kpi_snapshot": record.kpi_snapshot if record else None},
    )

    return {"status": "approved", "message": "KPI调整已通过"}


@router.post("/kpi-adjustments/{adj_id}/reject")
def reject_kpi_adjustment(
    adj_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr", "manager")),
):
    """驳回KPI调整申请"""
    adj = db.query(KpiAdjustment).filter(KpiAdjustment.id == adj_id).first()
    if not adj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="调整申请不存在")
    if user.role == "manager" and not _is_manager_of_record(db, user, adj):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权审批此调整申请")

    adj.status = "rejected"
    db.commit()

    log_operation(
        db=db,
        user_id=user.id,
        action="reject_kpi_adjustment",
        target_type="kpi_adjustment",
        target_id=adj_id,
    )

    return {"status": "rejected", "message": "KPI调整已驳回"}
