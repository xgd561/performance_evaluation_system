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

# Use file-based SQLite for tests (shared across connections)
_db_file = tempfile.mktemp(suffix='.db')
TEST_DATABASE_URL = f"sqlite:///{_db_file}"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
    # Override app.database engine and SessionLocal so background tasks use test DB too
    import app.database as app_database
    original_database_engine = app_database.engine
    original_database_sessionlocal = app_database.SessionLocal
    app_database.engine = engine
    app_database.SessionLocal = TestingSessionLocal
    with TestClient(app) as test_client:
        yield test_client
    app.router.on_startup[:] = original_on_startup
    if original_lifespan is not None:
        app.router.lifespan_context = original_lifespan
    app_database.engine = original_database_engine
    app_database.SessionLocal = original_database_sessionlocal
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_user(db_session: Session):
    """Create an admin user with employee."""
    dept = Department(name="管理部", code="ADMIN")
    db_session.add(dept)
    db_session.flush()
    pos = Position(name="系统管理员", department_id=dept.id)
    db_session.add(pos)
    db_session.flush()
    emp = Employee(employee_no="ADMIN001", name="系统管理员", department_id=dept.id, position_id=pos.id)
    db_session.add(emp)
    db_session.flush()
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
    dept = Department(name="人事部", code="HR")
    db_session.add(dept)
    db_session.flush()
    pos = Position(name="HR专员", department_id=dept.id)
    db_session.add(pos)
    db_session.flush()
    emp = Employee(employee_no="HR001", name="张HR", department_id=dept.id, position_id=pos.id)
    db_session.add(emp)
    db_session.flush()
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
    dept = Department(name="高管部", code="EXEC")
    db_session.add(dept)
    db_session.flush()
    pos = Position(name="高管", department_id=dept.id)
    db_session.add(pos)
    db_session.flush()
    emp = Employee(employee_no="EXEC001", name="赵高管", department_id=dept.id, position_id=pos.id)
    db_session.add(emp)
    db_session.flush()
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
    dept = Department(name="协作部", code="PEER")
    db_session.add(dept)
    db_session.flush()
    pos = Position(name="协作人", department_id=dept.id)
    db_session.add(pos)
    db_session.flush()
    emp = Employee(employee_no="PEER001", name="协作员工", department_id=dept.id, position_id=pos.id)
    db_session.add(emp)
    db_session.flush()
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