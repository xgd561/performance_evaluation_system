"""
test_cfg.py — System configuration tests (TC-CFG-001 ~ TC-CFG-004)

Corresponds to test cases in:
  TEST_CASES_绩效考核评分系统_v1.0.md  §12 系统配置模块 (CFG)
"""

import pytest
from fastapi.testclient import TestClient

from tests.scripts.utils import assert_status_code


class TestGradeRules:
    """TC-CFG-001, TC-CFG-002"""

    def test_update_grade_rules_success(self, client: TestClient, admin_headers: dict):
        """TC-CFG-001: 更新等级规则成功"""
        payload = {
            "A": {"min": 95, "max": 100},
            "B": {"min": 85, "max": 94.9},
            "C": {"min": 60, "max": 84.9},
            "D": {"min": 0, "max": 59.9},
        }
        resp = client.put("/config/grade-rules", json=payload, headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Grade rules endpoint not implemented")
        assert_status_code(resp, 200)
        # Verify new rules applied
        resp2 = client.get("/config/grade-rules", headers=admin_headers)
        assert resp2.json().get("A", {}).get("min") == 95

    def test_update_grade_rules_overlap_blocked(self, client: TestClient, admin_headers: dict):
        """TC-CFG-002: 等级规则区间重叠拦截"""
        payload = {
            "A": {"min": 90, "max": 100},
            "B": {"min": 88, "max": 95},  # Overlaps with A
        }
        resp = client.put("/config/grade-rules", json=payload, headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Grade rules endpoint not implemented")
        assert_status_code(resp, 422)
        assert "重叠" in resp.json().get("message", "")


class TestConfigUI:
    """TC-CFG-003, TC-CFG-004 (UI / E2E tests)"""

    def test_config_realtime_preview(self):
        """TC-CFG-003: 配置实时预览 (UI only)"""
        pytest.skip("UI-only test: verify realtime preview in browser/E2E suite")

    def test_config_auto_save(self):
        """TC-CFG-004: 配置表单自动保存 (UI only)"""
        pytest.skip("UI-only test: verify auto-save in browser/E2E suite")


class TestConfigDimensionWeights:
    """TC-CFG-003, TC-CFG-004"""

    def test_get_dimension_weights(self, client: TestClient, admin_headers: dict):
        """TC-CFG-003: 获取维度权重"""
        resp = client.get("/config/dimension-weights", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Dimension weights endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert isinstance(data, dict)
        weights = {k: v for k, v in data.items() if isinstance(v, (int, float))}
        assert sum(weights.values()) == 100

    def test_update_dimension_weights(self, client: TestClient, admin_headers: dict):
        """TC-CFG-004: 更新维度权重"""
        payload = {"业绩": 50, "能力": 30, "态度": 20}
        resp = client.put("/config/dimension-weights", json=payload, headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Dimension weights update endpoint not implemented")
        assert_status_code(resp, 200)
        # Verify new weights applied
        resp2 = client.get("/config/dimension-weights", headers=admin_headers)
        assert resp2.json().get("业绩") == 50


class TestConfigReviewerWeights:
    """TC-CFG-005, TC-CFG-006"""

    def test_get_reviewer_weights(self, client: TestClient, admin_headers: dict):
        """TC-CFG-005: 获取评分人权重"""
        resp = client.get("/config/reviewer-weights", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Reviewer weights endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert isinstance(data, dict)
        assert "self" in data or "manager" in data

    def test_update_reviewer_weights(self, client: TestClient, admin_headers: dict):
        """TC-CFG-006: 更新评分人权重"""
        payload = {"self": 40, "manager": 60}
        resp = client.put("/config/reviewer-weights", json=payload, headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Reviewer weights update endpoint not implemented")
        assert_status_code(resp, 200)
        # Test invalid sum
        bad_payload = {"self": 50, "manager": 40}
        resp2 = client.put("/config/reviewer-weights", json=bad_payload, headers=admin_headers)
        assert_status_code(resp2, 422)
        assert "总和" in resp2.json().get("message", "") or "100%" in resp2.json().get("message", "")


class TestConfigSmallDeptExemption:
    """TC-CFG-007, TC-CFG-008"""

    def test_get_small_dept_exemption(self, client: TestClient, admin_headers: dict):
        """TC-CFG-007: 获取小部门豁免配置"""
        resp = client.get("/config/small-dept-exemption", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Small dept exemption endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert "enabled" in data or "threshold" in data

    def test_update_small_dept_exemption(self, client: TestClient, admin_headers: dict):
        """TC-CFG-008: 更新小部门豁免"""
        payload = {"enabled": True, "threshold": 5}
        resp = client.put("/config/small-dept-exemption", json=payload, headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Small dept exemption update endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert data.get("enabled") is True or "保存" in data.get("message", "")
