"""
应用配置中心。

从 backend/.env（开发）或系统环境变量（生产）读取所有敏感配置，
统一通过 `settings` 单例向其他模块暴露，禁止在业务代码中直接使用 os.environ。

加载优先级（高→低）：
  1. 系统环境变量
  2. backend/.env 文件（通过 python-dotenv 加载）
  3. 此处定义的默认值（仅供本地开发 fallback，不可用于生产）
"""

import os
import pathlib
from dotenv import load_dotenv

# 自动查找 .env：从本文件向上寻找 backend/ 目录，兼容任意工作目录启动
_HERE = pathlib.Path(__file__).resolve()          # backend/app/core/config.py
_BACKEND_DIR = _HERE.parent.parent.parent         # backend/
_ENV_FILE = _BACKEND_DIR / ".env"

load_dotenv(dotenv_path=_ENV_FILE, override=False)  # 系统环境变量优先，不覆盖已有值


class Settings:
    # ── JWT ──────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = os.environ.get(
        "JWT_SECRET_KEY",
        "your-secret-key-change-in-production",   # 仅供 fallback，生产必须覆盖
    )
    JWT_ALGORITHM: str = os.environ.get("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = int(
        os.environ.get("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")
    )

    # ── 数据库 ────────────────────────────────────────────────────────────────
    # 若 DATABASE_URL 未设置或为空，则根据项目目录自动推导 SQLite 路径
    @property
    def DATABASE_URL(self) -> str:
        url = os.environ.get("DATABASE_URL", "").strip()
        if url:
            return url
        # 默认路径：<项目根>/data/db/performance_evaluation.db
        db_dir = _BACKEND_DIR.parent / "data" / "db"
        db_dir.mkdir(parents=True, exist_ok=True)
        db_path = str(db_dir / "performance_evaluation.db").replace("\\", "/")
        return f"sqlite:///{db_path}"


settings = Settings()
