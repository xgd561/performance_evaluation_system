from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import json

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import SystemConfig
from app.schemas import (
    GradeRulesConfig,
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
            "A": {"min": 90, "max": 100},
            "B": {"min": 80, "max": 89.9},
            "C": {"min": 60, "max": 79.9},
            "D": {"min": 0, "max": 59.9},
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
    for grade, g_data in req.items():
        if isinstance(g_data, dict):
            parsed[grade] = g_data
        elif isinstance(g_data, (int, float)):
            if grade == "A":
                parsed[grade] = {"min": g_data, "max": 100}
            elif grade == "B":
                parsed[grade] = {"min": g_data, "max": 89.9}
            elif grade == "C":
                parsed[grade] = {"min": g_data, "max": 79.9}
            elif grade == "D":
                parsed[grade] = {"min": g_data, "max": 59.9}
            else:
                parsed[grade] = {"min": g_data, "max": 100}
        else:
            parsed[grade] = {"min": 0, "max": 100}

    # Validate no overlapping ranges
    grades = [(parsed.get("A"), "A"), (parsed.get("B"), "B"), (parsed.get("C"), "C"), (parsed.get("D"), "D")]
    for i in range(len(grades)):
        for j in range(i + 1, len(grades)):
            g1, n1 = grades[i]
            g2, n2 = grades[j]
            if not g1 or not g2:
                continue
            min1, max1 = g1.get("min", 0), g1.get("max", 0)
            min2, max2 = g2.get("min", 0), g2.get("max", 0)
            if not (max1 < min2 or max2 < min1):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"等级规则区间重叠: {n1} 与 {n2}",
                )

    cfg = _get_or_create_config(db, "grade_rules", "{}")
    cfg.value = json.dumps(parsed)
    db.commit()

    log_operation(
        db=db,
        user_id=user.id,
        action="update_grade_rules",
        target_type="system_config",
        target_id=cfg.id,
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
        json.dumps({"self": 30, "manager": 60, "peer": 10})
    )
    data = json.loads(cfg.value)
    return data


@router.put("/reviewer-weights")
def update_reviewer_weights(
    req: dict,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin")),
):
    data = {k: v for k, v in req.items() if v is not None and isinstance(v, (int, float))}

    total = sum(data.values())
    if total != 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"评分人权重总和必须等于100%，当前为{total}%",
        )

    cfg = _get_or_create_config(db, "reviewer_weights", "{}")
    cfg.value = json.dumps(data)
    db.commit()

    log_operation(
        db=db,
        user_id=user.id,
        action="update_reviewer_weights",
        target_type="system_config",
        target_id=cfg.id,
        new_value={"reviewer_weights": data},
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
