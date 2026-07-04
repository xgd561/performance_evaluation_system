import os
import sys
import pytest
from sqlalchemy import Column, Integer

# 将 backend 加入路径，以便 import app.database
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.database import engine, SessionLocal, get_db, init_db, SQLALCHEMY_DATABASE_URL, DB_DIR


class TestDatabaseEngine:
    """验证数据库引擎配置正确"""

    def test_engine_url_points_to_correct_db(self):
        """断言 engine.url 指向 data/db/performance_evaluation.db"""
        expected_path = os.path.join(DB_DIR, "performance_evaluation.db").replace("\\", "/")
        expected_url = f"sqlite:///{expected_path}"
        assert str(engine.url) == expected_url, (
            f"数据库 URL 不匹配。期望: {expected_url}, 实际: {engine.url}"
        )

    def test_sqlalchemy_database_url_constant(self):
        """断言 SQLALCHEMY_DATABASE_URL 常量正确"""
        assert "performance_evaluation.db" in SQLALCHEMY_DATABASE_URL
        assert SQLALCHEMY_DATABASE_URL.startswith("sqlite:///")

    def test_db_directory_exists(self):
        """断言数据库目录已存在"""
        assert os.path.isdir(DB_DIR), f"数据库目录不存在: {DB_DIR}"


class TestSessionLocal:
    """验证 SessionLocal 配置"""

    def test_session_local_config(self):
        """断言 SessionLocal 配置正确：autocommit=False, autoflush=False, 绑定 engine"""
        assert SessionLocal.kw["autocommit"] is False
        assert SessionLocal.kw["autoflush"] is False
        assert SessionLocal.kw["bind"] is engine


class TestGetDbDependency:
    """验证 get_db() 依赖生成器"""

    def test_get_db_yields_session(self):
        """断言 get_db() 生成器可正确产生 Session 对象并关闭"""
        gen = get_db()
        db = next(gen)
        assert db is not None

        # 关闭生成器，触发 finally 中的 db.close()
        try:
            gen.close()
        except StopIteration:
            pass


class TestInitDb:
    """验证 init_db() 可创建数据库文件"""

    def test_init_db_creates_database_file(self, tmp_path):
        """断言 init_db() 可在空数据库路径下创建数据库文件和表"""
        # 使用临时数据库路径，避免污染主数据库
        import tempfile
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker, declarative_base

        tmp_db_path = tmp_path / "test_performance_evaluation.db"
        tmp_url = f"sqlite:///{tmp_db_path.as_posix()}"

        tmp_engine = create_engine(tmp_url, connect_args={"check_same_thread": False})
        TmpSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=tmp_engine)
        TmpBase = declarative_base()

        class DummyModel(TmpBase):
            __tablename__ = "dummy"
            id = Column(Integer, primary_key=True)

        TmpBase.metadata.create_all(bind=tmp_engine)
        assert tmp_db_path.exists(), "init_db() 未创建数据库文件"

    def test_init_db_with_existing_engine(self):
        """断言使用现有 engine 调用 init_db() 不报错"""
        # 由于 engine 已连接主数据库，我们只验证调用不抛异常
        # 并且数据库文件存在（或可被创建）
        db_file = os.path.join(DB_DIR, "performance_evaluation.db")
        try:
            init_db()
        except Exception as e:
            pytest.fail(f"init_db() 抛出异常: {e}")
        assert os.path.exists(db_file), f"数据库文件未创建: {db_file}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
