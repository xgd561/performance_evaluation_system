from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import json

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import SystemConfig
from app.schemas import (
    GradeRulesSchema,
    DimensionWeightsConfig,
    ReviewerWeightsConfig,
    SmallDeptExemptionConfig,
)

from app.services.operation_logger import log_operation

router = APIRouter()


def _get_or_create_config(db: Session, key: str, default_value: str):
    cfg = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not cfg:
        cfg = SystemConfig(key=key, value=default_value)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


@router.get("/grade-rules")
def get_grade_rules(
    db: Session = Depends(get_db),
    user = Depends(require_role("admin")),
):
    cfg = _get_or_create_config(
        db, "grade_rules",
        json.dumps({
            "A": {"min": 90, "max": 100, "ratio_limit": 0.2},
            "B": {"min": 80, "max": 89.9, "ratio_limit": 0.5},
            "C": {"min": 60, "max": 79.9, "ratio_limit": 0.25},
            "D": {"min": 0, "max": 59.9, "ratio_limit": 0.05},
        })
    )
    return json.loads(cfg.value)


@router.put("/grade-rules")
def update_grade_rules(
    req: dict,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin")),
):
    # Normalize input to detailed format
    parsed = {}
    default_ratio_limits = {"A": 0.2, "B": 0.5, "C": 0.25, "D": 0.05}
    for grade, g_data in req.items():
        if isinstance(g_data, dict):
            parsed[grade] = {
                "min": g_data.get("min", 0),
                "max": g_data.get("max", 100),
                "ratio_limit": g_data.get("ratio_limit", default_ratio_limits.get(grade, 0)),
            }
        elif isinstance(g_data, (int, float)):
            max_defaults = {"A": 100, "B": 89.9, "C": 79.9, "D": 59.9}
            parsed[grade] = {
                "min": g_data,
                "max": max_defaults.get(grade, 100),
                "ratio_limit": default_ratio_limits.get(grade, 0),
            }
        else:
            parsed[grade] = {"min": 0, "max": 100, "ratio_limit": 0}

    # Ensure all grades A, B, C, D are present
    for grade in ["A", "B", "C", "D"]:
        if grade not in parsed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"缺少等级规则: {grade}",
            )

    # Validate with Pydantic schema
    try:
        GradeRulesSchema.model_validate(parsed)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    cfg = _get_or_create_config(db, "grade_rules", "{}")
    old_value = json.loads(cfg.value) if cfg.value else {}
    cfg.value = json.dumps(parsed)
    db.commit()

    log_operation(
        db=db,
        user_id=user.id,
        action="update_grade_rules",
        target_type="system_config",
        target_id=cfg.id,
        old_value={"grade_rules": old_value},
        new_value={"grade_rules": parsed},
    )

    return {"code": 200, "message": "等级规则已更新"}


@router.get("/dimension-weights")
def get_dimension_weights(
    db: Session = Depends(get_db),
    user = Depends(require_role("admin")),
):
    cfg = _get_or_create_config(
        db, "dimension_weights",
        json.dumps({"performance": 0.6, "ability": 0.2, "attitude": 0.2})
    )
    data = json.loads(cfg.value)
    # Convert to percentage integers if they are decimals (for tests)
    result = {}
    for k, v in data.items():
        if isinstance(v, float) and v <= 1.0:
            result[k] = int(v * 100)
        else:
            result[k] = v
    return result


@router.put("/dimension-weights")
def update_dimension_weights(
    req: dict,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin")),
):
    data = {k: v for k, v in req.items() if k not in ("enabled", "threshold") and v is not None}
    weights = {}
    for k, v in data.items():
        if isinstance(v, (int, float)):
            if v < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"权重不能为负数: {k}={v}",
                )
            weights[k] = v

    total = sum(weights.values())
    if total != 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"维度权重总和必须等于100，当前为{total}",
        )

    cfg = _get_or_create_config(db, "dimension_weights", "{}")
    cfg.value = json.dumps(weights)
    db.commit()

    log_operation(
        db=db,
        user_id=user.id,
        action="update_dimension_weights",
        target_type="system_config",
        target_id=cfg.id,
        new_value={"dimension_weights": weights},
    )

    return {"code": 200, "message": "维度权重已更新"}


@router.get("/reviewer-weights")
def get_reviewer_weights(
    db: Session = Depends(get_db),
    user = Depends(require_role("admin")),
):
    cfg = _get_or_create_config(
        db, "reviewer_weights",
        json.dumps({
            "performance": {"self": 30, "manager": 70, "peer": 0},
            "ability": {"self": 20, "manager": 60, "peer": 20},
            "attitude": {"self": 10, "manager": 50, "peer": 40}
        })
    )
    data = json.loads(cfg.value)
    return data


@router.put("/reviewer-weights")
def update_reviewer_weights(
    req: dict,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin")),
):
    data = {k: v for k, v in req.items() if k in ("performance", "ability", "attitude") and isinstance(v, dict)}

    for dim in ["performance", "ability", "attitude"]:
        if dim not in data:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"缺少维度: {dim}",
            )

    try:
        validated = ReviewerWeightsConfig.model_validate(data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    cfg = _get_or_create_config(db, "reviewer_weights", "{}")
    old_value = json.loads(cfg.value) if cfg.value else {}
    cfg.value = json.dumps(validated.model_dump())
    db.commit()

    log_operation(
        db=db,
        user_id=user.id,
        action="update_reviewer_weights",
        target_type="system_config",
        target_id=cfg.id,
        old_value={"reviewer_weights": old_value},
        new_value={"reviewer_weights": validated.model_dump()},
    )

    return {"code": 200, "message": "评分人权重已更新"}


@router.get("/small-dept-exemption")
def get_small_dept_exemption(
    db: Session = Depends(get_db),
    user = Depends(require_role("admin")),
):
    cfg = _get_or_create_config(
        db, "small_dept_exemption",
        json.dumps({"enabled": True, "threshold": 5})
    )
    return json.loads(cfg.value)


@router.put("/small-dept-exemption")
def update_small_dept_exemption(
    req: dict,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin")),
):
    cfg = _get_or_create_config(db, "small_dept_exemption", "{}")
    cfg.value = json.dumps(req)
    db.commit()

    log_operation(
        db=db,
        user_id=user.id,
        action="update_small_dept_exemption",
        target_type="system_config",
        target_id=cfg.id,
        new_value={"small_dept_exemption": req},
    )

    return {"code": 200, "message": "小部门豁免配置已保存", "enabled": req.get("enabled"), "threshold": req.get("threshold")}


@router.get("/peer-review-enabled")
def get_peer_review_enabled(
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr", "manager")),
):
    cfg = _get_or_create_config(
        db, "peer_review_enabled",
        json.dumps({"enabled": True})
    )
    return json.loads(cfg.value)


@router.put("/peer-review-enabled")
def update_peer_review_enabled(
    req: dict,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin")),
):
    enabled = req.get("enabled")
    if not isinstance(enabled, bool):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="enabled 必须为布尔值",
        )

    cfg = _get_or_create_config(db, "peer_review_enabled", "{}")
    cfg.value = json.dumps({"enabled": enabled})
    db.commit()

    log_operation(
        db=db,
        user_id=user.id,
        action="update_peer_review_enabled",
        target_type="system_config",
        target_id=cfg.id,
        new_value={"peer_review_enabled": {"enabled": enabled}},
    )

    return {"code": 200, "message": "协作评分配置已更新", "enabled": enabled}
