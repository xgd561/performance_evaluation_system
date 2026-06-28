"""
conftest.py — Shared pytest fixtures and utilities for the Performance Evaluation System test suite.

Tech stack:
  • Backend: Python FastAPI + SQLAlchemy + SQLite
  • Testing: pytest + FastAPI TestClient

Note: Replace `main` with the actual FastAPI application entry module once implemented.
"""

import os
import sys
from typing import Generator

import pytest

# ---------------------------------------------------------------------------
# Path resolution (so we can import the app if it lives under project root)
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------------------------------
# Deferred imports — these will resolve once the application is implemented.
# ---------------------------------------------------------------------------
try:
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, Session

    # TODO: replace `main` with actual app module (e.g. app.main)
    from main import app
except ImportError as _exc:  # pragma: no cover
    app = None  # type: ignore
    TestClient = None  # type: ignore
    Session = None  # type: ignore

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

TEST_USERS = {
    "admin": {"username": "admin", "password": "admin123", "role": "admin"},
    "hr": {"username": "hr001", "password": "Hr001@123", "role": "hr"},
    "manager": {"username": "mgr001", "password": "Mgr001@123", "role": "manager"},
    "employee": {"username": "emp001", "password": "Emp001@123", "role": "employee"},
    "peer": {"username": "peer001", "password": "Peer001@123", "role": "peer"},
}

# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_engine():
    """Create a single in-memory / file-based SQLite engine for the whole test session."""
    if "create_engine" not in globals():
        pytest.skip("SQLAlchemy not available — app not yet implemented")
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator:
    """Yield a fresh SQLAlchemy Session for each test, rolling back on teardown."""
    if test_engine is None:
        pytest.skip("Engine not available")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ---------------------------------------------------------------------------
# Client fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client() -> TestClient:
    """FastAPI TestClient for the lifetime of the test session."""
    if app is None or TestClient is None:
        pytest.skip("FastAPI app not yet implemented — skipping integration tests")
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _get_token(client: TestClient, username: str, password: str) -> str:
    """Login and return the JWT access token."""
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
    data = resp.json()
    return data.get("access_token", data.get("token", ""))


@pytest.fixture(scope="session")
def admin_token(client) -> str:
    """JWT token for admin user."""
    return _get_token(client, TEST_USERS["admin"]["username"], TEST_USERS["admin"]["password"])


@pytest.fixture(scope="session")
def hr_token(client) -> str:
    """JWT token for HR user."""
    return _get_token(client, TEST_USERS["hr"]["username"], TEST_USERS["hr"]["password"])


@pytest.fixture(scope="session")
def manager_token(client) -> str:
    """JWT token for manager (直属上级) user."""
    return _get_token(client, TEST_USERS["manager"]["username"], TEST_USERS["manager"]["password"])


@pytest.fixture(scope="session")
def employee_token(client) -> str:
    """JWT token for employee user."""
    return _get_token(client, TEST_USERS["employee"]["username"], TEST_USERS["employee"]["password"])


@pytest.fixture(scope="session")
def peer_token(client) -> str:
    """JWT token for peer (协作评分人) user."""
    return _get_token(client, TEST_USERS["peer"]["username"], TEST_USERS["peer"]["password"])


@pytest.fixture(scope="session")
def admin_headers(admin_token) -> dict:
    """Auth headers for admin."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def hr_headers(hr_token) -> dict:
    """Auth headers for HR."""
    return {"Authorization": f"Bearer {hr_token}"}


@pytest.fixture(scope="session")
def manager_headers(manager_token) -> dict:
    """Auth headers for manager."""
    return {"Authorization": f"Bearer {manager_token}"}


@pytest.fixture(scope="session")
def employee_headers(employee_token) -> dict:
    """Auth headers for employee."""
    return {"Authorization": f"Bearer {employee_token}"}


@pytest.fixture(scope="session")
def peer_headers(peer_token) -> dict:
    """Auth headers for peer."""
    return {"Authorization": f"Bearer {peer_token}"}


# ---------------------------------------------------------------------------
# Data-seed helpers (used by multiple test modules)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def seeded_department(client, admin_headers) -> dict:
    """Create a department and return its JSON representation."""
    payload = {"name": "技术部", "code": "TECH"}
    resp = client.post("/departments", json=payload, headers=admin_headers)
    if resp.status_code == 409:
        # already exists — fetch by code
        resp = client.get("/departments?code=TECH", headers=admin_headers)
        return resp.json()[0]
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture(scope="session")
def seeded_position(client, admin_headers, seeded_department) -> dict:
    """Create a position under the seeded department."""
    payload = {"name": "Java工程师", "department_id": seeded_department["id"]}
    resp = client.post("/positions", json=payload, headers=admin_headers)
    if resp.status_code == 409:
        resp = client.get("/positions?name=Java工程师", headers=admin_headers)
        return resp.json()[0]
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture(scope="session")
def seeded_employee(client, admin_headers, seeded_department, seeded_position) -> dict:
    """Create a single employee record."""
    payload = {
        "employee_no": "EMP001",
        "name": "张三",
        "department_id": seeded_department["id"],
        "position_id": seeded_position["id"],
        "manager_id": None,
    }
    resp = client.post("/employees", json=payload, headers=admin_headers)
    if resp.status_code == 409:
        resp = client.get("/employees?employee_no=EMP001", headers=admin_headers)
        return resp.json()[0]
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture(scope="session")
def seeded_kpi_template(client, admin_headers, seeded_position) -> dict:
    """Create a KPI template for the seeded position."""
    payload = {
        "position_id": seeded_position["id"],
        "items": [
            {"name": "代码质量", "weight": 40},
            {"name": "项目交付", "weight": 35},
            {"name": "技术分享", "weight": 25},
        ],
    }
    resp = client.post("/kpi-templates", json=payload, headers=admin_headers)
    assert resp.status_code in (200, 201)
    return resp.json()


@pytest.fixture(scope="session")
def seeded_cycle(client, admin_headers) -> dict:
    """Create an assessment cycle."""
    payload = {
        "name": "2026年Q2季度考核",
        "type": "季度",
        "start_date": "2026-04-01",
        "end_date": "2026-06-30",
        "weights": {"业绩": 60, "能力": 20, "态度": 20},
        "grade_rules": {"A": 90, "B": 80, "C": 60, "D": 0},
    }
    resp = client.post("/assessment-cycles", json=payload, headers=admin_headers)
    assert resp.status_code in (200, 201)
    return resp.json()
