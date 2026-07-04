import pytest
from fastapi.testclient import TestClient


class TestConfigGradeRules:
    """Tests for GET/PUT /config/grade-rules"""

    def test_get_grade_rules_success(self, client: TestClient, admin_token):
        resp = client.get("/config/grade-rules", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "A" in data
        assert "B" in data
        assert "C" in data
        assert "D" in data

    def test_get_grade_rules_unauthorized(self, client: TestClient, employee_token):
        resp = client.get("/config/grade-rules", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403

    def test_update_grade_rules_success(self, client: TestClient, admin_token):
        payload = {
            "A": {"min": 90, "max": 100, "ratio_limit": 0.2},
            "B": {"min": 80, "max": 89.9, "ratio_limit": 0.5},
            "C": {"min": 60, "max": 79.9, "ratio_limit": 0.25},
            "D": {"min": 0, "max": 59.9, "ratio_limit": 0.05}
        }
        resp = client.put("/config/grade-rules", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert resp.json()["message"] == "等级规则已更新"

    def test_update_grade_rules_simple_format(self, client: TestClient, admin_token):
        payload = {"A": 90, "B": 80, "C": 60, "D": 0}
        resp = client.put("/config/grade-rules", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        # Persistence round-trip check
        get_resp = client.get("/config/grade-rules", headers={"Authorization": f"Bearer {admin_token}"})
        data = get_resp.json()
        assert data["A"]["min"] == 90
        assert data["D"]["min"] == 0
        assert "max" in data["A"]
        assert "ratio_limit" in data["A"]

    def test_update_grade_rules_overlapping(self, client: TestClient, admin_token):
        payload = {
            "A": {"min": 80, "max": 100, "ratio_limit": 0.2},
            "B": {"min": 80, "max": 89.9, "ratio_limit": 0.5},
            "C": {"min": 60, "max": 79.9, "ratio_limit": 0.25},
            "D": {"min": 0, "max": 59.9, "ratio_limit": 0.05}
        }
        resp = client.put("/config/grade-rules", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "区间重叠" in resp.json()["message"]

    def test_update_grade_rules_ratio_limit_exceeds_100(self, client: TestClient, admin_token):
        payload = {
            "A": {"min": 90, "max": 100, "ratio_limit": 0.5},
            "B": {"min": 80, "max": 89.9, "ratio_limit": 0.5},
            "C": {"min": 60, "max": 79.9, "ratio_limit": 0.25},
            "D": {"min": 0, "max": 59.9, "ratio_limit": 0.05}
        }
        resp = client.put("/config/grade-rules", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "ratio_limit合计不能超过100%" in resp.json()["message"]

    def test_update_grade_rules_discontinuous(self, client: TestClient, admin_token):
        payload = {
            "A": {"min": 90, "max": 100, "ratio_limit": 0.2},
            "B": {"min": 80, "max": 84.9, "ratio_limit": 0.5},
            "C": {"min": 60, "max": 79.9, "ratio_limit": 0.25},
            "D": {"min": 0, "max": 59.9, "ratio_limit": 0.05}
        }
        resp = client.put("/config/grade-rules", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "区间不连续" in resp.json()["message"]

    def test_update_grade_rules_missing_grade(self, client: TestClient, admin_token):
        payload = {
            "A": {"min": 90, "max": 100, "ratio_limit": 0.2},
            "B": {"min": 80, "max": 89.9, "ratio_limit": 0.5}
        }
        resp = client.put("/config/grade-rules", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "缺少等级规则" in resp.json()["message"]

    def test_update_grade_rules_min_ge_max(self, client: TestClient, admin_token):
        payload = {
            "A": {"min": 100, "max": 100, "ratio_limit": 0.2},
            "B": {"min": 80, "max": 89.9, "ratio_limit": 0.5},
            "C": {"min": 60, "max": 79.9, "ratio_limit": 0.25},
            "D": {"min": 0, "max": 59.9, "ratio_limit": 0.05}
        }
        resp = client.put("/config/grade-rules", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "min(" in resp.json()["message"]

    def test_update_grade_rules_unauthorized(self, client: TestClient, employee_token):
        resp = client.put("/config/grade-rules", json={"A": 90}, headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403


class TestConfigDimensionWeights:
    """Tests for GET/PUT /config/dimension-weights"""

    def test_get_dimension_weights_success(self, client: TestClient, admin_token):
        resp = client.get("/config/dimension-weights", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "performance" in data or "业绩" in data

    def test_update_dimension_weights_success(self, client: TestClient, admin_token):
        payload = {"performance": 60, "ability": 20, "attitude": 20}
        resp = client.put("/config/dimension-weights", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert resp.json()["message"] == "维度权重已更新"

    def test_update_dimension_weights_not_100(self, client: TestClient, admin_token):
        payload = {"performance": 50, "ability": 20, "attitude": 20}
        resp = client.put("/config/dimension-weights", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "权重总和必须等于100" in resp.json()["message"]

    def test_update_dimension_weights_negative(self, client: TestClient, admin_token):
        payload = {"performance": -10, "ability": 110, "attitude": 0}
        resp = client.put("/config/dimension-weights", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "权重不能为负数" in resp.json()["message"]

    def test_dimension_weights_unauthorized(self, client: TestClient, employee_token):
        resp = client.get("/config/dimension-weights", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403


class TestConfigReviewerWeights:
    """Tests for GET/PUT /config/reviewer-weights (by-dimension)"""

    DEFAULT = {
        "performance": {"self": 30, "manager": 70, "peer": 0},
        "ability": {"self": 20, "manager": 60, "peer": 20},
        "attitude": {"self": 10, "manager": 50, "peer": 40},
    }

    def test_get_reviewer_weights_success(self, client: TestClient, admin_token):
        resp = client.get("/config/reviewer-weights", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        for dim in ["performance", "ability", "attitude"]:
            assert dim in data
            assert "self" in data[dim]
            assert "manager" in data[dim]
            assert "peer" in data[dim]
            assert sum(data[dim].values()) == 100

    def test_update_reviewer_weights_success(self, client: TestClient, admin_token):
        payload = {
            "performance": {"self": 10, "manager": 80, "peer": 10},
            "ability": {"self": 20, "manager": 60, "peer": 20},
            "attitude": {"self": 10, "manager": 50, "peer": 40},
        }
        resp = client.put("/config/reviewer-weights", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert resp.json()["message"] == "评分人权重已更新"
        # Persistence round-trip check
        get_resp = client.get("/config/reviewer-weights", headers={"Authorization": f"Bearer {admin_token}"})
        data = get_resp.json()
        assert data["performance"]["self"] == 10
        assert data["performance"]["manager"] == 80
        assert data["performance"]["peer"] == 10

    def test_update_reviewer_weights_dimension_not_100(self, client: TestClient, admin_token):
        payload = {
            "performance": {"self": 30, "manager": 50, "peer": 10},  # 90
            "ability": {"self": 20, "manager": 60, "peer": 20},
            "attitude": {"self": 10, "manager": 50, "peer": 40},
        }
        resp = client.put("/config/reviewer-weights", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "权重总和必须等于100" in resp.json()["message"]

    def test_update_reviewer_weights_missing_dimension(self, client: TestClient, admin_token):
        payload = {
            "performance": {"self": 30, "manager": 70, "peer": 0},
            "ability": {"self": 20, "manager": 60, "peer": 20},
        }
        resp = client.put("/config/reviewer-weights", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "缺少维度" in resp.json()["message"]

    def test_reviewer_weights_unauthorized(self, client: TestClient, employee_token):
        resp = client.put(
            "/config/reviewer-weights",
            json={
                "performance": {"self": 100, "manager": 0, "peer": 0},
                "ability": {"self": 100, "manager": 0, "peer": 0},
                "attitude": {"self": 100, "manager": 0, "peer": 0},
            },
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 403


class TestConfigSmallDeptExemption:
    """Tests for GET/PUT /config/small-dept-exemption"""

    def test_get_small_dept_exemption_success(self, client: TestClient, admin_token):
        resp = client.get("/config/small-dept-exemption", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "enabled" in data
        assert "threshold" in data

    def test_update_small_dept_exemption_success(self, client: TestClient, admin_token):
        payload = {"enabled": True, "threshold": 10}
        resp = client.put("/config/small-dept-exemption", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert resp.json()["message"] == "小部门豁免配置已保存"

    def test_small_dept_exemption_unauthorized(self, client: TestClient, employee_token):
        resp = client.get("/config/small-dept-exemption", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403
