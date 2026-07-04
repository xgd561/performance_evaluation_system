import os
import sys
import pytest
from sqlalchemy import inspect, Column, Integer, String, Boolean, DateTime, ForeignKey, Text, DECIMAL
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.database import engine, init_db, SessionLocal
from app.models import Base, Department, Position, Employee, User


class TestModelImport:
    """验证模型可导入"""

    def test_import_all_models(self):
        """断言所有 P0-05 模型可导入"""
        from app.models import Department, Position, Employee, User
        assert Department is not None
        assert Position is not None
        assert Employee is not None
        assert User is not None

    def test_base_is_declarative(self):
        """断言 Base 是 SQLAlchemy declarative_base"""
        assert hasattr(Base, "metadata")
        assert hasattr(Base, "registry")


class TestTableCreation:
    """验证 Base.metadata.create_all 可创建表"""

    def test_create_all_tables(self, tmp_path):
        """断言 create_all 可创建数据库文件且不报错"""
        from sqlalchemy import create_engine

        tmp_db = tmp_path / "test_p0_05.db"
        tmp_url = f"sqlite:///{tmp_db.as_posix()}"
        tmp_engine = create_engine(tmp_url, connect_args={"check_same_thread": False})

        try:
            Base.metadata.create_all(bind=tmp_engine)
        except Exception as e:
            pytest.fail(f"Base.metadata.create_all 抛出异常: {e}")

        inspector = inspect(tmp_engine)
        tables = inspector.get_table_names()
        assert "departments" in tables
        assert "positions" in tables
        assert "employees" in tables
        assert "users" in tables


class TestDepartmentModel:
    """验证 Department 模型结构"""

    def test_tablename(self):
        assert Department.__tablename__ == "departments"

    def test_columns(self):
        cols = {c.name for c in Department.__table__.columns}
        assert "id" in cols
        assert "name" in cols
        assert "code" in cols
        assert "parent_id" in cols
        assert "head_id" in cols
        assert "created_at" in cols

    def test_primary_key(self):
        pk = [c.name for c in Department.__table__.primary_key]
        assert "id" in pk

    def test_name_not_nullable(self):
        col = Department.__table__.c.name
        assert col.nullable is False

    def test_code_unique(self):
        col = Department.__table__.c.code
        assert col.unique is True

    def test_parent_id_fk(self):
        col = Department.__table__.c.parent_id
        fks = list(col.foreign_keys)
        assert any("departments.id" in str(fk) for fk in fks)

    def test_head_id_fk(self):
        col = Department.__table__.c.head_id
        fks = list(col.foreign_keys)
        assert any("employees.id" in str(fk) for fk in fks)

    def test_relationships(self):
        assert hasattr(Department, "employees")
        assert hasattr(Department, "positions")


class TestPositionModel:
    """验证 Position 模型结构"""

    def test_tablename(self):
        assert Position.__tablename__ == "positions"

    def test_columns(self):
        cols = {c.name for c in Position.__table__.columns}
        assert "id" in cols
        assert "name" in cols
        assert "department_id" in cols
        assert "created_at" in cols

    def test_department_id_fk(self):
        col = Position.__table__.c.department_id
        fks = list(col.foreign_keys)
        assert any("departments.id" in str(fk) for fk in fks)

    def test_name_not_nullable(self):
        col = Position.__table__.c.name
        assert col.nullable is False

    def test_relationships(self):
        assert hasattr(Position, "department")
        assert hasattr(Position, "employees")
        assert hasattr(Position, "kpi_templates")


class TestEmployeeModel:
    """验证 Employee 模型结构"""

    def test_tablename(self):
        assert Employee.__tablename__ == "employees"

    def test_columns(self):
        cols = {c.name for c in Employee.__table__.columns}
        expected = {
            "id", "employee_no", "name", "department_id",
            "position_id", "manager_id", "is_department_head",
            "is_active", "created_at"
        }
        assert expected.issubset(cols)

    def test_employee_no_unique(self):
        col = Employee.__table__.c.employee_no
        assert col.unique is True
        assert col.nullable is False

    def test_name_not_nullable(self):
        col = Employee.__table__.c.name
        assert col.nullable is False

    def test_manager_id_self_fk(self):
        col = Employee.__table__.c.manager_id
        fks = list(col.foreign_keys)
        assert any("employees.id" in str(fk) for fk in fks)

    def test_department_id_fk(self):
        col = Employee.__table__.c.department_id
        fks = list(col.foreign_keys)
        assert any("departments.id" in str(fk) for fk in fks)

    def test_position_id_fk(self):
        col = Employee.__table__.c.position_id
        fks = list(col.foreign_keys)
        assert any("positions.id" in str(fk) for fk in fks)

    def test_relationships(self):
        assert hasattr(Employee, "department")
        assert hasattr(Employee, "position")
        assert hasattr(Employee, "manager")
        assert hasattr(Employee, "subordinates")
        assert hasattr(Employee, "user")

    def test_default_is_active(self):
        col = Employee.__table__.c.is_active
        assert col.default is not None or str(col.default.arg) == "True"


