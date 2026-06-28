"""
utils.py — Shared helper utilities for the test suite.

Provides convenience wrappers for repetitive setup / teardown operations.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover
    TestClient = Any


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def create_user(
    client: TestClient,
    headers: Dict[str, str],
    username: str,
    password: str,
    role: str = "employee",
) -> Dict[str, Any]:
    """Create a user via the admin API."""
    payload = {"username": username, "password": password, "role": role}
    resp = client.post("/users", json=payload, headers=headers)
    if resp.status_code == 409:
        resp = client.get(f"/users?username={username}", headers=headers)
        return resp.json()[0]
    assert resp.status_code == 201, f"create_user failed: {resp.text}"
    return resp.json()


def create_department(
    client: TestClient, headers: Dict[str, str], name: str, code: str
) -> Dict[str, Any]:
    """Create a department."""
    payload = {"name": name, "code": code}
    resp = client.post("/departments", json=payload, headers=headers)
    if resp.status_code == 409:
        resp = client.get(f"/departments?code={code}", headers=headers)
        return resp.json()[0]
    assert resp.status_code == 201
    return resp.json()


def create_position(
    client: TestClient, headers: Dict[str, str], name: str, department_id: int
) -> Dict[str, Any]:
    """Create a position under a department."""
    payload = {"name": name, "department_id": department_id}
    resp = client.post("/positions", json=payload, headers=headers)
    if resp.status_code == 409:
        resp = client.get(f"/positions?name={name}", headers=headers)
        return resp.json()[0]
    assert resp.status_code == 201
    return resp.json()


def create_employee(
    client: TestClient,
    headers: Dict[str, str],
    employee_no: str,
    name: str,
    department_id: int,
    position_id: int,
    manager_id: int | None = None,
) -> Dict[str, Any]:
    """Create an employee record."""
    payload = {
        "employee_no": employee_no,
        "name": name,
        "department_id": department_id,
        "position_id": position_id,
        "manager_id": manager_id,
    }
    resp = client.post("/employees", json=payload, headers=headers)
    if resp.status_code == 409:
        resp = client.get(f"/employees?employee_no={employee_no}", headers=headers)
        return resp.json()[0]
    assert resp.status_code == 201
    return resp.json()


def create_kpi_template(
    client: TestClient,
    headers: Dict[str, str],
    position_id: int,
    items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Create a KPI template for a position."""
    payload = {"position_id": position_id, "items": items}
    resp = client.post("/kpi-templates", json=payload, headers=headers)
    assert resp.status_code in (200, 201)
    return resp.json()


def create_assessment_cycle(
    client: TestClient,
    headers: Dict[str, str],
    name: str,
    cycle_type: str,
    start_date: str,
    end_date: str,
    weights: Dict[str, int],
    grade_rules: Dict[str, int],
) -> Dict[str, Any]:
    """Create an assessment cycle."""
    payload = {
        "name": name,
        "type": cycle_type,
        "start_date": start_date,
        "end_date": end_date,
        "weights": weights,
        "grade_rules": grade_rules,
    }
    resp = client.post("/assessment-cycles", json=payload, headers=headers)
    assert resp.status_code in (200, 201)
    return resp.json()


def launch_cycle(
    client: TestClient, headers: Dict[str, str], cycle_id: int, employee_ids: List[int]
) -> Dict[str, Any]:
    """Launch an assessment cycle for a list of employees."""
    payload = {"cycle_id": cycle_id, "employee_ids": employee_ids}
    resp = client.post("/assessment-cycles/launch", json=payload, headers=headers)
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# Excel helpers
# ---------------------------------------------------------------------------

def make_excel_bytes(row_count: int, headers: List[str], rows: List[List[Any]]) -> bytes:
    """Return a minimal XLSX byte stream (placeholder until openpyxl is available)."""
    # When openpyxl is installed, replace with real Excel generation.
    # For now, return an empty bytes stream so the test can be skipped gracefully.
    try:
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(headers)
        for r in rows:
            ws.append(r)
        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()
    except ImportError:
        return b""


# ---------------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------------

def assert_fields_absent(data: Dict[str, Any], *fields: str) -> None:
    """Assert that a dict does NOT contain any of the listed keys."""
    for f in fields:
        assert f not in data, f"Sensitive field '{f}' leaked in response"


def assert_status_code(resp, expected: int) -> None:
    """Assert response status code with helpful message."""
    assert resp.status_code == expected, (
        f"Expected {expected}, got {resp.status_code}: {resp.text[:200]}"
    )


def assert_json_field(resp, field: str, expected: Any) -> None:
    """Assert a JSON field equals expected value."""
    data = resp.json()
    actual = data.get(field)
    assert actual == expected, (
        f"JSON field '{field}': expected {expected!r}, got {actual!r}"
    )


# ---------------------------------------------------------------------------
# Security / payload helpers
# ---------------------------------------------------------------------------

def sql_injection_payloads() -> List[str]:
    """Return a list of SQL injection strings for security testing."""
    return [
        "' OR '1'='1",
        "1'; DROP TABLE employees; --",
        "' UNION SELECT * FROM users --",
        "1 AND 1=1",
        "1' AND 1=2",
    ]


def xss_payloads() -> List[str]:
    """Return a list of XSS payloads for security testing."""
    return [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert('xss')>",
        "<body onload=alert('xss')>",
        "javascript:alert('xss')",
    ]


def path_traversal_payloads() -> List[str]:
    """Return path traversal strings for security testing."""
    return [
        "../../../etc/passwd",
        "..\\..\\windows\\system32\\drivers\\etc\\hosts",
        "..\\..\\..\\app.py",
    ]


def large_excel_payload(row_count: int = 1000) -> bytes:
    """Generate a large Excel file for performance / exception testing."""
    headers = ["工号", "姓名", "部门", "岗位", "入职日期"]
    rows = []
    for i in range(1, row_count + 1):
        rows.append([f"EMP{i:05d}", f"员工{i}", "技术部", "工程师", "2026-01-01"])
    return make_excel_bytes(row_count, headers, rows)
