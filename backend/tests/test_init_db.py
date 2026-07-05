import os
import sys
import sqlite3
import bcrypt
import pytest
from fastapi.testclient import TestClient

# 确保 backend 在路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module")
def init_db_fixture():
    """
    运行 init_db.py 初始化演示数据，并在测试结束后恢复。
    由于 init_db.py 会操作真实数据库，此 fixture 在模块级别执行一次。
    """
    # 运行初始化脚本
    scripts_dir = os.path.join(os.path.dirname(__file__), '..', 'scripts')
    init_db_path = os.path.join(scripts_dir, 'init_db.py')

    # 动态导入并执行 init_db
    import importlib.util
    spec = importlib.util.spec_from_file_location("init_db", init_db_path)
    init_db_module = importlib.util.module_from_spec(spec)
    sys.modules["init_db"] = init_db_module
    spec.loader.exec_module(init_db_module)
    init_db_module.init_database()

    yield

    # 测试结束后无需特别清理，因为每次运行都会重新初始化


def test_login_all_demo_users(init_db_fixture):
    """
    验收标准：7 个演示账号可正常登录
    """
    users = [
        ("admin", "admin123", "admin", "张系管"),
        ("hr001", "admin123", "hr", "张燕子"),
        ("mgr001", "admin123", "manager", "李建国"),
        ("emp001", "admin123", "employee", "王志强"),
        ("peer001", "admin123", "peer", "刘芳"),
        ("emp002", "admin123", "employee", "赵晓峰"),
        ("emp003", "admin123", "employee", "陈志强"),
    ]

    for username, password, expected_role, expected_name in users:
        res = client.post("/auth/login", json={"username": username, "password": password})
        assert res.status_code == 200, f"用户 {username} 登录失败: {res.status_code}"
        body = res.json()
        assert "access_token" in body, f"用户 {username} 登录响应缺少 access_token"
        assert body["user"]["username"] == username
        assert body["user"]["role"] == expected_role
        assert body["user"]["name"] == expected_name


def test_login_with_wrong_password(init_db_fixture):
    """错误密码应返回 401"""
    res = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
    assert res.status_code == 401


def test_login_nonexistent_user(init_db_fixture):
    """不存在的用户应返回 401"""
    res = client.post("/auth/login", json={"username": "nobody", "password": "admin123"})
    assert res.status_code == 401


def test_manager_subordinate_relationship(init_db_fixture):
    """
    验收标准：汇报关系正确（李建国是王志强的上级）
    通过员工列表接口验证 manager_id 关系
    """
    # 先登录 admin 获取 token
    login_res = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 获取员工列表
    res = client.get("/employees", headers=headers, params={"page": 1, "size": 100})
    assert res.status_code == 200
    body = res.json()
    assert "items" in body

    employees = {item["employee_no"]: item for item in body["items"]}

    # 验证李建国存在
    assert "MGR001" in employees, "未找到李建国(MGR001)"
    li_jianguo = employees["MGR001"]
    assert li_jianguo["name"] == "李建国"

    # 验证王志强存在，且 manager_id 指向李建国
    assert "EMP001" in employees, "未找到王志强(EMP001)"
    wang_zhiqiang = employees["EMP001"]
    assert wang_zhiqiang["name"] == "王志强"
    assert wang_zhiqiang["manager_id"] == li_jianguo["id"], "王志强的上级不是李建国"

    # 验证赵晓峰的上级也是李建国
    assert "EMP002" in employees, "未找到赵晓峰(EMP002)"
    zhao_xiaofeng = employees["EMP002"]
    assert zhao_xiaofeng["name"] == "赵晓峰"
    assert zhao_xiaofeng["manager_id"] == li_jianguo["id"], "赵晓峰的上级不是李建国"

    # 验证陈志强的上级也是李建国
    assert "EMP003" in employees, "未找到陈志强(EMP003)"
    chen_zhiqiang = employees["EMP003"]
    assert chen_zhiqiang["name"] == "陈志强"
    assert chen_zhiqiang["manager_id"] == li_jianguo["id"], "陈志强的上级不是李建国"


def test_department_and_position_structure(init_db_fixture):
    """
    验证部门、岗位结构正确
    """
    login_res = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 部门列表
    dept_res = client.get("/departments", headers=headers)
    assert dept_res.status_code == 200
    departments = dept_res.json()
    assert isinstance(departments, list)
    assert len(departments) == 2

    dept_map = {d["code"]: d for d in departments}
    assert "ADMIN" in dept_map
    assert "TECH" in dept_map

    # 研发部负责人应为李建国
    tech_dept = dept_map["TECH"]
    assert tech_dept["head_id"] is not None

    # 岗位列表
    pos_res = client.get("/positions", headers=headers, params={"page": 1, "size": 100})
    assert pos_res.status_code == 200
    positions = pos_res.json().get("items", [])
    assert len(positions) == 6

    pos_names = {p["name"] for p in positions}
    expected = {"系统管理员", "HR专员", "技术经理", "Java工程师", "产品经理", "协作专员"}
    assert pos_names == expected, f"岗位不匹配: {pos_names}"


def test_password_is_bcrypt_hashed(init_db_fixture):
    """
    验证密码使用了 bcrypt 哈希（而不是明文存储）
    """
    # 直接连接数据库验证
    # tests -> backend -> project_root -> data/db/performance_evaluation.db
    db_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', '..', 'data', 'db', 'performance_evaluation.db'
    )).replace(chr(92), '/')
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users WHERE username = 'admin'")
    row = cur.fetchone()
    conn.close()

    assert row is not None
    password_hash = row[0]
    # bcrypt 哈希以 $2b$ 开头
    assert password_hash.startswith("$2b$"), "密码未使用 bcrypt 哈希"
    # 验证能正确校验
    assert bcrypt.checkpw("admin123".encode('utf-8'), password_hash.encode('utf-8'))
    assert not bcrypt.checkpw("wrong".encode('utf-8'), password_hash.encode('utf-8'))
