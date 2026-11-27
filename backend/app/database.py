from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models import Base

from app.core.config import settings

# 数据库 URL 从环境变量/配置中心读取，不再硬编码。
# 默认路径由 settings.DATABASE_URL 属性自动推导（<项目根>/data/db/performance_evaluation.db）。
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

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
