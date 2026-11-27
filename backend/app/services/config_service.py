import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models import SystemConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 进程内配置缓存（单 Worker 约束）
# ---------------------------------------------------------------------------
# 当前实现使用模块级 dict 作为进程内缓存，适用于单 Worker（单进程）部署。
# 多 Worker 场景下每个进程各持一份缓存，写入后仅 invalidate 本进程缓存，
# 其他进程在下次 TTL 过期前会读到旧值。
#
# 若需多 Worker 部署，须将缓存迁移到集中式存储（如 Redis），
# 或改用每次请求直接读库（去掉 _CACHE）。
#
# ⚠️  WARNING: This in-process cache is NOT safe for multi-worker deployments.
#              Migrate to a shared cache (e.g. Redis) before scaling workers.
# ---------------------------------------------------------------------------

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
