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


class TestConfigPeerReviewEnabled:
    """Tests for GET/PUT /config/peer-review-enabled"""

    def test_get_peer_review_enabled_success_admin(self, client: TestClient, admin_token):
        resp = client.get("/config/peer-review-enabled", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "enabled" in data
        assert isinstance(data["enabled"], bool)

    def test_get_peer_review_enabled_success_hr(self, client: TestClient, hr_token):
        resp = client.get("/config/peer-review-enabled", headers={"Authorization": f"Bearer {hr_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "enabled" in data
        assert isinstance(data["enabled"], bool)

    def test_get_peer_review_enabled_success_manager(self, client: TestClient, manager_token):
        resp = client.get("/config/peer-review-enabled", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "enabled" in data
        assert isinstance(data["enabled"], bool)

    def test_get_peer_review_enabled_unauthorized_employee(self, client: TestClient, employee_token):
        resp = client.get("/config/peer-review-enabled", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403

    def test_get_peer_review_enabled_unauthorized_peer(self, client: TestClient, peer_token):
        resp = client.get("/config/peer-review-enabled", headers={"Authorization": f"Bearer {peer_token}"})
        assert resp.status_code == 403

    def test_update_peer_review_enabled_success(self, client: TestClient, admin_token):
        # Toggle to False
        resp = client.put(
            "/config/peer-review-enabled",
            json={"enabled": False},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "协作评分配置已更新"
        assert resp.json()["enabled"] is False

        # Persistence round-trip check
        get_resp = client.get("/config/peer-review-enabled", headers={"Authorization": f"Bearer {admin_token}"})
        data = get_resp.json()
        assert data["enabled"] is False

        # Toggle back to True
        resp = client.put(
            "/config/peer-review-enabled",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True

    def test_update_peer_review_enabled_not_bool(self, client: TestClient, admin_token):
        resp = client.put(
            "/config/peer-review-enabled",
            json={"enabled": "yes"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422
        assert "enabled 必须为布尔值" in resp.json()["message"]

    def test_update_peer_review_enabled_unauthorized_hr(self, client: TestClient, hr_token):
        resp = client.put(
            "/config/peer-review-enabled",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {hr_token}"},
        )
        assert resp.status_code == 403

    def test_update_peer_review_enabled_unauthorized_manager(self, client: TestClient, manager_token):
        resp = client.put(
            "/config/peer-review-enabled",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 403

    def test_update_peer_review_enabled_unauthorized_employee(self, client: TestClient, employee_token):
        resp = client.put(
            "/config/peer-review-enabled",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 403


class TestPydanticValidators:
    """Direct unit tests for Pydantic schemas (boundary values, illegal values)"""

    def test_grade_rule_entry_ratio_limit_over_1(self):
        from app.schemas import GradeRuleEntry
        with pytest.raises(ValueError) as exc:
            GradeRuleEntry(min=0, max=100, ratio_limit=1.5)
        assert "ratio_limit" in str(exc.value).lower() or "1.5" in str(exc.value)

    def test_grade_rule_entry_min_negative(self):
        from app.schemas import GradeRuleEntry
        with pytest.raises(ValueError) as exc:
            GradeRuleEntry(min=-1, max=100, ratio_limit=0.2)
        assert "ge" in str(exc.value).lower() or "-1" in str(exc.value)

    def test_grade_rule_entry_max_over_100(self):
        from app.schemas import GradeRuleEntry
        with pytest.raises(ValueError) as exc:
            GradeRuleEntry(min=0, max=101, ratio_limit=0.2)
        assert "le" in str(exc.value).lower() or "101" in str(exc.value)

    def test_grade_rule_entry_min_ge_max(self):
        from app.schemas import GradeRuleEntry
        with pytest.raises(ValueError) as exc:
            GradeRuleEntry(min=90, max=90, ratio_limit=0.2)
        assert "min" in str(exc.value) and "max" in str(exc.value)

    def test_grade_rules_schema_missing_grade(self):
        from app.schemas import GradeRulesSchema
        with pytest.raises(ValueError) as exc:
            GradeRulesSchema.model_validate({
                "A": {"min": 90, "max": 100, "ratio_limit": 0.2},
                "B": {"min": 80, "max": 89.9, "ratio_limit": 0.5},
                "C": {"min": 60, "max": 79.9, "ratio_limit": 0.25},
            })
        assert "Field required" in str(exc.value) or "D" in str(exc.value)

    def test_grade_rules_schema_ratio_sum_exceeds_1(self):
        from app.schemas import GradeRulesSchema
        with pytest.raises(ValueError) as exc:
            GradeRulesSchema.model_validate({
                "A": {"min": 90, "max": 100, "ratio_limit": 0.5},
                "B": {"min": 80, "max": 89.9, "ratio_limit": 0.5},
                "C": {"min": 60, "max": 79.9, "ratio_limit": 0.25},
                "D": {"min": 0, "max": 59.9, "ratio_limit": 0.05},
            })
        assert "ratio_limit合计不能超过100%" in str(exc.value)

    def test_reviewer_weights_entry_sum_not_100(self):
        from app.schemas import ReviewerWeightEntry
        with pytest.raises(ValueError) as exc:
            ReviewerWeightEntry(self=30, manager=50, peer=10)
        assert "权重总和必须等于100" in str(exc.value)

    def test_reviewer_weights_config_missing_dimension(self):
        from app.schemas import ReviewerWeightsConfig
        with pytest.raises(ValueError) as exc:
            ReviewerWeightsConfig.model_validate({
                "performance": {"self": 30, "manager": 70, "peer": 0},
                "ability": {"self": 20, "manager": 60, "peer": 20},
            })
        assert "缺少维度" in str(exc.value)

    def test_kpi_template_create_empty_items(self):
        from app.schemas import KpiTemplateCreate
        with pytest.raises(ValueError) as exc:
            KpiTemplateCreate(position_id=1, items=[])
        assert "指标列表不能为空" in str(exc.value)

    def test_kpi_template_create_duplicate_names(self):
        from app.schemas import KpiTemplateCreate, KpiItemCreate
        from decimal import Decimal
        with pytest.raises(ValueError) as exc:
            KpiTemplateCreate(position_id=1, items=[
                KpiItemCreate(name="指标A", weight=Decimal("60")),
                KpiItemCreate(name="指标A", weight=Decimal("40")),
            ])
        assert "指标名称不能重复" in str(exc.value)

    def test_kpi_template_create_weight_not_100(self):
        from app.schemas import KpiTemplateCreate, KpiItemCreate
        from decimal import Decimal
        with pytest.raises(ValueError) as exc:
            KpiTemplateCreate(position_id=1, items=[
                KpiItemCreate(name="指标A", weight=Decimal("50")),
                KpiItemCreate(name="指标B", weight=Decimal("40")),
            ])
        assert "权重总和必须等于100" in str(exc.value)

    def test_kpi_template_update_empty_items(self):
        from app.schemas import KpiTemplateUpdate
        with pytest.raises(ValueError) as exc:
            KpiTemplateUpdate(items=[])
        assert "指标列表不能为空" in str(exc.value)

    def test_kpi_template_update_weight_not_100(self):
        from app.schemas import KpiTemplateUpdate, KpiItemCreate
        from decimal import Decimal
        with pytest.raises(ValueError) as exc:
            KpiTemplateUpdate(items=[
                KpiItemCreate(name="指标A", weight=Decimal("99")),
            ])
        assert "权重总和必须等于100" in str(exc.value)


class TestConfigSmallDeptExemption:
    """Tests for GET/PUT /config/small-dept-exemption"""

    def test_get_small_dept_exemption_success(self, client: TestClient, admin_token):
        resp = client.get("/config/small-dept-exemption", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "enabled" in data
        assert isinstance(data["enabled"], bool)
        assert "threshold" in data
        assert isinstance(data["threshold"], int)

    def test_update_small_dept_exemption_success(self, client: TestClient, admin_token):
        payload = {"enabled": True, "threshold": 10}
        resp = client.put("/config/small-dept-exemption", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert resp.json()["message"] == "小部门豁免配置已保存"
        assert resp.json()["enabled"] is True
        assert resp.json()["threshold"] == 10

        # Persistence round-trip check
        get_resp = client.get("/config/small-dept-exemption", headers={"Authorization": f"Bearer {admin_token}"})
        data = get_resp.json()
        assert data["enabled"] is True
        assert data["threshold"] == 10

    def test_update_small_dept_exemption_threshold_zero(self, client: TestClient, admin_token):
        payload = {"enabled": True, "threshold": 0}
        resp = client.put("/config/small-dept-exemption", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "threshold 必须在 1-50 之间" in resp.json()["message"]

    def test_update_small_dept_exemption_threshold_negative(self, client: TestClient, admin_token):
        payload = {"enabled": True, "threshold": -1}
        resp = client.put("/config/small-dept-exemption", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "threshold 必须在 1-50 之间" in resp.json()["message"]

    def test_update_small_dept_exemption_threshold_over_50(self, client: TestClient, admin_token):
        payload = {"enabled": True, "threshold": 51}
        resp = client.put("/config/small-dept-exemption", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "threshold 必须在 1-50 之间" in resp.json()["message"]

    def test_update_small_dept_exemption_threshold_not_int(self, client: TestClient, admin_token):
        payload = {"enabled": True, "threshold": 5.5}
        resp = client.put("/config/small-dept-exemption", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "threshold 必须为整数" in resp.json()["message"]

    def test_update_small_dept_exemption_threshold_bool(self, client: TestClient, admin_token):
        payload = {"enabled": True, "threshold": True}
        resp = client.put("/config/small-dept-exemption", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "threshold 必须为整数" in resp.json()["message"]

    def test_update_small_dept_exemption_enabled_not_bool(self, client: TestClient, admin_token):
        payload = {"enabled": "yes", "threshold": 5}
        resp = client.put("/config/small-dept-exemption", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "enabled 必须为布尔值" in resp.json()["message"]

    def test_small_dept_exemption_unauthorized(self, client: TestClient, employee_token):
        resp = client.get("/config/small-dept-exemption", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403

    def test_update_small_dept_exemption_unauthorized(self, client: TestClient, hr_token):
        resp = client.put(
            "/config/small-dept-exemption",
            json={"enabled": True, "threshold": 5},
            headers={"Authorization": f"Bearer {hr_token}"},
        )
        assert resp.status_code == 403
