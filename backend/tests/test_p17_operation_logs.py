import pytest
from fastapi.testclient import TestClient
from app.models import OperationLog


class TestOperationLogs:
    """Tests for P1-17: GET /logs"""

    def test_list_logs_success(self, client: TestClient, admin_token, db_session):
        """Admin should be able to list operation logs"""
        # Create some logs
        log1 = OperationLog(user_id=1, action="update_cycle", target_type="assessment_cycle", target_id=1)
        log2 = OperationLog(user_id=1, action="launch_cycle", target_type="assessment_cycle", target_id=2)
        db_session.add(log1)
        db_session.add(log2)
        db_session.commit()

        resp = client.get("/logs?page=1&size=10", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "items" in data
        assert data["total"] >= 2
        assert isinstance(data["items"], list)

        # Verify item structure
        if data["items"]:
            item = data["items"][0]
            assert "id" in item
            assert "user_id" in item
            assert "action" in item
            assert "created_at" in item

    def test_list_logs_pagination(self, client: TestClient, admin_token, db_session):
        """Pagination should work correctly"""
        for i in range(5):
            log = OperationLog(user_id=1, action="test_action", target_type="test", target_id=i)
            db_session.add(log)
        db_session.commit()

        resp = client.get("/logs?page=1&size=2", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2

        resp2 = client.get("/logs?page=2&size=2", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert len(data2["items"]) == 2

    def test_list_logs_filter_by_action(self, client: TestClient, admin_token, db_session):
        """Filter by action type should work"""
        log1 = OperationLog(user_id=1, action="launch_cycle", target_type="assessment_cycle", target_id=1)
        log2 = OperationLog(user_id=1, action="archive_cycle", target_type="assessment_cycle", target_id=2)
        db_session.add(log1)
        db_session.add(log2)
        db_session.commit()

        resp = client.get("/logs?action=launch_cycle", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["action"] == "launch_cycle"

    def test_list_logs_filter_by_target_type(self, client: TestClient, admin_token, db_session):
        """Filter by target_type should work"""
        log1 = OperationLog(user_id=1, action="update", target_type="assessment_cycle", target_id=1)
        log2 = OperationLog(user_id=1, action="update", target_type="employee", target_id=2)
        db_session.add(log1)
        db_session.add(log2)
        db_session.commit()

        resp = client.get("/logs?target_type=employee", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["target_type"] == "employee"

    def test_list_logs_filter_by_date(self, client: TestClient, admin_token, db_session):
        """Filter by date range should work"""
        from datetime import datetime, timedelta
        from app.models import OperationLog

        log1 = OperationLog(user_id=1, action="past_action", target_type="test", target_id=1)
        log1.created_at = datetime.utcnow() - timedelta(days=10)
        log2 = OperationLog(user_id=1, action="recent_action", target_type="test", target_id=2)
        db_session.add(log1)
        db_session.add(log2)
        db_session.commit()

        from datetime import date
        start = date.today().isoformat()
        resp = client.get(f"/logs?start_date={start}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["action"] == "recent_action"

    def test_list_logs_hr_can_access(self, client: TestClient, hr_token, db_session):
        """HR should be able to list logs"""
        log = OperationLog(user_id=1, action="test", target_type="test", target_id=1)
        db_session.add(log)
        db_session.commit()

        resp = client.get("/logs", headers={"Authorization": f"Bearer {hr_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_list_logs_employee_forbidden(self, client: TestClient, employee_token, db_session):
        """Employee should not be able to list logs"""
        resp = client.get("/logs", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403

    def test_list_actions(self, client: TestClient, admin_token, db_session):
        """Should return distinct action types"""
        log1 = OperationLog(user_id=1, action="action_a", target_type="test", target_id=1)
        log2 = OperationLog(user_id=1, action="action_b", target_type="test", target_id=2)
        db_session.add(log1)
        db_session.add(log2)
        db_session.commit()

        resp = client.get("/logs/actions", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert "action_a" in data
        assert "action_b" in data

    def test_list_logs_empty(self, client: TestClient, admin_token):
        """Should return empty list when no logs exist"""
        resp = client.get("/logs", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []
