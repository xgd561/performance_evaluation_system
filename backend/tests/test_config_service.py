import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.services import config_service
from app.models import SystemConfig


class TestConfigServiceCache:
    """Direct tests for config_service caching behavior."""

    def test_get_grade_rules_returns_default(self, db_session):
        config_service.clear_config_cache()
        data = config_service.get_grade_rules(db_session)
        assert "A" in data
        assert data["A"]["min"] == 90
        assert data["A"]["ratio_limit"] == 0.2

    def test_get_dimension_weights_returns_default(self, db_session):
        config_service.clear_config_cache()
        data = config_service.get_dimension_weights(db_session)
        assert data["performance"] == 60
        assert data["ability"] == 20
        assert data["attitude"] == 20

    def test_get_reviewer_weights_returns_default(self, db_session):
        config_service.clear_config_cache()
        data = config_service.get_reviewer_weights(db_session)
        assert data["performance"]["self"] == 30
        assert data["performance"]["manager"] == 70

    def test_get_small_dept_exemption_returns_default(self, db_session):
        config_service.clear_config_cache()
        data = config_service.get_small_dept_exemption(db_session)
        assert data["enabled"] is True
        assert data["threshold"] == 5

    def test_get_peer_review_enabled_returns_default(self, db_session):
        config_service.clear_config_cache()
        data = config_service.get_peer_review_enabled(db_session)
        assert data["enabled"] is True

    def test_cache_reduces_db_queries(self, db_session):
        config_service.clear_config_cache()
        # First call should hit DB
        with patch.object(config_service, '_get_or_create_config') as mock_get:
            mock_get.return_value = SystemConfig(
                key="grade_rules",
                value=json.dumps({
                    "A": {"min": 90, "max": 100, "ratio_limit": 0.2},
                    "B": {"min": 80, "max": 89.9, "ratio_limit": 0.5},
                    "C": {"min": 60, "max": 79.9, "ratio_limit": 0.25},
                    "D": {"min": 0, "max": 59.9, "ratio_limit": 0.05},
                })
            )
            data1 = config_service.get_grade_rules(db_session)
            assert mock_get.call_count == 1
            data2 = config_service.get_grade_rules(db_session)
            # Second call should use cache, not call _get_or_create_config again
            assert mock_get.call_count == 1
            assert data1 == data2

    def test_invalidate_cache_on_update(self, db_session):
        config_service.clear_config_cache()
        # Prime cache
        old = config_service.get_grade_rules(db_session)
        assert old["A"]["min"] == 90

        # Update DB directly
        cfg = db_session.query(SystemConfig).filter(SystemConfig.key == "grade_rules").first()
        cfg.value = json.dumps({
            "A": {"min": 85, "max": 100, "ratio_limit": 0.2},
            "B": {"min": 70, "max": 84.9, "ratio_limit": 0.5},
            "C": {"min": 60, "max": 69.9, "ratio_limit": 0.25},
            "D": {"min": 0, "max": 59.9, "ratio_limit": 0.05},
        })
        db_session.commit()

        # Without invalidation, cache still returns old value
        cached = config_service.get_grade_rules(db_session)
        assert cached["A"]["min"] == 90

        # After invalidation, new value is read
        config_service.invalidate_config_cache("grade_rules")
        new = config_service.get_grade_rules(db_session)
        assert new["A"]["min"] == 85

    def test_clear_cache(self, db_session):
        config_service.clear_config_cache()
        config_service.get_grade_rules(db_session)
        assert "grade_rules" in config_service._CACHE
        config_service.clear_config_cache()
        assert "grade_rules" not in config_service._CACHE

    def test_get_dimension_weights_float_conversion(self, db_session):
        # Store as floats (0.6 style)
        config_service.clear_config_cache()
        cfg = db_session.query(SystemConfig).filter(SystemConfig.key == "dimension_weights").first()
        if not cfg:
            cfg = SystemConfig(
                key="dimension_weights",
                value=json.dumps({"performance": 0.6, "ability": 0.2, "attitude": 0.2})
            )
            db_session.add(cfg)
            db_session.commit()
        else:
            cfg.value = json.dumps({"performance": 0.6, "ability": 0.2, "attitude": 0.2})
            db_session.commit()
        config_service.invalidate_config_cache("dimension_weights")
        data = config_service.get_dimension_weights(db_session)
        assert data["performance"] == 60
        assert data["ability"] == 20
        assert data["attitude"] == 20

    def test_get_dimension_weights_int_no_conversion(self, db_session):
        # Store as ints (60 style)
        config_service.clear_config_cache()
        cfg = db_session.query(SystemConfig).filter(SystemConfig.key == "dimension_weights").first()
        if not cfg:
            cfg = SystemConfig(
                key="dimension_weights",
                value=json.dumps({"performance": 60, "ability": 20, "attitude": 20})
            )
            db_session.add(cfg)
            db_session.commit()
        else:
            cfg.value = json.dumps({"performance": 60, "ability": 20, "attitude": 20})
            db_session.commit()
        config_service.invalidate_config_cache("dimension_weights")
        data = config_service.get_dimension_weights(db_session)
        assert data["performance"] == 60
        assert data["ability"] == 20
        assert data["attitude"] == 20


