import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

from sqlalchemy import text

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
    # Force drop all tables with foreign keys disabled to handle circular dependencies
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f"DROP TABLE IF EXISTS {table.name}"))
        conn.execute(text("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        with engine.begin() as conn:
            conn.execute(text("PRAGMA foreign_keys=OFF"))
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(text(f"DROP TABLE IF EXISTS {table.name}"))
            conn.execute(text("PRAGMA foreign_keys=ON"))


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
def executive_token(client: TestClient, executive_user):
    """Get executive access token."""
    resp = client.post("/auth/login", json={"username": "exec001", "password": "Exec001@123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


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
def peer_token(client: TestClient, peer_user):
    """Get peer access token."""
    resp = client.post("/auth/login", json={"username": "peer001", "password": "Peer001@123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]
