import os
import sys
import pytest
import bcrypt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.models import Base, Employee, User, SystemConfig, Department, Position
from init_db import (
    init_system_configs,
    create_preset_users,
    init_departments_and_positions,
    hash_password,
)


class TestHashPassword:
    """验证密码哈希工具"""

    def test_hash_password_returns_bcrypt(self):
        hashed = hash_password("Password123")
        assert hashed.startswith("$2b$")

    def test_hash_password_verifies(self):
        hashed = hash_password("Password123")
        assert bcrypt.checkpw("Password123".encode(), hashed.encode()) is True

    def test_hash_password_different_salts(self):
        h1 = hash_password("Password123")
        h2 = hash_password("Password123")
        assert h1 != h2
        assert bcrypt.checkpw("Password123".encode(), h1.encode())
        assert bcrypt.checkpw("Password123".encode(), h2.encode())


class TestInitDb:
    """验证 init_db.py 初始化逻辑"""

    def test_create_all_tables(self, tmp_path):
        """断言 Base.metadata.create_all 可创建全部 18 张表"""
        db_path = tmp_path / "test_p0_08.db"
        engine = create_engine(
            f"sqlite:///{db_path.as_posix()}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)

        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        expected = {
            "departments", "positions", "employees", "users",
            "assessment_cycles", "kpi_templates", "assessment_records",
            "score_details", "kpi_adjustments", "approval_records",
            "cycle_employees", "peer_reviewers", "operation_logs",
            "appeal_records", "interview_records", "system_configs",
            "notifications", "peer_review_tasks",
        }
        assert expected.issubset(tables), f"缺少表: {expected - tables}"
        assert len(tables) >= 18, f"表数量不足，期望 >= 18，实际 {len(tables)}"

    def test_init_departments_and_positions(self, tmp_path):
        """断言可创建部门与岗位"""
        db_path = tmp_path / "test_p0_08_2.db"
        engine = create_engine(
            f"sqlite:///{db_path.as_posix()}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        try:
            init_departments_and_positions(db)
        finally:
            db.close()

        db = Session()
        try:
            rd = db.query(Department).filter(Department.code == "RD").first()
            assert rd is not None
            assert rd.name == "研发部"

            pd = db.query(Department).filter(Department.code == "PD").first()
            assert pd is not None
            assert pd.name == "产品部"

            pos = db.query(Position).filter(Position.name == "研发工程师").first()
            assert pos is not None
            assert pos.department_id == rd.id

            pos2 = db.query(Position).filter(Position.name == "产品经理").first()
            assert pos2 is not None
            assert pos2.department_id == pd.id
        finally:
            db.close()

    def test_init_system_configs(self, tmp_path):
        """断言可插入 5 条默认系统配置"""
        db_path = tmp_path / "test_p0_08_3.db"
        engine = create_engine(
            f"sqlite:///{db_path.as_posix()}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        try:
            init_system_configs(db)
        finally:
            db.close()

        db = Session()
        try:
            configs = db.query(SystemConfig).all()
            keys = {c.key for c in configs}
            assert keys == {
                "grade_rules",
                "dimension_weights",
                "reviewer_weights",
                "small_dept_exemption",
                "peer_review_enabled",
            }

            grade_rules = db.query(SystemConfig).filter(SystemConfig.key == "grade_rules").first()
            assert "A" in grade_rules.value
            assert "ratio_limit" in grade_rules.value

            reviewer_weights = db.query(SystemConfig).filter(SystemConfig.key == "reviewer_weights").first()
            assert "performance" in reviewer_weights.value
            assert "self" in reviewer_weights.value
        finally:
            db.close()

    def test_create_preset_users(self, tmp_path):
        """断言可创建 7 个预置用户，且汇报关系正确"""
        db_path = tmp_path / "test_p0_08_4.db"
        engine = create_engine(
            f"sqlite:///{db_path.as_posix()}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        try:
            init_departments_and_positions(db)
            init_system_configs(db)
            create_preset_users(db)
        finally:
            db.close()

        db = Session()
        try:
            users = db.query(User).all()
            assert len(users) == 7

            usernames = {u.username for u in users}
            expected = {
                "zhangxiguan010001",
                "zhangyanzi020001",
                "lijianguo030001",
                "wangzhiqiang040001",
                "liufang050001",
                "zhaoxiaofeng060001",
                "chenzhiqiang070001",
            }
            assert expected.issubset(usernames)

            # 验证角色
            roles = {u.username: u.role for u in users}
            assert roles["zhangxiguan010001"] == "admin"
            assert roles["zhangyanzi020001"] == "hr"
            assert roles["lijianguo030001"] == "manager"
            assert roles["chenzhiqiang070001"] == "executive"
            assert roles["wangzhiqiang040001"] == "employee"

            # 验证汇报关系：王志强上级是李建国
            lijianguo = db.query(Employee).filter(Employee.employee_no == "030001").first()
            wangzhiqiang = db.query(Employee).filter(Employee.employee_no == "040001").first()
            assert lijianguo is not None
            assert wangzhiqiang is not None
            assert wangzhiqiang.manager_id == lijianguo.id

            # 验证刘芳上级也是李建国
            liufang = db.query(Employee).filter(Employee.employee_no == "050001").first()
            assert liufang.manager_id == lijianguo.id

            # 验证李建国是部门经理
            assert lijianguo.is_department_head is True

            # 验证密码
            user = db.query(User).filter(User.username == "wangzhiqiang040001").first()
            assert bcrypt.checkpw("040001@123".encode(), user.password_hash.encode())
        finally:
            db.close()

    def test_create_preset_users_idempotent(self, tmp_path):
        """断言重复执行初始化不会重复插入数据"""
        db_path = tmp_path / "test_p0_08_5.db"
        engine = create_engine(
            f"sqlite:///{db_path.as_posix()}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        try:
            init_departments_and_positions(db)
            init_system_configs(db)
            create_preset_users(db)
            create_preset_users(db)  # 第二次应幂等
        finally:
            db.close()

        db = Session()
        try:
            users = db.query(User).all()
            assert len(users) == 7

            employees = db.query(Employee).all()
            assert len(employees) == 7

            depts = db.query(Department).all()
            assert len(depts) == 2

            configs = db.query(SystemConfig).all()
            assert len(configs) == 5
        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
