import pytest
from fastapi.testclient import TestClient
from app.models import KpiTemplate, Position, Department, AssessmentRecord, AssessmentCycle, Employee, KpiAdjustment


class TestKpiTemplateList:
    """Tests for GET /kpi-templates"""

    def test_list_templates_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="测试部", code="TEST")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        tmpl = KpiTemplate(position_id=pos.id, name="指标1", weight=50, target_value="100", is_active=True)
        db_session.add(tmpl)
        db_session.commit()

        resp = client.get("/kpi-templates", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        item = next(i for i in data if i["name"] == "指标1")
        assert item["position_id"] == pos.id
        assert item["weight"] == 50
        assert item["target_value"] == "100"
        assert item["is_active"] is True
        assert "id" in item and "created_at" in item
        assert len(data) >= 1
        item = next(i for i in data if i["name"] == "指标1")
        assert item["position_id"] == pos.id
        assert item["weight"] == 50
        assert item["target_value"] == "100"
        assert item["is_active"] is True
        assert "id" in item and "created_at" in item
        assert "scoring_method" in item
        assert "description" in item

    def test_list_templates_no_auth(self, client: TestClient):
        resp = client.get("/kpi-templates")
        assert resp.status_code == 401


class TestKpiTemplateCreate:
    """Tests for POST /kpi-templates"""

    def test_create_template_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="新建部", code="NEW")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="新建岗", department_id=dept.id)
        db_session.add(pos)
        db_session.commit()
        db_session.refresh(pos)

        payload = {
            "position_id": pos.id,
            "items": [
                {"name": "指标A", "weight": 60, "target_value": "100"},
                {"name": "指标B", "weight": 40, "target_value": "95%"}
            ]
        }
        resp = client.post("/kpi-templates", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["position_id"] == pos.id
        assert len(data["items"]) == 2
        assert data["items"][0]["name"] == "指标A"
        assert data["items"][0]["weight"] == 60
        assert data["items"][0]["target_value"] == "100"
        assert data["items"][1]["name"] == "指标B"
        assert data["items"][1]["weight"] == 40
        assert data["items"][1]["target_value"] == "95%"

    def test_create_template_weight_not_100(self, client: TestClient, admin_token, db_session):
        dept = Department(name="权重部", code="WGT")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="权重岗", department_id=dept.id)
        db_session.add(pos)
        db_session.commit()
        db_session.refresh(pos)

        payload = {
            "position_id": pos.id,
            "items": [
                {"name": "指标A", "weight": 50, "target_value": "100"}
            ]
        }
        resp = client.post("/kpi-templates", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "权重总和必须等于100" in resp.json()["message"]

    def test_create_template_unauthorized(self, client: TestClient, employee_token, db_session):
        dept = Department(name="未授权部", code="UNAUTH")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="未授权岗", department_id=dept.id)
        db_session.add(pos)
        db_session.commit()
        db_session.refresh(pos)

        payload = {"position_id": pos.id, "items": [{"name": "指标", "weight": 100}]}
        resp = client.post("/kpi-templates", json=payload, headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403


class TestKpiTemplateUpdate:
    """Tests for PUT /kpi-templates/{template_id}"""

    def test_update_template_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="更新部", code="UPD")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="更新岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        tmpl = KpiTemplate(position_id=pos.id, name="原指标", weight=100, target_value="100", is_active=True)
        db_session.add(tmpl)
        db_session.commit()
        db_session.refresh(tmpl)

        payload = {
            "items": [
                {"name": "新指标A", "weight": 70, "target_value": "100"},
                {"name": "新指标B", "weight": 30, "target_value": "95%"}
            ]
        }
        resp = client.put(f"/kpi-templates/{tmpl.id}", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["position_id"] == pos.id
        assert len(data["items"]) == 2
        assert data["items"][0]["name"] == "新指标A"
        assert data["items"][0]["weight"] == 70
        assert data["items"][1]["name"] == "新指标B"
        assert data["items"][1]["weight"] == 30

    def test_update_template_not_found(self, client: TestClient, admin_token):
        payload = {"items": [{"name": "指标", "weight": 100}]}
        resp = client.put("/kpi-templates/99999", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404

    def test_update_template_weight_not_100(self, client: TestClient, admin_token, db_session):
        dept = Department(name="权重部", code="WGT")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="权重岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        tmpl = KpiTemplate(position_id=pos.id, name="指标", weight=100, is_active=True)
        db_session.add(tmpl)
        db_session.commit()
        db_session.refresh(tmpl)

        payload = {"items": [{"name": "指标", "weight": 50}]}
        resp = client.put(f"/kpi-templates/{tmpl.id}", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422


class TestKpiTemplateDelete:
    """Tests for DELETE /kpi-templates/{template_id}"""

    def test_delete_template_success(self, client: TestClient, admin_token, db_session):
        dept = Department(name="删除部", code="DEL")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="删除岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        tmpl = KpiTemplate(position_id=pos.id, name="待删除", weight=100, is_active=True)
        db_session.add(tmpl)
        db_session.commit()
        db_session.refresh(tmpl)

        resp = client.delete(f"/kpi-templates/{tmpl.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 204

    def test_delete_template_not_found(self, client: TestClient, admin_token):
        resp = client.delete("/kpi-templates/99999", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404

    def test_delete_template_unauthorized(self, client: TestClient, employee_token):
        resp = client.delete("/kpi-templates/1", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403


class TestKpiAdjustment:
    """Tests for KPI adjustment endpoints"""

    def test_adjustment_success(self, client: TestClient, admin_token, db_session):
        # Create prerequisite data: cycle, employee, record
        from datetime import date, timedelta
        cycle = AssessmentCycle(
            name="调整周期", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30)
        )
        db_session.add(cycle)
        db_session.flush()
        dept = Department(name="调整部", code="ADJ")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="调整岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="ADJ001", name="调整员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
        record = AssessmentRecord(cycle_id=cycle.id, employee_id=emp.id, position_id=pos.id, department_id=dept.id)
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)

        payload = {"kpi_id": 1, "new_target": "200", "reason": "目标调整"}
        resp = client.post(f"/kpi-templates/{record.id}/adjust", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "待审批"
        assert "message" in data

    def test_adjustment_record_not_found(self, client: TestClient, admin_token):
        resp = client.post("/kpi-templates/99999/adjust", json={"kpi_id": 1, "new_target": "100", "reason": "测试"}, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404

    def test_list_pending_adjustments_success(self, client: TestClient, admin_token, db_session):
        from datetime import date, timedelta
        cycle = AssessmentCycle(
            name="审批周期", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30)
        )
        db_session.add(cycle)
        db_session.flush()
        dept = Department(name="审批部", code="APP")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="审批岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="APP001", name="审批员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
        record = AssessmentRecord(cycle_id=cycle.id, employee_id=emp.id, position_id=pos.id, department_id=dept.id)
        db_session.add(record)
        db_session.flush()
        adj = KpiAdjustment(record_id=record.id, original_kpi="{}", adjusted_kpi="{}", reason="测试", status="pending")
        db_session.add(adj)
        db_session.commit()

        resp = client.get("/kpi-templates/kpi-adjustments/pending", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_list_pending_adjustments_unauthorized(self, client: TestClient, employee_token):
        resp = client.get("/kpi-templates/kpi-adjustments/pending", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403

    def test_approve_adjustment_success(self, client: TestClient, admin_token, db_session):
        from datetime import date, timedelta
        cycle = AssessmentCycle(
            name="通过周期", type="monthly", start_date=date.today(), end_date=date.today() + timedelta(days=30)
        )
        db_session.add(cycle)
        db_session.flush()
        dept = Department(name="通过部", code="PAS")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="通过岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        emp = Employee(employee_no="PAS001", name="通过员工", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
        record = AssessmentRecord(cycle_id=cycle.id, employee_id=emp.id, position_id=pos.id, department_id=dept.id)
        db_session.add(record)
        db_session.flush()
        adj = KpiAdjustment(record_id=record.id, original_kpi="{}", adjusted_kpi="{}", reason="测试", status="pending")
        db_session.add(adj)
        db_session.commit()
        db_session.refresh(adj)

        resp = client.post(f"/kpi-templates/kpi-adjustments/{adj.id}/approve", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"

    def test_approve_adjustment_not_found(self, client: TestClient, admin_token):
        resp = client.post("/kpi-templates/kpi-adjustments/99999/approve", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404
