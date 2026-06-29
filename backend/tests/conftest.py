import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.database import get_db, Base
from app.models import User, Employee, Department, Position
from app.auth import get_password_hash

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test function."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session):
    """Create a test client with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
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
    dept = Department(name="技术部", code="TECH")
    db_session.add(dept)
    db_session.flush()
    pos = Position(name="技术经理", department_id=dept.id)
    db_session.add(pos)
    db_session.flush()
    emp = Employee(employee_no="MGR001", name="李经理", department_id=dept.id, position_id=pos.id)
    db_session.add(emp)
    db_session.flush()
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
    dept = Department(name="技术部", code="TECH")
    db_session.add(dept)
    db_session.flush()
    pos = Position(name="Java工程师", department_id=dept.id)
    db_session.add(pos)
    db_session.flush()
    emp = Employee(employee_no="EMP001", name="王员工", department_id=dept.id, position_id=pos.id)
    db_session.add(emp)
    db_session.flush()
    user = User(
        username="emp001",
        password_hash=get_password_hash("Emp001@123"),
        role="employee",
        employee_id=emp.id,
        is_first_login=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture(scope="function")
def admin_token(client: TestClient, admin_user):
    """Get admin access token."""
    resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture(scope="function")
def hr_token(client: TestClient, hr_user):
    """Get HR access token."""
    resp = client.post("/auth/login", json={"username": "hr001", "password": "Hr001@123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture(scope="function")
def manager_token(client: TestClient, manager_user):
    """Get manager access token."""
    resp = client.post("/auth/login", json={"username": "mgr001", "password": "Mgr001@123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture(scope="function")
def employee_token(client: TestClient, employee_user):
    """Get employee access token."""
    resp = client.post("/auth/login", json={"username": "emp001", "password": "Emp001@123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]
