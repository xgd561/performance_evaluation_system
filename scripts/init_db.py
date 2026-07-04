#!/usr/bin/env python3
"""
系统初始化脚本
运行方式：cd backend && python ../scripts/init_db.py
功能：
1. 创建数据库表（若不存在）
2. 初始化默认系统配置（等级规则、权重、豁免等）
3. 预置系统管理员 + HR 专员账号（供首次登录和演示使用）
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
from app.models import Base, Employee, User, SystemConfig


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


def init_system_configs(db):
    """初始化默认系统配置"""
    configs = [
        {
            "key": "grade_rules",
            "value": '{"A":{"min":90,"max":100,"max_ratio":0.20},'
                     '"B":{"min":80,"max":89.9,"max_ratio":0.50},'
                     '"C":{"min":60,"max":79.9,"max_ratio":0.25},'
                     '"D":{"min":0,"max":59.9,"max_ratio":0.05}}',
        },
        {
            "key": "dimension_weights",
            "value": '{"performance":60,"ability":20,"attitude":20}',
        },
        {
            "key": "reviewer_weights",
            "value": '{"self":10,"manager":70,"peer":20}',
        },
        {
            "key": "small_dept_exemption",
            "value": '{"threshold":5,"enabled":false}',
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
    """预置系统管理员 + HR 专员账号"""
    presets = [
        {
            "employee_no": "010001",
            "name": "张系管",
            "username": "zhangxiguan010001",
            "password": "010001@123",
            "role": "admin",
        },
        {
            "employee_no": "020001",
            "name": "张燕子",
            "username": "zhangyanzi020001",
            "password": "020001@123",
            "role": "hr",
        },
    ]

    for preset in presets:
        # 检查是否已存在
        existing_user = db.query(User).filter(User.username == preset["username"]).first()
        if existing_user:
            print(f"  [~] 用户已存在，跳过: {preset['username']}")
            continue

        # 创建 Employee 记录
        employee = Employee(
            employee_no=preset["employee_no"],
            name=preset["name"],
            is_active=True,
        )
        db.add(employee)
        db.flush()  # 获取 employee.id

        # 创建 User 记录（密码 bcrypt 哈希，首次登录标记为 True）
        user = User(
            username=preset["username"],
            password_hash=hash_password(preset["password"]),
            role=preset["role"],
            employee_id=employee.id,
            is_active=True,
            is_first_login=True,  # 强制首次登录修改密码
        )
        db.add(user)
        db.flush()

        print(f"  [+] 创建账号: {preset['username']} ({preset['name']}, {preset['role']})")
        print(f"      默认密码: {preset['password']}（首次登录必须修改）")

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
    print("\n[1/4] 创建数据库表...")
    init_db()
    print("  完成")

    db = SessionLocal()
    try:
        # 2. 默认配置
        print("\n[2/4] 初始化默认系统配置...")
        init_system_configs(db)

        # 3. 预置账号
        print("\n[3/4] 预置系统账号（管理员 + HR 专员）...")
        create_preset_users(db)

        # 4. 可选自定义管理员
        print("\n[4/4] 自定义管理员（可选）...")
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
    print("  首次登录后系统将强制要求修改密码。")
    print("=" * 50)


if __name__ == "__main__":
    main()
