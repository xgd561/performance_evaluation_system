import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import SystemConfig

# In-memory cache: config_key -> parsed Python dict
_CACHE: dict[str, Any] = {}


def _get_or_create_config(db: Session, key: str, default_value: str) -> SystemConfig:
    cfg = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not cfg:
        cfg = SystemConfig(key=key, value=default_value)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def _fetch(db: Session, key: str, default_value: str) -> dict:
    if key in _CACHE:
        return _CACHE[key]
    cfg = _get_or_create_config(db, key, default_value)
    value = json.loads(cfg.value)
    _CACHE[key] = value
    return value


def clear_config_cache():
    """Clear the entire in-memory config cache."""
    _CACHE.clear()


def invalidate_config_cache(key: str):
    """Invalidate a specific config key from the cache."""
    _CACHE.pop(key, None)


def get_grade_rules(db: Session) -> dict:
    """Return grade rules config. Cached after first DB read."""
    return _fetch(
        db,
        "grade_rules",
        json.dumps({
            "A": {"min": 90, "max": 100, "ratio_limit": 0.2},
            "B": {"min": 80, "max": 89.9, "ratio_limit": 0.5},
            "C": {"min": 60, "max": 79.9, "ratio_limit": 0.25},
            "D": {"min": 0, "max": 59.9, "ratio_limit": 0.05},
        }),
    )


def get_dimension_weights(db: Session) -> dict:
    """Return dimension weights as integer percentages. Cached after first DB read."""
    raw = _fetch(
        db,
        "dimension_weights",
        json.dumps({"performance": 0.6, "ability": 0.2, "attitude": 0.2}),
    )
    result = {}
    for k, v in raw.items():
        if isinstance(v, float) and v <= 1.0:
            result[k] = int(v * 100)
        else:
            result[k] = v
    return result


def get_reviewer_weights(db: Session) -> dict:
    """Return per-dimension reviewer weights. Cached after first DB read."""
    return _fetch(
        db,
        "reviewer_weights",
        json.dumps({
            "performance": {"self": 30, "manager": 70, "peer": 0},
            "ability": {"self": 20, "manager": 60, "peer": 20},
            "attitude": {"self": 10, "manager": 50, "peer": 40},
        }),
    )


def get_small_dept_exemption(db: Session) -> dict:
    """Return small-dept exemption config. Cached after first DB read."""
    return _fetch(
        db,
        "small_dept_exemption",
        json.dumps({"enabled": True, "threshold": 5}),
    )


def get_peer_review_enabled(db: Session) -> dict:
    """Return peer-review enabled flag. Cached after first DB read."""
    return _fetch(
        db,
        "peer_review_enabled",
        json.dumps({"enabled": True}),
    )
