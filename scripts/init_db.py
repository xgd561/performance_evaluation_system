#!/usr/bin/env python3
"""
系统初始化脚本
运行方式：cd backend && python ../scripts/init_db.py
功能：
1. 创建数据库表（若不存在）
2. 初始化默认系统配置（等级规则、权重、豁免等）
3. 预置 7 个演示账号（供首次登录和演示使用）
"""
import sys
import os
import bcrypt
import getpass
import re

# 将 backend 加入模块搜索路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(SCRIPT_DIR, "..", "backend")
sys.path.insert(0, os.path.abspath(BACKEND_DIR))

from app.database import engine, SessionLocal, init_db
from app.models import Base, Employee, User, SystemConfig, Department, Position


def validate_password_strength(password: str) -> bool:
    """校验密码强度：8-16位，必须含大小写字母和数字"""
    if not (8 <= len(password) <= 16):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    return True


def hash_password(password: str) -> str:
    """bcrypt 哈希密码，salt rounds = 10"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=10)).decode("utf-8")


def init_departments_and_positions(db):
    """初始化部门与岗位"""
    depts = [
        {"name": "研发部", "code": "RD"},
        {"name": "产品部", "code": "PD"},
    ]
    dept_map = {}
    for d in depts:
        existing = db.query(Department).filter(Department.code == d["code"]).first()
        if existing:
            dept_map[d["code"]] = existing
            print(f"  [~] 部门已存在，跳过: {d['name']}")
        else:
            dept = Department(name=d["name"], code=d["code"])
            db.add(dept)
            db.flush()
            dept_map[d["code"]] = dept
            print(f"  [+] 创建部门: {d['name']}")

    positions = [
        {"name": "研发工程师", "dept_code": "RD"},
        {"name": "产品经理", "dept_code": "PD"},
    ]
    pos_map = {}
    for p in positions:
        dept = dept_map.get(p["dept_code"])
        existing = db.query(Position).filter(
            Position.name == p["name"],
            Position.department_id == (dept.id if dept else None)
        ).first()
        if existing:
            pos_map[p["name"]] = existing
            print(f"  [~] 岗位已存在，跳过: {p['name']}")
        else:
            pos = Position(name=p["name"], department_id=dept.id if dept else None)
            db.add(pos)
            db.flush()
            pos_map[p["name"]] = pos
            print(f"  [+] 创建岗位: {p['name']}")

    db.commit()
    return dept_map, pos_map


def init_system_configs(db):
    """初始化默认系统配置"""
    configs = [
        {
            "key": "grade_rules",
            "value": '{"A":{"min":90,"max":100,"ratio_limit":0.20},'
                     '"B":{"min":80,"max":89.9,"ratio_limit":0.50},'
                     '"C":{"min":60,"max":79.9,"ratio_limit":0.25},'
                     '"D":{"min":0,"max":59.9,"ratio_limit":0.05}}',
        },
        {
            "key": "dimension_weights",
            "value": '{"performance":0.6,"ability":0.2,"attitude":0.2}',
        },
        {
            "key": "reviewer_weights",
            "value": '{"performance":{"self":0.3,"manager":0.7},'
                     '"ability":{"self":0.2,"manager":0.6,"peer":0.2},'
                     '"attitude":{"self":0.2,"manager":0.8}}',
        },
        {
            "key": "small_dept_exemption",
            "value": '{"threshold":5,"enabled":true}',
        },
        {
            "key": "peer_review_enabled",
            "value": 'true',
        },
    ]

    for cfg in configs:
        existing = db.query(SystemConfig).filter(SystemConfig.key == cfg["key"]).first()
        if not existing:
            db.add(SystemConfig(key=cfg["key"], value=cfg["value"]))
            print(f"  [+] 初始化系统配置: {cfg['key']}")
        else:
            print(f"  [~] 系统配置已存在，跳过: {cfg['key']}")

    db.commit()


def create_preset_users(db):
    """预置 7 个演示账号"""
    # 先获取部门和岗位
    rd_dept = db.query(Department).filter(Department.code == "RD").first()
    pd_dept = db.query(Department).filter(Department.code == "PD").first()
    rd_pos = db.query(Position).filter(
        Position.name == "研发工程师",
        Position.department_id == (rd_dept.id if rd_dept else None)
    ).first()
    pd_pos = db.query(Position).filter(
        Position.name == "产品经理",
        Position.department_id == (pd_dept.id if pd_dept else None)
    ).first()

    presets = [
        {"employee_no": "010001", "name": "张系管", "username": "zhangxiguan010001", "password": "010001@123", "role": "admin", "dept": None, "pos": None, "manager_no": None, "is_head": False},
        {"employee_no": "020001", "name": "张燕子", "username": "zhangyanzi020001", "password": "020001@123", "role": "hr", "dept": None, "pos": None, "manager_no": None, "is_head": False},
        {"employee_no": "030001", "name": "李建国", "username": "lijianguo030001", "password": "030001@123", "role": "manager", "dept": rd_dept, "pos": rd_pos, "manager_no": None, "is_head": True},
        {"employee_no": "040001", "name": "王志强", "username": "wangzhiqiang040001", "password": "040001@123", "role": "employee", "dept": rd_dept, "pos": rd_pos, "manager_no": "030001", "is_head": False},
        {"employee_no": "050001", "name": "刘芳", "username": "liufang050001", "password": "050001@123", "role": "employee", "dept": rd_dept, "pos": rd_pos, "manager_no": "030001", "is_head": False},
        {"employee_no": "060001", "name": "赵晓峰", "username": "zhaoxiaofeng060001", "password": "060001@123", "role": "employee", "dept": pd_dept, "pos": pd_pos, "manager_no": None, "is_head": False},
        {"employee_no": "070001", "name": "陈志强", "username": "chenzhiqiang070001", "password": "070001@123", "role": "executive", "dept": None, "pos": None, "manager_no": None, "is_head": False},
    ]

    # 第一轮：创建所有 Employee（如果不存在）
    employee_map = {}
    for preset in presets:
        existing = db.query(Employee).filter(Employee.employee_no == preset["employee_no"]).first()
        if existing:
            employee_map[preset["employee_no"]] = existing
            print(f"  [~] 员工已存在，跳过: {preset['name']}")
            continue

        employee = Employee(
            employee_no=preset["employee_no"],
            name=preset["name"],
            department_id=preset["dept"].id if preset["dept"] else None,
            position_id=preset["pos"].id if preset["pos"] else None,
            is_department_head=preset["is_head"],
            is_active=True,
        )
        db.add(employee)
        db.flush()
        employee_map[preset["employee_no"]] = employee
        print(f"  [+] 创建员工: {preset['name']}")

    # 第二轮：设置 manager_id
    for preset in presets:
        if preset["manager_no"] and preset["employee_no"] in employee_map:
            manager = employee_map.get(preset["manager_no"])
            if manager:
                employee_map[preset["employee_no"]].manager_id = manager.id

    db.flush()

    # 第三轮：创建 User（如果不存在）
    for preset in presets:
        if preset["employee_no"] not in employee_map:
            continue

        existing_user = db.query(User).filter(User.username == preset["username"]).first()
        if existing_user:
            print(f"  [~] 用户已存在，跳过: {preset['username']}")
            continue

        employee = employee_map[preset["employee_no"]]
        user = User(
            username=preset["username"],
            password_hash=hash_password(preset["password"]),
            role=preset["role"],
            employee_id=employee.id,
            is_active=True,
            is_first_login=True,
        )
        db.add(user)
        print(f"  [+] 创建账号: {preset['username']} ({preset['name']}, {preset['role']})")

    db.commit()


def create_admin_interactive(db):
    """交互式创建自定义管理员（可选）"""
    print("\n是否要额外创建一个自定义管理员账号？（直接回车跳过）")
    choice = input("请输入 y/n [n]: ").strip().lower()
    if choice not in ("y", "yes"):
        print("  跳过自定义管理员创建。")
        return

    username = input("  用户名: ").strip()
    if not username:
        print("  用户名不能为空，跳过。")
        return

    # 检查用户名是否已存在
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        print(f"  用户名 {username} 已存在，跳过。")
        return

    # 密码输入（隐藏回显）
    while True:
        password = getpass.getpass("  密码: ")
        confirm = getpass.getpass("  确认密码: ")
        if password != confirm:
            print("  两次输入不一致，请重新输入。")
            continue
        if not validate_password_strength(password):
            print("  密码强度不足：需 8-16 位，同时含大小写字母和数字。")
            continue
        break

    employee_name = input("  姓名: ").strip() or username
    employee_no = input("  工号: ").strip() or username

    employee = Employee(
        employee_no=employee_no,
        name=employee_name,
        is_active=True,
    )
    db.add(employee)
    db.flush()

    user = User(
        username=username,
        password_hash=hash_password(password),
        role="admin",
        employee_id=employee.id,
        is_active=True,
        is_first_login=True,
    )
    db.add(user)
    db.commit()

    print(f"  [+] 自定义管理员已创建: {username}")


def main():
    # 确保数据库目录存在
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "db"), exist_ok=True)
    print("=" * 50)
    print("绩效考核评分系统 - 初始化脚本")
    print("=" * 50)

    # 1. 创建表
    print("\n[1/5] 创建数据库表...")
    init_db()
    print("  完成")

    db = SessionLocal()
    try:
        # 2. 部门与岗位
        print("\n[2/5] 初始化部门与岗位...")
        init_departments_and_positions(db)

        # 3. 默认配置
        print("\n[3/5] 初始化默认系统配置...")
        init_system_configs(db)

        # 4. 预置账号
        print("\n[4/5] 预置 7 个演示账号...")
        create_preset_users(db)

        # 5. 可选自定义管理员
        print("\n[5/5] 自定义管理员（可选）...")
        create_admin_interactive(db)

    except Exception as e:
        db.rollback()
        print(f"\n[错误] 初始化失败: {e}")
        raise
    finally:
        db.close()

    print("\n" + "=" * 50)
    print("初始化完成。请使用以下账号登录：")
    print("  管理员 : zhangxiguan010001 / 010001@123")
    print("  HR 专员: zhangyanzi020001 / 020001@123")
    print("  经理   : lijianguo030001 / 030001@123")
    print("  员工   : wangzhiqiang040001 / 040001@123")
    print("  员工   : liufang050001 / 050001@123")
    print("  员工   : zhaoxiaofeng060001 / 060001@123")
    print("  高管   : chenzhiqiang070001 / 070001@123")
    print("  首次登录后系统将强制要求修改密码。")
    print("=" * 50)


if __name__ == "__main__":
    main()
