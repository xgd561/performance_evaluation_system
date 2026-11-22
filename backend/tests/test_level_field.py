"""职级（level）字段：Schema 约束与岗位/员工接口贯通。"""
import pytest
from pydantic import ValidationError

from app.schemas import PositionCreate, EmployeeCreate


@pytest.mark.parametrize("raw, expected", [("P5", "P5"), ("m3", "M3"), (" p10 ", "P10"), ("", None), (None, None)])
def test_level_normalized(raw, expected):
    """合法职级统一转大写去空格；空串归一化为 None。"""
    assert PositionCreate(name="岗位", level=raw).level == expected
    assert EmployeeCreate(employee_no="E1", name="张三", level=raw).level == expected


@pytest.mark.parametrize("bad", ["X1", "P0", "MM1", "P", "高级", "P1.5"])
def test_level_rejected(bad):
    """非 P/M + 1~2 位数字的取值应被拒绝。"""
    with pytest.raises(ValidationError):
        PositionCreate(name="岗位", level=bad)


def test_create_position_with_level(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.post("/api/v1/positions", json={"name": "Java工程师", "level": "p6"}, headers=headers)
    assert resp.status_code == 201, resp.text
    assert resp.json()["level"] == "P6"


def test_create_position_rejects_bad_level(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.post("/api/v1/positions", json={"name": "Java工程师", "level": "资深"}, headers=headers)
    assert resp.status_code == 422, resp.text


def test_create_employee_with_level(client, admin_token, db_session):
    from app.models import Department

    dept = Department(name="研发部", code="RD")
    db_session.add(dept)
    db_session.commit()

    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.post(
        "/api/v1/employees",
        json={"employee_no": "LV001", "name": "李四", "department_id": dept.id, "level": "m2"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["level"] == "M2"