class TestUserModel:
    """验证 User 模型结构"""

    def test_tablename(self):
        assert User.__tablename__ == "users"

    def test_columns(self):
        cols = {c.name for c in User.__table__.columns}
        expected = {"id", "username", "password_hash", "role", "employee_id", "is_active", "is_first_login", "created_at"}
        assert expected.issubset(cols)

    def test_username_unique(self):
        col = User.__table__.c.username
        assert col.unique is True
        assert col.nullable is False

    def test_password_hash_not_nullable(self):
        col = User.__table__.c.password_hash
        assert col.nullable is False

    def test_role_not_nullable(self):
        col = User.__table__.c.role
        assert col.nullable is False

    def test_employee_id_fk(self):
        col = User.__table__.c.employee_id
        fks = list(col.foreign_keys)
        assert any("employees.id" in str(fk) for fk in fks)

    def test_employee_id_nullable(self):
        col = User.__table__.c.employee_id
        assert col.nullable is True

    def test_relationships(self):
        assert hasattr(User, "employee")

    def test_default_is_first_login(self):
        col = User.__table__.c.is_first_login
        assert col.default is not None or str(col.default.arg) == "True"


class TestCrudOperations:
    """验证基础 CRUD 可正常工作"""

    def test_create_department(self, tmp_path):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        tmp_db = tmp_path / "test_crud.db"
        tmp_url = f"sqlite:///{tmp_db.as_posix()}"
        tmp_engine = create_engine(tmp_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=tmp_engine)
        Session = sessionmaker(bind=tmp_engine)
        session = Session()

        dept = Department(name="研发部", code="RD")
        session.add(dept)
        session.commit()
        session.refresh(dept)

        assert dept.id is not None
        assert dept.name == "研发部"
        assert dept.code == "RD"
        session.close()

    def test_create_position(self, tmp_path):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        tmp_db = tmp_path / "test_crud2.db"
        tmp_url = f"sqlite:///{tmp_db.as_posix()}"
        tmp_engine = create_engine(tmp_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=tmp_engine)
        Session = sessionmaker(bind=tmp_engine)
        session = Session()

        pos = Position(name="研发工程师")
        session.add(pos)
        session.commit()
        session.refresh(pos)

        assert pos.id is not None
        assert pos.name == "研发工程师"
        session.close()

    def test_employee_manager_self_ref(self, tmp_path):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        tmp_db = tmp_path / "test_crud3.db"
        tmp_url = f"sqlite:///{tmp_db.as_posix()}"
        tmp_engine = create_engine(tmp_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=tmp_engine)
        Session = sessionmaker(bind=tmp_engine)
        session = Session()

        manager = Employee(employee_no="E001", name="李建国")
        subordinate = Employee(employee_no="E002", name="王志强", manager_id=manager.id)
        session.add(manager)
        session.flush()  # 获取 manager.id
        subordinate.manager_id = manager.id
        session.add(subordinate)
        session.commit()

        assert manager.id is not None
        assert subordinate.id is not None
        assert subordinate.manager_id == manager.id
        session.close()

    def test_user_employee_relationship(self, tmp_path):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        tmp_db = tmp_path / "test_crud4.db"
        tmp_url = f"sqlite:///{tmp_db.as_posix()}"
        tmp_engine = create_engine(tmp_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=tmp_engine)
        Session = sessionmaker(bind=tmp_engine)
        session = Session()

        emp = Employee(employee_no="E003", name="张系管")
        session.add(emp)
        session.flush()

        user = User(username="zhangxiguan", password_hash="hashed", role="admin", employee_id=emp.id)
        session.add(user)
        session.commit()

        assert user.id is not None
        assert user.employee_id == emp.id
        session.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