class TestConfigServiceAPI:
    """Integration tests via FastAPI TestClient to verify service wiring."""

    def test_get_grade_rules_via_api(self, client: TestClient, admin_token):
        config_service.clear_config_cache()
        resp = client.get("/config/grade-rules", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["A"]["min"] == 90

    def test_update_invalidate_cache_via_api(self, client: TestClient, admin_token):
        config_service.clear_config_cache()
        # Prime cache
        get_resp = client.get("/config/grade-rules", headers={"Authorization": f"Bearer {admin_token}"})
        assert get_resp.status_code == 200
        old_data = get_resp.json()

        # Update via API
        new_payload = {
            "A": {"min": 85, "max": 100, "ratio_limit": 0.2},
            "B": {"min": 70, "max": 84.9, "ratio_limit": 0.5},
            "C": {"min": 60, "max": 69.9, "ratio_limit": 0.25},
            "D": {"min": 0, "max": 59.9, "ratio_limit": 0.05},
        }
        put_resp = client.put("/config/grade-rules", json=new_payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert put_resp.status_code == 200

        # Next GET should see new data (cache invalidated by router)
        get_resp2 = client.get("/config/grade-rules", headers={"Authorization": f"Bearer {admin_token}"})
        assert get_resp2.status_code == 200
        data = get_resp2.json()
        assert data["A"]["min"] == 85

        # Restore original
        client.put("/config/grade-rules", json=old_data, headers={"Authorization": f"Bearer {admin_token}"})

    def test_get_dimension_weights_via_api(self, client: TestClient, admin_token):
        config_service.clear_config_cache()
        resp = client.get("/config/dimension-weights", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["performance"] == 60

    def test_get_reviewer_weights_via_api(self, client: TestClient, admin_token):
        config_service.clear_config_cache()
        resp = client.get("/config/reviewer-weights", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["performance"]["self"] == 30

    def test_get_small_dept_exemption_via_api(self, client: TestClient, admin_token):
        config_service.clear_config_cache()
        resp = client.get("/config/small-dept-exemption", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "enabled" in data
        assert "threshold" in data

    def test_get_peer_review_enabled_via_api(self, client: TestClient, admin_token):
        config_service.clear_config_cache()
        resp = client.get("/config/peer-review-enabled", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["enabled"], bool)

    def test_put_dimension_weights_invalidate_cache(self, client: TestClient, admin_token):
        config_service.clear_config_cache()
        # Set a known value
        client.put(
            "/config/dimension-weights",
            json={"performance": 50, "ability": 30, "attitude": 20},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # GET should reflect new value without stale cache
        resp = client.get("/config/dimension-weights", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["performance"] == 50
        assert data["ability"] == 30
        assert data["attitude"] == 20
        # Restore default
        client.put(
            "/config/dimension-weights",
            json={"performance": 60, "ability": 20, "attitude": 20},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

    def test_put_reviewer_weights_invalidate_cache(self, client: TestClient, admin_token):
        config_service.clear_config_cache()
        new_weights = {
            "performance": {"self": 10, "manager": 80, "peer": 10},
            "ability": {"self": 20, "manager": 60, "peer": 20},
            "attitude": {"self": 10, "manager": 50, "peer": 40},
        }
        client.put(
            "/config/reviewer-weights",
            json=new_weights,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        resp = client.get("/config/reviewer-weights", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["performance"]["self"] == 10
        # Restore default
        default_weights = {
            "performance": {"self": 30, "manager": 70, "peer": 0},
            "ability": {"self": 20, "manager": 60, "peer": 20},
            "attitude": {"self": 10, "manager": 50, "peer": 40},
        }
        client.put(
            "/config/reviewer-weights",
            json=default_weights,
            headers={"Authorization": f"Bearer {admin_token}"}
        )

    def test_put_small_dept_exemption_invalidate_cache(self, client: TestClient, admin_token):
        config_service.clear_config_cache()
        client.put(
            "/config/small-dept-exemption",
            json={"enabled": False, "threshold": 3},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        resp = client.get("/config/small-dept-exemption", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is False
        assert data["threshold"] == 3
        # Restore default
        client.put(
            "/config/small-dept-exemption",
            json={"enabled": True, "threshold": 5},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

    def test_put_peer_review_enabled_invalidate_cache(self, client: TestClient, admin_token):
        config_service.clear_config_cache()
        client.put(
            "/config/peer-review-enabled",
            json={"enabled": False},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        resp = client.get("/config/peer-review-enabled", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is False
        # Restore default
        client.put(
            "/config/peer-review-enabled",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
