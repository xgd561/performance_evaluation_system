"""模型驱动迁移：验证旧库缺失列会被自动补齐，且重复执行幂等。"""
import os
import tempfile

from sqlalchemy import create_engine, inspect, text


def _new_engine():
    db_file = tempfile.mktemp(suffix=".db")
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    return engine, db_file


def test_migrate_db_adds_missing_nullable_columns(monkeypatch):
    """模拟旧库（positions/employees 缺 level 列），迁移后应自动补齐。"""
    from app.models import Base

    engine, db_file = _new_engine()
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE positions DROP COLUMN level"))
        conn.execute(text("ALTER TABLE employees DROP COLUMN level"))

    import app.database as app_database
    monkeypatch.setattr(app_database, "engine", engine)

    from app.main import _migrate_db
    _migrate_db()

    assert "level" in {c["name"] for c in inspect(engine).get_columns("positions")}
    assert "level" in {c["name"] for c in inspect(engine).get_columns("employees")}

    # 幂等：再次执行不应报错，也不应重复加列
    _migrate_db()
    position_columns = [c["name"] for c in inspect(engine).get_columns("positions")]
    assert position_columns.count("level") == 1

    engine.dispose()
    os.remove(db_file)


def test_migrate_db_noop_on_current_schema(monkeypatch):
    """库结构与模型一致时，迁移应为空操作。"""
    from app.models import Base

    engine, db_file = _new_engine()
    Base.metadata.create_all(bind=engine)

    import app.database as app_database
    monkeypatch.setattr(app_database, "engine", engine)

    from app.main import _migrate_db
    _migrate_db()

    expected = {t.name for t in Base.metadata.sorted_tables}
    assert expected.issubset(set(inspect(engine).get_table_names()))

    engine.dispose()
    os.remove(db_file)