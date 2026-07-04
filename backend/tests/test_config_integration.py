import pytest
from fastapi.testclient import TestClient
from datetime import date, timedelta

from app.services import config_service
from app.models import (
    SystemConfig,
    Department,
    Position,
    Employee,
    AssessmentCycle,
    AssessmentRecord,
    ScoreDetail,
    KpiTemplate,
    OperationLog,
)


class TestConfigFullIntegrationFlow:
    """Integration tests for the full config modification → read-back → consistency flow."""

    def test_login_update_grade_rules_read_back_consistency(self, client: TestClient, admin_token):
        """登录 → 修改等级规则 → 读取 → 验证数据一致性."""
        config_service.clear_config_cache()

        new_rules = {
            "A": {"min": 95, "max": 100, "ratio_limit": 0.15},
            "B": {"min": 80, "max": 94.9, "ratio_limit": 0.55},
            "C": {"min": 60, "max": 79.9, "ratio_limit": 0.25},
            "D": {"min": 0, "max": 59.9, "ratio_limit": 0.05},
        }

        # Update
        put_resp = client.put(
            "/config/grade-rules",
            json=new_rules,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert put_resp.status_code == 200
        assert put_resp.json()["message"] == "等级规则已更新"

        # Read back
        get_resp = client.get(
            "/config/grade-rules",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert get_resp.status_code == 200
        data = get_resp.json()

        # Verify consistency
        assert data["A"]["min"] == 95
        assert data["A"]["max"] == 100
        assert data["A"]["ratio_limit"] == 0.15
        assert data["B"]["min"] == 80
        assert data["B"]["max"] == 94.9
        assert data["B"]["ratio_limit"] == 0.55
        assert data["C"]["min"] == 60
        assert data["C"]["max"] == 79.9
        assert data["C"]["ratio_limit"] == 0.25
        assert data["D"]["min"] == 0
        assert data["D"]["max"] == 59.9
        assert data["D"]["ratio_limit"] == 0.05

        # Restore default
        default_rules = {
            "A": {"min": 90, "max": 100, "ratio_limit": 0.2},
            "B": {"min": 80, "max": 89.9, "ratio_limit": 0.5},
            "C": {"min": 60, "max": 79.9, "ratio_limit": 0.25},
            "D": {"min": 0, "max": 59.9, "ratio_limit": 0.05},
        }
        client.put(
            "/config/grade-rules",
            json=default_rules,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    def test_login_update_dimension_weights_read_back_consistency(self, client: TestClient, admin_token):
        """登录 → 修改维度权重 → 读取 → 验证数据一致性."""
        config_service.clear_config_cache()

        new_weights = {"performance": 50, "ability": 30, "attitude": 20}
        put_resp = client.put(
            "/config/dimension-weights",
            json=new_weights,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert put_resp.status_code == 200
        assert put_resp.json()["message"] == "维度权重已更新"

        get_resp = client.get(
            "/config/dimension-weights",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["performance"] == 50
        assert data["ability"] == 30
        assert data["attitude"] == 20

        # Restore default
        client.put(
            "/config/dimension-weights",
            json={"performance": 60, "ability": 20, "attitude": 20},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    def test_login_update_reviewer_weights_read_back_consistency(self, client: TestClient, admin_token):
        """登录 → 修改评价人权重 → 读取 → 验证数据一致性."""
        config_service.clear_config_cache()

        new_weights = {
            "performance": {"self": 10, "manager": 80, "peer": 10},
            "ability": {"self": 20, "manager": 60, "peer": 20},
            "attitude": {"self": 10, "manager": 50, "peer": 40},
        }
        put_resp = client.put(
            "/config/reviewer-weights",
            json=new_weights,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert put_resp.status_code == 200
        assert put_resp.json()["message"] == "评分人权重已更新"

        get_resp = client.get(
            "/config/reviewer-weights",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["performance"]["self"] == 10
        assert data["performance"]["manager"] == 80
        assert data["performance"]["peer"] == 10

        # Restore default
        default_weights = {
            "performance": {"self": 30, "manager": 70, "peer": 0},
            "ability": {"self": 20, "manager": 60, "peer": 20},
            "attitude": {"self": 10, "manager": 50, "peer": 40},
        }
        client.put(
            "/config/reviewer-weights",
            json=default_weights,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    def test_login_update_small_dept_exemption_read_back_consistency(self, client: TestClient, admin_token):
        """登录 → 修改小部门豁免 → 读取 → 验证数据一致性."""
        config_service.clear_config_cache()

        new_config = {"enabled": False, "threshold": 3}
        put_resp = client.put(
            "/config/small-dept-exemption",
            json=new_config,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert put_resp.status_code == 200
        assert put_resp.json()["message"] == "小部门豁免配置已保存"

        get_resp = client.get(
            "/config/small-dept-exemption",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["enabled"] is False
        assert data["threshold"] == 3

        # Restore default
        client.put(
            "/config/small-dept-exemption",
            json={"enabled": True, "threshold": 5},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    def test_login_update_peer_review_enabled_read_back_consistency(self, client: TestClient, admin_token):
        """登录 → 修改协作评分开关 → 读取 → 验证数据一致性."""
        config_service.clear_config_cache()

        put_resp = client.put(
            "/config/peer-review-enabled",
            json={"enabled": False},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert put_resp.status_code == 200
        assert put_resp.json()["message"] == "协作评分配置已更新"

        get_resp = client.get(
            "/config/peer-review-enabled",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["enabled"] is False

        # Restore default
        client.put(
            "/config/peer-review-enabled",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    def test_config_update_generates_operation_log(self, client: TestClient, admin_token, db_session):
        """验证配置修改后会生成操作日志."""
        config_service.clear_config_cache()

        # Count existing logs for this action
        old_count = db_session.query(OperationLog).filter(
            OperationLog.action == "update_grade_rules"
        ).count()

        new_rules = {
            "A": {"min": 90, "max": 100, "ratio_limit": 0.2},
            "B": {"min": 80, "max": 89.9, "ratio_limit": 0.5},
            "C": {"min": 60, "max": 79.9, "ratio_limit": 0.25},
            "D": {"min": 0, "max": 59.9, "ratio_limit": 0.05},
        }
        put_resp = client.put(
            "/config/grade-rules",
            json=new_rules,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert put_resp.status_code == 200

        new_count = db_session.query(OperationLog).filter(
            OperationLog.action == "update_grade_rules"
        ).count()
        assert new_count == old_count + 1

        log = db_session.query(OperationLog).filter(
            OperationLog.action == "update_grade_rules"
        ).order_by(OperationLog.id.desc()).first()
        assert log is not None
        assert log.target_type == "system_config"
        # old_value is stored as JSON text containing the grade_rules snapshot
        import json
        old_value_data = json.loads(log.old_value)
        assert "grade_rules" in old_value_data
        new_value_data = json.loads(log.new_value)
        assert "grade_rules" in new_value_data

    def test_multiple_config_updates_are_isolated(self, client: TestClient, admin_token):
        """验证修改一个配置项不会影响其他配置项."""
        config_service.clear_config_cache()

        # Modify only dimension weights
        client.put(
            "/config/dimension-weights",
            json={"performance": 55, "ability": 25, "attitude": 20},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Verify grade rules are still default
        grade_resp = client.get(
            "/config/grade-rules",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert grade_resp.status_code == 200
        grade_data = grade_resp.json()
        assert grade_data["A"]["min"] == 90
        assert grade_data["B"]["min"] == 80

        # Verify reviewer weights are still default
        reviewer_resp = client.get(
            "/config/reviewer-weights",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert reviewer_resp.status_code == 200
        reviewer_data = reviewer_resp.json()
        assert reviewer_data["performance"]["self"] == 30

        # Restore
        client.put(
            "/config/dimension-weights",
            json={"performance": 60, "ability": 20, "attitude": 20},
            headers={"Authorization": f"Bearer {admin_token}"},
        )


class TestKpiTemplateLifecycleIntegration:
    """Integration tests for KPI template create → copy → delete → reference protection."""

    def test_create_list_copy_delete_full_lifecycle(self, client: TestClient, admin_token, db_session):
        """KPI 模板创建 → 列表查询 → 复制 → 删除 完整生命周期."""
        # Create prerequisite department and position
        dept = Department(name="集成测试部", code="INTEG")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="集成测试岗", department_id=dept.id)
        db_session.add(pos)
        db_session.commit()
        db_session.refresh(pos)

        # 1. Create KPI template
        create_payload = {
            "position_id": pos.id,
            "items": [
                {"name": "指标A", "weight": 60, "target_value": "100"},
                {"name": "指标B", "weight": 40, "target_value": "95%"},
            ],
        }
        create_resp = client.post(
            "/kpi-templates",
            json=create_payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert create_resp.status_code == 201
        created = create_resp.json()
        assert created["position_id"] == pos.id
        assert len(created["items"]) == 2
        template_id = created["items"][0]["id"]

        # 2. Verify in list
        list_resp = client.get(
            "/kpi-templates",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert list_resp.status_code == 200
        items = list_resp.json()
        found = next((i for i in items if i["name"] == "指标A"), None)
        assert found is not None
        assert found["position_id"] == pos.id

        # 3. Copy template
        copy_resp = client.post(
            f"/kpi-templates/{template_id}/copy",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert copy_resp.status_code == 201
        copied = copy_resp.json()
        assert copied["name"] == "指标A-副本"
        assert copied["position_id"] == pos.id
        assert copied["weight"] == 60
        assert copied["id"] != template_id
        copied_id = copied["id"]

        # 4. Verify copy in list
        list_resp2 = client.get(
            "/kpi-templates",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert list_resp2.status_code == 200
        items2 = list_resp2.json()
        found_copy = next((i for i in items2 if i["name"] == "指标A-副本"), None)
        assert found_copy is not None

        # 5. Delete original and copy
        del_resp = client.delete(
            f"/kpi-templates/{template_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert del_resp.status_code == 204

        del_resp2 = client.delete(
            f"/kpi-templates/{copied_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert del_resp2.status_code == 204

        # 6. Verify deletion
        list_resp3 = client.get(
            "/kpi-templates",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert list_resp3.status_code == 200
        items3 = list_resp3.json()
        assert not any(i["name"] == "指标A" for i in items3)
        assert not any(i["name"] == "指标A-副本" for i in items3)

    def test_delete_referenced_template_is_blocked(self, client: TestClient, admin_token, db_session):
        """引用保护：被考核记录引用的 KPI 模板无法删除."""
        # Create prerequisite data
        dept = Department(name="引用保护部", code="REFPROT")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="引用保护岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()

        tmpl = KpiTemplate(
            position_id=pos.id,
            name="被引用指标",
            weight=100,
            target_value="100",
            is_active=True,
        )
        db_session.add(tmpl)
        db_session.flush()

        cycle = AssessmentCycle(
            name="引用保护周期",
            type="monthly",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )
        db_session.add(cycle)
        db_session.flush()

        emp = Employee(
            employee_no="REFPROT001",
            name="引用员工",
            department_id=dept.id,
            position_id=pos.id,
        )
        db_session.add(emp)
        db_session.flush()

        record = AssessmentRecord(
            cycle_id=cycle.id,
            employee_id=emp.id,
            position_id=pos.id,
            department_id=dept.id,
        )
        db_session.add(record)
        db_session.flush()

        # Create ScoreDetail referencing the template
        sd = ScoreDetail(
            record_id=record.id,
            kpi_template_id=tmpl.id,
            kpi_name=tmpl.name,
            weight=tmpl.weight,
        )
        db_session.add(sd)
        db_session.commit()

        # Attempt to delete should fail
        del_resp = client.delete(
            f"/kpi-templates/{tmpl.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert del_resp.status_code == 400
        assert "已被考核记录引用" in del_resp.json()["message"]

        # Verify template still exists
        detail_resp = client.get(
            f"/kpi-templates/{tmpl.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert detail_resp.status_code == 200

    def test_copy_nonexistent_template_returns_404(self, client: TestClient, admin_token):
        """复制不存在的模板返回 404."""
        resp = client.post(
            "/kpi-templates/99999/copy",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    def test_unauthorized_user_cannot_create_template(self, client: TestClient, employee_token, db_session):
        """非 admin 用户无法创建 KPI 模板."""
        dept = Department(name="未授权部", code="UNAUTH2")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="未授权岗", department_id=dept.id)
        db_session.add(pos)
        db_session.commit()
        db_session.refresh(pos)

        payload = {
            "position_id": pos.id,
            "items": [{"name": "指标", "weight": 100, "target_value": "100"}],
        }
        resp = client.post(
            "/kpi-templates",
            json=payload,
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 403

    def test_config_and_kpi_template_are_independent(self, client: TestClient, admin_token, db_session):
        """验证配置系统和 KPI 模板系统相互独立，修改配置不影响 KPI 模板."""
        config_service.clear_config_cache()

        # Create a KPI template
        dept = Department(name="独立部", code="INDEP")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="独立岗", department_id=dept.id)
        db_session.add(pos)
        db_session.commit()
        db_session.refresh(pos)

        payload = {
            "position_id": pos.id,
            "items": [{"name": "独立指标", "weight": 100, "target_value": "100"}],
        }
        create_resp = client.post(
            "/kpi-templates",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert create_resp.status_code == 201
        template_id = create_resp.json()["items"][0]["id"]

        # Modify config (grade rules)
        new_rules = {
            "A": {"min": 95, "max": 100, "ratio_limit": 0.15},
            "B": {"min": 80, "max": 94.9, "ratio_limit": 0.55},
            "C": {"min": 60, "max": 79.9, "ratio_limit": 0.25},
            "D": {"min": 0, "max": 59.9, "ratio_limit": 0.05},
        }
        client.put(
            "/config/grade-rules",
            json=new_rules,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Verify KPI template is unaffected
        detail_resp = client.get(
            f"/kpi-templates/{template_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert detail_resp.status_code == 200
        data = detail_resp.json()
        assert data["name"] == "独立指标"

        # Cleanup
        client.delete(
            f"/kpi-templates/{template_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        client.put(
            "/config/grade-rules",
            json={
                "A": {"min": 90, "max": 100, "ratio_limit": 0.2},
                "B": {"min": 80, "max": 89.9, "ratio_limit": 0.5},
                "C": {"min": 60, "max": 79.9, "ratio_limit": 0.25},
                "D": {"min": 0, "max": 59.9, "ratio_limit": 0.05},
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
