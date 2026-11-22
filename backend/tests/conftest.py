import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

from sqlalchemy import text

import sys
import tempfile
import os

# Force reload of app modules to pick up schema changes in models
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith('app.'):
        del sys.modules[mod_name]

from app.main import app
from app.database import get_db, Base
from app.models import User, Employee, Department, Position
from app.auth import get_password_hash, create_access_token

# --- 统一响应的测试适配 -----------------------------------------------------
# 后端成功响应已统一包装为 {code, message, data}（见 app/core/response.py），
# 而测试断言习惯直接取业务字段（resp.json()["id"]）。
# 这里在测试进程内给 httpx.Response.json 加一层解包，做到适配一处、930+ 断言零改动。
# 需要断言原始信封结构的用例，请读 resp.content / resp.text 自行 json.loads，
# 参见 tests/test_unified_response.py。
import httpx

_RAW_JSON = httpx.Response.json


def _unwrapped_json(self, **kwargs):
    payload = _RAW_JSON(self, **kwargs)
    if 200 <= self.status_code < 300 and isinstance(payload, dict):
        if {"code", "message", "data"}.issubset(payload.keys()) and isinstance(payload.get("code"), int):
            return payload["data"]
    return payload


if not getattr(httpx.Response.json, "_unified_unwrap", False):
    _unwrapped_json._unified_unwrap = True
    httpx.Response.json = _unwrapped_json

# Use file-based SQLite for tests (shared across connections)
_db_file = tempfile.mktemp(suffix='.db')
TEST_DATABASE_URL = f"sqlite:///{_db_file}"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 测试进程内所有数据库访问统一指向测试库：
# 除 get_db 依赖外，仍有不少用例直接调用 app.database.SessionLocal()，
# 只有把模块属性一并替换，才能避免它们写到真实库 data/db/*.db。
import app.database as _app_database

_app_database.engine = engine
_app_database.SessionLocal = TestingSessionLocal


_HASH_CACHE: dict[str, str] = {}


def _cached_hash(password: str) -> str:
    """缓存密码哈希：bcrypt 开销大，而每个用例重建表都会重新写入基础账号。"""
    if password not in _HASH_CACHE:
        _HASH_CACHE[password] = get_password_hash(password)
    return _HASH_CACHE[password]


def _seed_base_data(session: Session) -> None:
    """写入基础部门/岗位/账号，供依赖账号的用例自建业务数据。"""
    departments = [
        ("ADMIN", "管理部"),
        ("HR", "人事部"),
        ("TECH", "技术部"),
        ("PEER", "协作部"),
        ("EXEC", "高管部"),
    ]
    dept_map = {}
    for code, name in departments:
        dept = session.query(Department).filter(Department.code == code).first()
        if not dept:
            dept = Department(name=name, code=code)
            session.add(dept)
            session.flush()
        dept_map[code] = dept

    positions = [
        ("系统管理员", "ADMIN"),
        ("HR专员", "HR"),
        ("技术经理", "TECH"),
        ("Java工程师", "TECH"),
        ("协作人", "PEER"),
        ("高管", "EXEC"),
    ]
    pos_map = {}
    for name, code in positions:
        pos = session.query(Position).filter(Position.name == name).first()
        if not pos:
            pos = Position(name=name, department_id=dept_map[code].id)
            session.add(pos)
            session.flush()
        pos_map[name] = pos

    accounts = [
        ("admin", "admin123", "admin", "ADMIN001", "系统管理员", "系统管理员", "ADMIN"),
        ("hr001", "Hr001@123", "hr", "HR001", "张HR", "HR专员", "HR"),
        ("mgr001", "Mgr001@123", "manager", "MGR001", "李经理", "技术经理", "TECH"),
        ("peer001", "Peer001@123", "peer", "PEER001", "协作员工", "协作人", "PEER"),
        ("emp001", "Emp001@123", "employee", "EMP001", "王员工", "Java工程师", "TECH"),
        ("exec001", "Exec001@123", "executive", "EXEC001", "赵高管", "高管", "EXEC"),
    ]
    for username, password, role, emp_no, emp_name, pos_name, dept_code in accounts:
        emp = session.query(Employee).filter(Employee.employee_no == emp_no).first()
        if not emp:
            emp = Employee(
                employee_no=emp_no,
                name=emp_name,
                department_id=dept_map[dept_code].id,
                position_id=pos_map[pos_name].id,
            )
            session.add(emp)
            session.flush()
        user = session.query(User).filter(User.username == username).first()
        if not user:
            session.add(User(
                username=username,
                password_hash=_cached_hash(password),
                role=role,
                employee_id=emp.id,
                is_first_login=False,
            ))
    session.commit()


# 会话开始前先建表并写入基础账号，供 module 级 fixture 直接使用
Base.metadata.create_all(bind=engine)
_seed_session = TestingSessionLocal()
try:
    _seed_base_data(_seed_session)
finally:
    _seed_session.close()


