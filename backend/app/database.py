from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models import Base

import os

# 数据库文件统一放在项目根级 data/db/ 目录下，便于备份和运维
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "db")
os.makedirs(DB_DIR, exist_ok=True)
_db_path = os.path.join(DB_DIR, "performance_evaluation.db").replace("\\", "/")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{_db_path}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
