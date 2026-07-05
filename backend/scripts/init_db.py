import os
import sys
import bcrypt
from datetime import datetime

# 计算项目根目录（backend 的父目录）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 添加 backend 到 Python 路径
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'backend'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Department, Position, Employee, User

# 直接使用项目根目录下的 data/db/performance_evaluation.db
DB_PATH = os.path.join(PROJECT_ROOT, "data", "db", "performance_evaluation.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"


def hash_password(password: str) -> str:
    """使用 bcrypt 哈希密码"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def init_database():
    """
    初始化数据库并创建 7 个演示账号：
    张系管(系统管理员)、张燕子(HR)、李建国(技术经理/部门负责人)、
    王志强(Java工程师)、刘芳(协作评分人)、赵晓峰(Java工程师)、陈志强(产品经理)
    """
    print("=" * 60)
    print("初始化演示数据库")
    print("=" * 60)

    # 确保数据库目录存在
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # 创建所有表
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        print(f"数据库文件路径: {SQLALCHEMY_DATABASE_URL}")
        # 使用 DROP ALL 清空所有表（包括外键关联的数据），然后重新创建
        print("正在清空旧数据...")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        print("OK: 旧数据已清空，表结构已重建")

        # 验证清空
        dept_count = db.query(Department).count()
        print(f"DEBUG: 清空后部门数量: {dept_count}")

        # ============================================================
        # 1. 创建部门
        # ============================================================
        print("\n[1/4] 创建部门...")
        dept_admin = Department(name="管理部", code="ADMIN")
        dept_tech = Department(name="研发部", code="TECH")
        db.add_all([dept_admin, dept_tech])
        db.commit()
        db.refresh(dept_admin)
        db.refresh(dept_tech)
        print(f"  - 管理部 (ID={dept_admin.id})")
        print(f"  - 研发部 (ID={dept_tech.id})")

        # ============================================================
        # 2. 创建岗位
        # ============================================================
        print("\n[2/4] 创建岗位...")
        pos_admin = Position(name="系统管理员", department_id=dept_admin.id)
        pos_hr = Position(name="HR专员", department_id=dept_admin.id)
        pos_tech_mgr = Position(name="技术经理", department_id=dept_tech.id)
        pos_java = Position(name="Java工程师", department_id=dept_tech.id)
        pos_product = Position(name="产品经理", department_id=dept_tech.id)
        pos_peer = Position(name="协作专员", department_id=dept_tech.id)

        db.add_all([pos_admin, pos_hr, pos_tech_mgr, pos_java, pos_product, pos_peer])
        db.commit()
        db.refresh(pos_admin)
        db.refresh(pos_hr)
        db.refresh(pos_tech_mgr)
        db.refresh(pos_java)
        db.refresh(pos_product)
        db.refresh(pos_peer)
        print(f"  - 系统管理员 (ID={pos_admin.id})")
        print(f"  - HR专员 (ID={pos_hr.id})")
        print(f"  - 技术经理 (ID={pos_tech_mgr.id})")
        print(f"  - Java工程师 (ID={pos_java.id})")
        print(f"  - 产品经理 (ID={pos_product.id})")
        print(f"  - 协作专员 (ID={pos_peer.id})")

        # ============================================================
        # 3. 创建员工
        # ============================================================
        print("\n[3/4] 创建员工...")
        employees_data = [
            {
                "employee_no": "ADMIN001",
                "name": "张系管",
                "department_id": dept_admin.id,
                "position_id": pos_admin.id,
                "manager_id": None,
                "is_department_head": False,
                "role": "admin",
                "username": "admin",
            },
            {
                "employee_no": "HR001",
                "name": "张燕子",
                "department_id": dept_admin.id,
                "position_id": pos_hr.id,
                "manager_id": None,
                "is_department_head": False,
                "role": "hr",
                "username": "hr001",
            },
            {
                "employee_no": "MGR001",
                "name": "李建国",
                "department_id": dept_tech.id,
                "position_id": pos_tech_mgr.id,
                "manager_id": None,
                "is_department_head": True,
                "role": "manager",
                "username": "mgr001",
            },
            {
                "employee_no": "EMP001",
                "name": "王志强",
                "department_id": dept_tech.id,
                "position_id": pos_java.id,
                "manager_id": None,  # 将在后面更新为李建国
                "is_department_head": False,
                "role": "employee",
                "username": "emp001",
            },
            {
                "employee_no": "PEER001",
                "name": "刘芳",
                "department_id": dept_tech.id,
                "position_id": pos_peer.id,
                "manager_id": None,
                "is_department_head": False,
                "role": "peer",
                "username": "peer001",
            },
            {
                "employee_no": "EMP002",
                "name": "赵晓峰",
                "department_id": dept_tech.id,
                "position_id": pos_java.id,
                "manager_id": None,  # 将在后面更新为李建国
                "is_department_head": False,
                "role": "employee",
                "username": "emp002",
            },
            {
                "employee_no": "EMP003",
                "name": "陈志强",
                "department_id": dept_tech.id,
                "position_id": pos_product.id,
                "manager_id": None,  # 将在后面更新为李建国
                "is_department_head": False,
                "role": "employee",
                "username": "emp003",
            },
        ]

        employee_map = {}
        for data in employees_data:
            emp = Employee(
                employee_no=data["employee_no"],
                name=data["name"],
                department_id=data["department_id"],
                position_id=data["position_id"],
                manager_id=data["manager_id"],
                is_department_head=data["is_department_head"],
            )
            db.add(emp)
            db.commit()
            db.refresh(emp)
            employee_map[data["employee_no"]] = emp
            print(f"  - {data['name']} ({data['employee_no']}, ID={emp.id})")

        # ============================================================
        # 4. 建立汇报关系（李建国是王志强、赵晓峰、陈志强的上级）
        # ============================================================
        print("\n[4/4] 建立汇报关系...")
        li_jianguo = employee_map["MGR001"]

        wang_zhiqiang = employee_map["EMP001"]
        wang_zhiqiang.manager_id = li_jianguo.id

        zhao_xiaofeng = employee_map["EMP002"]
        zhao_xiaofeng.manager_id = li_jianguo.id

        chen_zhiqiang = employee_map["EMP003"]
        chen_zhiqiang.manager_id = li_jianguo.id

        # 设置研发部负责人为李建国
        dept_tech.head_id = li_jianguo.id

        db.commit()
        print(f"  - 李建国 (ID={li_jianguo.id}) -> 王志强 (ID={wang_zhiqiang.id})")
        print(f"  - 李建国 (ID={li_jianguo.id}) -> 赵晓峰 (ID={zhao_xiaofeng.id})")
        print(f"  - 李建国 (ID={li_jianguo.id}) -> 陈志强 (ID={chen_zhiqiang.id})")
        print(f"  - 研发部负责人: 李建国")

        # ============================================================
        # 5. 创建用户账号（密码统一为 "admin123"，使用 bcrypt 哈希）
        # ============================================================
        print("\n[5/4] 创建用户账号（密码统一为 admin123）...")
        default_password = hash_password("admin123")

        for data in employees_data:
            emp = employee_map[data["employee_no"]]
            user = User(
                username=data["username"],
                password_hash=default_password,
                role=data["role"],
                employee_id=emp.id,
                is_active=True,
                is_first_login=False,
            )
            db.add(user)
            db.commit()
            print(f"  - {data['username']} ({data['role']}) -> {data['name']}")

        print("\n" + "=" * 60)
        print("数据库初始化完成！")
        print("=" * 60)
        print("\n演示账号信息：")
        print("  用户名: admin,   密码: admin123, 角色: admin,   姓名: 张系管")
        print("  用户名: hr001,   密码: admin123, 角色: hr,      姓名: 张燕子")
        print("  用户名: mgr001,  密码: admin123, 角色: manager, 姓名: 李建国")
        print("  用户名: emp001,  密码: admin123, 角色: employee,姓名: 王志强")
        print("  用户名: peer001, 密码: admin123, 角色: peer,    姓名: 刘芳")
        print("  用户名: emp002,  密码: admin123, 角色: employee,姓名: 赵晓峰")
        print("  用户名: emp003,  密码: admin123, 角色: employee,姓名: 陈志强")
        print("\n汇报关系：")
        print("  李建国 -> 王志强")
        print("  李建国 -> 赵晓峰")
        print("  李建国 -> 陈志强")

    except Exception as e:
        db.rollback()
        print(f"\nERROR: 初始化失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
