"""考核周期权重的默认值与入参判别回归测试。

约束：
1. 创建周期时若请求未携带 `weights`，维度权重与评分人权重都应取自
   `app.services.config_service` 的全局默认值，而不是路由层硬编码。
2. `weights` 单字段按键名判别语义：`self/manager/peer` 为评分人权重，
   `performance/ability/attitude` 为维度权重，两类键不可混传。
"""
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.utils.json_columns import load_json


def _payload(name, **extra):
    today = date.today()
    body = {
        "name": name,
        "type": "monthly",
        "start_date": str(today + timedelta(days=1)),
        "end_date": str(today + timedelta(days=30)),
        "grade_rules": {"A": 90, "B": 80, "C": 60, "D": 0},
    }
    body.update(extra)
    return body


def test_create_cycle_uses_global_default_weights(client: TestClient, db_session, admin_token):
    payload = _payload("默认权重周期")
    resp = client.post(
        "/api/v1/assessment-cycles",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201, resp.text

    from app.models import AssessmentCycle

    cycle = db_session.query(AssessmentCycle).filter(AssessmentCycle.name == payload["name"]).first()
    dimension_weights = load_json(cycle.dimension_weights)
    reviewer_weights = load_json(cycle.reviewer_weights)

    # 维度权重固定取 get_dimension_weights 的全局默认值（60/20/20）
    assert dimension_weights == {"performance": 60, "ability": 20, "attitude": 20}, dimension_weights
    # 评分人权重取 get_reviewer_weights 的按维度默认值
    assert reviewer_weights["performance"] == {"self": 30, "manager": 70, "peer": 0}, reviewer_weights
    assert reviewer_weights["ability"] == {"self": 20, "manager": 60, "peer": 20}, reviewer_weights
    assert reviewer_weights["attitude"] == {"self": 10, "manager": 50, "peer": 40}, reviewer_weights


def test_weights_with_reviewer_keys_goes_to_reviewer_weights(client: TestClient, db_session, admin_token):
    payload = _payload("评分人权重周期", weights={"self": 20, "manager": 60, "peer": 20})
    resp = client.post(
        "/api/v1/assessment-cycles",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201, resp.text

    from app.models import AssessmentCycle

    cycle = db_session.query(AssessmentCycle).filter(AssessmentCycle.name == payload["name"]).first()
    assert load_json(cycle.reviewer_weights) == {"self": 20, "manager": 60, "peer": 20}
    # 维度权重仍取全局默认值
    assert load_json(cycle.dimension_weights) == {"performance": 60, "ability": 20, "attitude": 20}


def test_weights_with_dimension_keys_goes_to_dimension_weights(client: TestClient, db_session, admin_token):
    payload = _payload("维度权重周期", weights={"performance": 50, "ability": 30, "attitude": 20})
    resp = client.post(
        "/api/v1/assessment-cycles",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201, resp.text

    from app.models import AssessmentCycle

    cycle = db_session.query(AssessmentCycle).filter(AssessmentCycle.name == payload["name"]).first()
    assert load_json(cycle.dimension_weights) == {"performance": 50, "ability": 30, "attitude": 20}
    # 评分人权重仍取全局默认值
    assert load_json(cycle.reviewer_weights)["performance"] == {"self": 30, "manager": 70, "peer": 0}


def test_weights_mixing_two_key_groups_rejected(client: TestClient, db_session, admin_token):
    payload = _payload("混传权重周期", weights={"self": 50, "performance": 50})
    resp = client.post(
        "/api/v1/assessment-cycles",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422, resp.text
    assert "权重键无法识别" in resp.text


def test_weights_sum_must_be_100(client: TestClient, db_session, admin_token):
    payload = _payload("权重不足周期", weights={"self": 20, "manager": 60, "peer": 10})
    resp = client.post(
        "/api/v1/assessment-cycles",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422, resp.text
    assert "权重总和必须等于100" in resp.text


def test_nested_reviewer_weights_accepted(client: TestClient, db_session, admin_token):
    payload = _payload(
        "嵌套评分人周期",
        weights={
            "performance": {"self": 30, "manager": 70, "peer": 0},
            "ability": {"self": 20, "manager": 60, "peer": 20},
            "attitude": {"self": 10, "manager": 50, "peer": 40},
        },
    )
    resp = client.post(
        "/api/v1/assessment-cycles",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201, resp.text