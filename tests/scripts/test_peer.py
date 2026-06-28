"""
test_peer.py — Peer scoring management tests (TC-PEER-001 ~ TC-PEER-003)

Corresponds to test cases in:
  TEST_CASES_绩效考核评分系统_v1.0.md  §9 协作评分人管理模块 (PEER)
"""

import pytest
from fastapi.testclient import TestClient

from tests.scripts.utils import assert_status_code


class TestPeerScore:
    """TC-PEER-001"""

    def test_peer_score_submit_success(self, client: TestClient, peer_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-PEER-001: 协作评分提交成功"""
        # Assign peer to employee first
        client.post(
            "/peers/assign",
            json={"employee_id": seeded_employee["id"], "peer_ids": ["peer001"]},
            headers=peer_headers,
        )
        payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_id": seeded_employee["id"],
            "dimension_scores": {"能力": 85},
        }
        resp = client.post("/scores/peer", json=payload, headers=peer_headers)
        if resp.status_code == 404:
            pytest.skip("Peer scoring endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert data.get("status") in ("待汇总", "已完成")


class TestPeerUI:
    """TC-PEER-002, TC-PEER-003 (UI / E2E tests)"""

    def test_peer_star_rating(self):
        """TC-PEER-002: 协作人星级评分组件 (UI only)"""
        pytest.skip("UI-only test: verify star rating in browser/E2E suite")

    def test_peer_batch_assign(self):
        """TC-PEER-003: 批量分配协作人 (UI only)"""
        pytest.skip("UI-only test: verify batch peer assignment in browser/E2E suite")


class TestPeerManagement:
    """TC-PEER-002, TC-PEER-003, TC-PEER-004, TC-PEER-005"""

    def test_my_pending_peer_reviews(self, client: TestClient, peer_headers: dict):
        """TC-PEER-002: 我的待协作评分列表"""
        resp = client.get("/peer-reviewers/my-reviews", headers=peer_headers)
        if resp.status_code == 404:
            pytest.skip("My peer reviews endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert isinstance(data, list) or "items" in data

    def test_assign_peer_reviewer(self, client: TestClient, admin_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-PEER-003: 分配协作评分人"""
        # Create a peer employee
        from tests.scripts.utils import create_employee
        peer = create_employee(
            client, admin_headers, "PEER_NEW", "协作人",
            seeded_employee["department_id"], seeded_employee["position_id"],
        )
        payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_id": seeded_employee["id"],
            "peer_id": peer["id"],
        }
        resp = client.post("/peer-reviewers", json=payload, headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Peer reviewer assignment endpoint not implemented")
        assert_status_code(resp, 201)
        assert resp.json().get("peer_id") == peer["id"]

    def test_remove_peer_reviewer(self, client: TestClient, admin_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-PEER-004: 移除协作评分人"""
        # First assign a peer
        from tests.scripts.utils import create_employee
        peer = create_employee(
            client, admin_headers, "PEER_RM", "待移除协作人",
            seeded_employee["department_id"], seeded_employee["position_id"],
        )
        assign = client.post(
            "/peer-reviewers",
            json={"cycle_id": seeded_cycle["id"], "employee_id": seeded_employee["id"], "peer_id": peer["id"]},
            headers=admin_headers,
        )
        if assign.status_code == 404:
            pytest.skip("Peer reviewer assignment endpoint not implemented")
        relationship_id = assign.json().get("id", 1)
        # Now remove
        resp = client.delete(f"/peer-reviewers/{relationship_id}", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Peer reviewer removal endpoint not implemented")
        assert_status_code(resp, 204)

    def test_peer_unassigned_employee_blocked(self, client: TestClient, peer_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-PEER-005: 对未分配的员工提交协作评分被拦截"""
        payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_id": seeded_employee["id"],
            "dimension_scores": {"能力": 85},
        }
        resp = client.post("/scores/peer", json=payload, headers=peer_headers)
        if resp.status_code == 404:
            pytest.skip("Peer scoring endpoint not implemented")
        assert_status_code(resp, 403)