@pytest.fixture(scope="session")
def test_db_info():
    """暴露测试库位置，供需要直接建引擎的脚本类用例对齐（如 scripts/init_db.py）。"""
    return {"url": TEST_DATABASE_URL, "path": _db_file, "engine": engine}


@pytest.fixture(scope="module", autouse=True)
def _ensure_base_accounts(request):
    """每个模块首次测试前重置测试库并播种基础账号。

    测试库在整个进程内共享，上一个模块遗留的周期/记录（如已归档周期、
    已提交过的记录）会污染后续用例；按模块重建表等价于每个模块独立数据库。
    test_init_db 由 scripts/init_db.py 自行播种演示数据，跳过基础账号播种。
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    if request.module.__name__.split(".")[-1] == "test_init_db":
        return
    session = TestingSessionLocal()
    try:
        _seed_base_data(session)
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _reset_login_rate_limit():
    """清空登录失败计数：它是进程内全局状态，跨用例累积会误触 429 锁定。"""
    from app.routers.auth import _failed_attempts

    _failed_attempts.clear()
    yield
    _failed_attempts.clear()


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test function."""
    # Drop and recreate all tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    conn = engine.connect()
    session = Session(bind=conn)
    return session


@pytest.fixture(scope="function")
def client(db_session: Session):
    """Create a test client with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    # Temporarily remove startup handlers and lifespan to avoid re-initializing file DB
    original_on_startup = app.router.on_startup.copy()
    app.router.on_startup.clear()
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def dummy_lifespan(app):
        yield
    original_lifespan = getattr(app.router, 'lifespan_context', None)
    app.router.lifespan_context = dummy_lifespan
    # 数据库引擎已在模块级统一指向测试库，这里不再临时替换/还原，
    # 避免旧用例把 app.database.SessionLocal 还原回真实库。
    with TestClient(app) as test_client:
        yield test_client
    app.router.on_startup[:] = original_on_startup
    if original_lifespan is not None:
        app.router.lifespan_context = original_lifespan
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_user(db_session: Session):
    """Create an admin user with employee."""
    dept = db_session.query(Department).filter(Department.code == "ADMIN").first()
    if not dept:
        dept = Department(name="管理部", code="ADMIN")
        db_session.add(dept)
        db_session.flush()
    pos = db_session.query(Position).filter(Position.name == "系统管理员").first()
    if not pos:
        pos = Position(name="系统管理员", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
    emp = db_session.query(Employee).filter(Employee.employee_no == "ADMIN001").first()
    if not emp:
        emp = Employee(employee_no="ADMIN001", name="系统管理员", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
    user = db_session.query(User).filter(User.username == "admin").first()
    if not user:
        user = User(
            username="admin",
            password_hash=get_password_hash("admin123"),
            role="admin",
            employee_id=emp.id,
            is_first_login=False,
        )
        db_session.add(user)
        db_session.commit()
    return user


@pytest.fixture(scope="function")
def hr_user(db_session: Session):
    """Create an HR user with employee."""
    dept = db_session.query(Department).filter(Department.code == "HR").first()
    if not dept:
        dept = Department(name="人事部", code="HR")
        db_session.add(dept)
        db_session.flush()
    pos = db_session.query(Position).filter(Position.name == "HR专员").first()
    if not pos:
        pos = Position(name="HR专员", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
    emp = db_session.query(Employee).filter(Employee.employee_no == "HR001").first()
    if not emp:
        emp = Employee(employee_no="HR001", name="张HR", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
    user = db_session.query(User).filter(User.username == "hr001").first()
    if not user:
        user = User(
            username="hr001",
            password_hash=get_password_hash("Hr001@123"),
            role="hr",
            employee_id=emp.id,
            is_first_login=False,
        )
        db_session.add(user)
        db_session.commit()
    return user


@pytest.fixture(scope="function")
def manager_user(db_session: Session):
    """Create a manager user with employee."""
    dept = db_session.query(Department).filter(Department.code == "TECH").first()
    if not dept:
        dept = Department(name="技术部", code="TECH")
        db_session.add(dept)
        db_session.flush()
    pos = db_session.query(Position).filter(Position.name == "技术经理", Position.department_id == dept.id).first()
    if not pos:
        pos = Position(name="技术经理", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
    emp = db_session.query(Employee).filter(Employee.employee_no == "MGR001").first()
    if not emp:
        emp = Employee(employee_no="MGR001", name="李经理", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
    user = db_session.query(User).filter(User.username == "mgr001").first()
    if not user:
        user = User(
            username="mgr001",
            password_hash=get_password_hash("Mgr001@123"),
            role="manager",
            employee_id=emp.id,
            is_first_login=False,
        )
        db_session.add(user)
        db_session.commit()
    return user


@pytest.fixture(scope="function")
def employee_user(db_session: Session):
    """Create a regular employee user."""
    dept = db_session.query(Department).filter(Department.code == "TECH").first()
    if not dept:
        dept = Department(name="技术部", code="TECH")
        db_session.add(dept)
        db_session.flush()
    pos = db_session.query(Position).filter(Position.name == "Java工程师", Position.department_id == dept.id).first()
    if not pos:
        pos = Position(name="Java工程师", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
    emp = db_session.query(Employee).filter(Employee.employee_no == "EMP001").first()
    if not emp:
        emp = Employee(employee_no="EMP001", name="王员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
    user = db_session.query(User).filter(User.username == "emp001").first()
    if not user:
        user = User(
            username="emp001",
            password_hash=get_password_hash("Emp001@123"),
            role="employee",
            employee_id=emp.id,
            is_first_login=False,
        )
        db_session.add(user)
        db_session.commit()
    return user


@pytest.fixture(scope="function")
def first_login_employee(db_session: Session):
    """Create an employee user still in first-login state (must change password)."""
    dept = db_session.query(Department).filter(Department.code == "FIRST_LOGIN").first()
    if not dept:
        dept = Department(name="首登测试部", code="FIRST_LOGIN")
        db_session.add(dept)
        db_session.flush()
    pos = db_session.query(Position).filter(Position.name == "首登测试岗", Position.department_id == dept.id).first()
    if not pos:
        pos = Position(name="首登测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
    emp = db_session.query(Employee).filter(Employee.employee_no == "FL001").first()
    if not emp:
        emp = Employee(employee_no="FL001", name="首登员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
    user = db_session.query(User).filter(User.username == "fl001").first()
    if not user:
        user = User(
            username="fl001",
            password_hash=get_password_hash("Fl001@123"),
            role="employee",
            employee_id=emp.id,
            is_first_login=True,
        )
        db_session.add(user)
        db_session.commit()
    return user


@pytest.fixture(scope="function")
def first_login_token(first_login_employee):
    """Get access token for a user who still needs to change the initial password."""
    return create_access_token(data={"sub": first_login_employee.username})


@pytest.fixture(scope="function")
def admin_token(admin_user):
    """Get admin access token (generated directly to avoid rate limits)."""
    return create_access_token(data={"sub": admin_user.username})


@pytest.fixture(scope="function")
def hr_token(hr_user):
    """Get HR access token (generated directly to avoid rate limits)."""
    return create_access_token(data={"sub": hr_user.username})


@pytest.fixture(scope="function")
def manager_token(manager_user):
    """Get manager access token (generated directly to avoid rate limits)."""
    return create_access_token(data={"sub": manager_user.username})


@pytest.fixture(scope="function")
def employee_token(employee_user):
    """Get employee access token (generated directly to avoid rate limits)."""
    # employee_user 已完成首次改密；首登场景请使用 first_login_token
    return create_access_token(data={"sub": employee_user.username})


@pytest.fixture(scope="function")
def executive_user(db_session: Session):
    """Create an executive user with employee."""
    dept = db_session.query(Department).filter(Department.code == "EXEC").first()
    if not dept:
        dept = Department(name="高管部", code="EXEC")
        db_session.add(dept)
        db_session.flush()
    pos = db_session.query(Position).filter(Position.name == "高管").first()
    if not pos:
        pos = Position(name="高管", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
    emp = db_session.query(Employee).filter(Employee.employee_no == "EXEC001").first()
    if not emp:
        emp = Employee(employee_no="EXEC001", name="赵高管", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
    user = db_session.query(User).filter(User.username == "exec001").first()
    if not user:
        user = User(
            username="exec001",
            password_hash=get_password_hash("Exec001@123"),
            role="executive",
            employee_id=emp.id,
            is_first_login=False,
        )
        db_session.add(user)
        db_session.commit()
    return user


@pytest.fixture(scope="function")
def executive_token(executive_user):
    """Get executive access token (generated directly to avoid rate limits)."""
    return create_access_token(data={"sub": executive_user.username})


@pytest.fixture(scope="function")
def peer_user(db_session: Session):
    """Create a peer user with employee."""
    dept = db_session.query(Department).filter(Department.code == "PEER").first()
    if not dept:
        dept = Department(name="协作部", code="PEER")
        db_session.add(dept)
        db_session.flush()
    pos = db_session.query(Position).filter(Position.name == "协作人").first()
    if not pos:
        pos = Position(name="协作人", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
    emp = db_session.query(Employee).filter(Employee.employee_no == "PEER001").first()
    if not emp:
        emp = Employee(employee_no="PEER001", name="协作员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
    user = db_session.query(User).filter(User.username == "peer001").first()
    if not user:
        user = User(
            username="peer001",
            password_hash=get_password_hash("Peer001@123"),
            role="peer",
            employee_id=emp.id,
            is_first_login=False,
        )
        db_session.add(user)
        db_session.commit()
    return user


@pytest.fixture(scope="function")
def peer_token(peer_user):
    """Get peer access token (generated directly to avoid rate limits)."""
    return create_access_token(data={"sub": peer_user.username})