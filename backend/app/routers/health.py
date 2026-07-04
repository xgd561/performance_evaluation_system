from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db

router = APIRouter()

APP_VERSION = "1.0.0"

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """系统健康检查接口，返回数据库连接状态、当前时间、版本号。"""
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return {
        "code": 0,
        "data": {
            "db": db_status,
            "version": APP_VERSION,
        },
    }
