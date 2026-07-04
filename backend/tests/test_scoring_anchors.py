import json
import re
import pytest
from fastapi.testclient import TestClient

from app.core.constants import SCORING_ANCHORS


FRONTEND_CONSTANTS_PATH = "D:/cc_project/performance_evaluation_system/frontend/src/constants/scoringAnchors.js"


class TestScoringAnchorsBackend:
    """Tests for backend scoring anchor constants."""

    def test_scoring_anchors_is_list(self):
        assert isinstance(SCORING_ANCHORS, list)

    def test_scoring_anchors_has_four_items(self):
        assert len(SCORING_ANCHORS) == 4

    def test_scoring_anchors_ranges(self):
        expected_ranges = ["90-100", "80-89", "60-79", "0-59"]
        actual_ranges = [a["range"] for a in SCORING_ANCHORS]
        assert actual_ranges == expected_ranges

    def test_scoring_anchors_labels(self):
        expected_labels = ["优秀", "良好", "合格", "待改进"]
        actual_labels = [a["label"] for a in SCORING_ANCHORS]
        assert actual_labels == expected_labels

    def test_scoring_anchors_have_descriptions(self):
        for anchor in SCORING_ANCHORS:
            assert "desc" in anchor
            assert isinstance(anchor["desc"], str)
            assert len(anchor["desc"]) > 0

    def test_scoring_anchors_no_duplicate_labels(self):
        labels = [a["label"] for a in SCORING_ANCHORS]
        assert len(labels) == len(set(labels))

    def test_scoring_anchors_descending_order(self):
        # Verify the ranges are in descending score order
        min_scores = []
        for anchor in SCORING_ANCHORS:
            parts = anchor["range"].split("-")
            min_scores.append(int(parts[0]))
        assert min_scores == sorted(min_scores, reverse=True)


class TestScoringAnchorsAPI:
    """Tests for the scoring anchors API endpoint using FastAPI TestClient."""

    def test_get_scoring_anchors_status_code(self, client: TestClient, admin_token):
        resp = client.get("/config/scoring-anchors", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200

    def test_get_scoring_anchors_response_structure(self, client: TestClient, admin_token):
        resp = client.get("/config/scoring-anchors", headers={"Authorization": f"Bearer {admin_token}"})
        data = resp.json()
        assert "anchors" in data
        assert isinstance(data["anchors"], list)
        assert len(data["anchors"]) == 4

    def test_get_scoring_anchors_data_correctness(self, client: TestClient, admin_token):
        resp = client.get("/config/scoring-anchors", headers={"Authorization": f"Bearer {admin_token}"})
        data = resp.json()
        anchors = data["anchors"]
        assert anchors[0]["range"] == "90-100"
        assert anchors[0]["label"] == "优秀"
        assert anchors[1]["range"] == "80-89"
        assert anchors[1]["label"] == "良好"
        assert anchors[2]["range"] == "60-79"
        assert anchors[2]["label"] == "合格"
        assert anchors[3]["range"] == "0-59"
        assert anchors[3]["label"] == "待改进"

    def test_get_scoring_anchors_matches_backend_constant(self, client: TestClient, admin_token):
        resp = client.get("/config/scoring-anchors", headers={"Authorization": f"Bearer {admin_token}"})
        data = resp.json()
        assert data["anchors"] == SCORING_ANCHORS

    def test_get_scoring_anchors_hr_can_access(self, client: TestClient, hr_token):
        resp = client.get("/config/scoring-anchors", headers={"Authorization": f"Bearer {hr_token}"})
        assert resp.status_code == 200
        assert "anchors" in resp.json()

    def test_get_scoring_anchors_manager_can_access(self, client: TestClient, manager_token):
        resp = client.get("/config/scoring-anchors", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        assert "anchors" in resp.json()

    def test_get_scoring_anchors_employee_can_access(self, client: TestClient, employee_token):
        resp = client.get("/config/scoring-anchors", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 200
        assert "anchors" in resp.json()

    def test_get_scoring_anchors_unauthorized_without_token(self, client: TestClient):
        resp = client.get("/config/scoring-anchors")
        assert resp.status_code == 401


class TestScoringAnchorsConsistency:
    """Tests to verify frontend and backend constants are consistent."""

    def test_frontend_file_exists(self):
        import os
        assert os.path.exists(FRONTEND_CONSTANTS_PATH), f"Frontend constants file not found: {FRONTEND_CONSTANTS_PATH}"

    def test_frontend_contains_all_ranges(self):
        with open(FRONTEND_CONSTANTS_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        for anchor in SCORING_ANCHORS:
            assert anchor["range"] in content, f"Missing range {anchor['range']} in frontend file"

    def test_frontend_contains_all_labels(self):
        with open(FRONTEND_CONSTANTS_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        for anchor in SCORING_ANCHORS:
            assert anchor["label"] in content, f"Missing label {anchor['label']} in frontend file"

    def test_frontend_contains_all_descriptions(self):
        with open(FRONTEND_CONSTANTS_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        for anchor in SCORING_ANCHORS:
            assert anchor["desc"] in content, f"Missing desc {anchor['desc']} in frontend file"

    def test_frontend_backend_structural_match(self, client: TestClient, admin_token):
        """Verify API response matches what the frontend file declares."""
        resp = client.get("/config/scoring-anchors", headers={"Authorization": f"Bearer {admin_token}"})
        api_anchors = resp.json()["anchors"]

        with open(FRONTEND_CONSTANTS_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify every API anchor is representable in the frontend file
        for anchor in api_anchors:
            assert anchor["range"] in content
            assert anchor["label"] in content
            assert anchor["desc"] in content

        # Verify count matches
        # Count occurrences of 'range:' in the JS file (should be 4)
        range_count = content.count("range:")
        assert range_count == 4, f"Expected 4 range entries in frontend file, found {range_count}"
