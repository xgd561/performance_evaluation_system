"""考核周期权重的默认值回归测试。

约束：创建周期时若请求未携带 `weights`，维度权重与评分人权重都应取自
`app.services.config_service` 的全局默认值，而不是路由层硬编码。
"""
import json
from datetime import date, timedelta

from fastapi.testclient import TestClient


def test_create_cycle_uses_global_default_weights(client: TestClient, db_session, admin_token):
    today = date.today()
    payload = {
        "name": "默认权重周期",
        "type": "monthly",
        "start_date": str(today + timedelta(days=1)),
        "end_date": str(today + timedelta(days=30)),
        "grade_rules": {"A": 90, "B": 80, "C": 60, "D": 0},
    }
    resp = client.post(
        "/api/v1/assessment-cycles",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201, resp.text

    from app.models import AssessmentCycle

    cycle = db_session.query(AssessmentCycle).filter(AssessmentCycle.name == payload["name"]).first()
    dimension_weights = json.loads(cycle.dimension_weights)
    reviewer_weights = json.loads(cycle.reviewer_weights)

    # 维度权重固定取 get_dimension_weights 的全局默认值（60/20/20）
    assert dimension_weights == {"performance": 60, "ability": 20, "attitude": 20}, dimension_weights
    # 评分人权重取 get_reviewer_weights 的按维度默认值
    assert reviewer_weights["performance"] == {"self": 30, "manager": 70, "peer": 0}, reviewer_weights
    assert reviewer_weights["ability"] == {"self": 20, "manager": 60, "peer": 20}, reviewer_weights
    assert reviewer_weights["attitude"] == {"self": 10, "manager": 50, "peer": 40}, reviewer_weights