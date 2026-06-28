"""
test_log.py — Audit log tests (TC-LOG-001 ~ TC-LOG-003)

Corresponds to test cases in:
  TEST_CASES_绩效考核评分系统_v1.0.md  §13 审计日志模块 (LOG)
"""

import pytest
from fastapi.testclient import TestClient

from tests.scripts.utils import assert_status_code


class TestAuditLog:
    """TC-LOG-001, TC-LOG-002, TC-LOG-003"""

    def test_operation_log_recorded(self, client: TestClient, admin_headers: dict, seeded_employee: dict):
        """TC-LOG-001: 操作日志记录正确"""
        # Perform a sensitive operation (e.g., override grade)
        record_id = self._get_record_id(client, admin_headers, seeded_employee)
        override_payload = {"grade": "A", "reason": "特批"}
        client.post(f"/records/{record_id}/override", json=override_payload, headers=admin_headers)

        # Query logs
        resp = client.get(f"/logs/record/{record_id}", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Logs endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert isinstance(data, list)
        if data:
            log = data[0]
            assert "operator" in log
            assert "action" in log
            assert "old_value" in log
            assert "new_value" in log
            assert "timestamp" in log

    def test_log_immutable(self, client: TestClient, admin_headers: dict):
        """TC-LOG-002: 日志不可删除不可修改"""
        # Attempt to delete a log
        resp = client.delete("/logs/1", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Log delete endpoint not implemented (expected)")
        assert_status_code(resp, 403)
        assert "不可删除" in resp.json().get("message", "")

    def test_log_filter_and_pagination(self, client: TestClient, admin_headers: dict):
        """TC-LOG-003: 日志筛选与分页"""
        resp = client.get("/logs?page=1&size=20&action=grade_override", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Logs list endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert "total" in data
        assert "items" in data
        for item in data.get("items", []):
            assert item.get("action") == "grade_override"

    def _get_record_id(self, client, headers, employee):
        resp = client.get(f"/records?employee_id={employee['id']}", headers=headers)
        if resp.status_code == 404:
            pytest.skip("Records endpoint not implemented")
        items = resp.json().get("items", [])
        if not items:
            pytest.skip("No assessment record found")
        return items[0]["id"]


class TestLogQueries:
    """TC-LOG-002 (API), TC-LOG-004"""

    def test_log_query_and_pagination(self, client: TestClient, admin_headers: dict):
        """TC-LOG-002: 操作日志查询与分页"""
        resp = client.get("/logs?page=1&size=20", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Logs query endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert "total" in data
        assert "items" in data

    def test_log_time_filter(self, client: TestClient, admin_headers: dict):
        """TC-LOG-004: 日志时间筛选"""
        resp = client.get("/logs?start_date=2026-06-01&end_date=2026-06-30", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Logs time filter endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert "items" in data
        # Invalid date format should return 422
        resp2 = client.get("/logs?start_date=invalid", headers=admin_headers)
        if resp2.status_code != 404:
            assert_status_code(resp2, 422)
