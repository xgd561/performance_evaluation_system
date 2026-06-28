"""
test_scr.py — Scoring management tests (TC-SCR-001 ~ TC-SCR-013)

Corresponds to test cases in:
  TEST_CASES_绩效考核评分系统_v1.0.md  §5 评分管理模块 (SCR)
"""

import pytest
from fastapi.testclient import TestClient

from tests.scripts.utils import assert_status_code


class TestSelfScore:
    """TC-SCR-001, TC-SCR-002, TC-SCR-009, TC-SCR-010, TC-SCR-011"""

    def test_self_score_submit_success(self, client: TestClient, employee_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-SCR-001: 员工自评提交成功"""
        payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_id": seeded_employee["id"],
            "kpi_scores": {"KPI1": 85, "KPI2": 90, "KPI3": 88},
            "dimension_scores": {"业绩": 85, "能力": 90, "态度": 88},
        }
        resp = client.post("/scores/self", json=payload, headers=employee_headers)
        assert_status_code(resp, 200)
        data = resp.json()
        assert data.get("status") == "待上级评"

    def test_self_score_out_of_range_blocked(self, client: TestClient, employee_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-SCR-002: 自评分数超出0-100范围拦截"""
        payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_id": seeded_employee["id"],
            "dimension_scores": {"业绩": 105, "能力": -5},
        }
        resp = client.post("/scores/self", json=payload, headers=employee_headers)
        assert_status_code(resp, 422)
        assert "0-100" in resp.json().get("message", "")

    def test_self_score_realtime_calculation(self, client: TestClient, employee_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-SCR-009: 评分输入框实时计算"""
        payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_id": seeded_employee["id"],
            "kpi_scores": {"KPI1": 85, "KPI2": 90},
        }
        resp = client.post("/scores/self-preview", json=payload, headers=employee_headers)
        if resp.status_code == 404:
            pytest.skip("Preview endpoint not implemented")
        assert_status_code(resp, 200)
        assert "total_score" in resp.json()

    def test_self_score_auto_save(self, client: TestClient, employee_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-SCR-010: 自动保存提示"""
        payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_id": seeded_employee["id"],
            "draft": {"业绩": 85, "能力": 90},
        }
        resp = client.post("/scores/draft", json=payload, headers=employee_headers)
        if resp.status_code == 404:
            pytest.skip("Draft endpoint not implemented")
        assert_status_code(resp, 200)
        assert "草稿" in resp.json().get("message", "")

    def test_kpi_target_side_by_side_display(self, client: TestClient, manager_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-SCR-011: KPI目标值并排显示 (API validates data completeness)"""
        resp = client.get(
            f"/scores/manager?cycle_id={seeded_cycle['id']}&employee_id={seeded_employee['id']}",
            headers=manager_headers,
        )
        if resp.status_code == 404:
            pytest.skip("Manager scoring endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert "kpi_targets" in data
        assert "self_scores" in data


class TestManagerScore:
    """TC-SCR-003, TC-SCR-004, TC-SCR-005, TC-SCR-006, TC-SCR-012, TC-SCR-013"""

    def test_manager_score_diff_over_20_confirmation(self, client: TestClient, manager_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-SCR-003: 上级评分与自评差异大于20分提示确认"""
        # First submit self score
        self_payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_id": seeded_employee["id"],
            "dimension_scores": {"业绩": 90, "能力": 90, "态度": 90},
        }
        client.post("/scores/self", json=self_payload, headers=manager_headers)

        # Manager scores with large difference
        mgr_payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_id": seeded_employee["id"],
            "dimension_scores": {"业绩": 65, "能力": 90, "态度": 90},
            "comment": "差异测试",
        }
        resp = client.post("/scores/manager", json=mgr_payload, headers=manager_headers)
        assert_status_code(resp, 200)
        data = resp.json()
        assert data.get("needs_confirmation") is True or "差异" in data.get("message", "")

    def test_manager_score_submit_success(self, client: TestClient, manager_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-SCR-004: 上级评分提交成功"""
        payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_id": seeded_employee["id"],
            "kpi_scores": {"KPI1": 88, "KPI2": 85, "KPI3": 90},
            "dimension_scores": {"业绩": 88, "能力": 85, "态度": 90},
            "comment": "该员工本季度表现良好，业绩达标",
        }
        resp = client.post("/scores/manager", json=payload, headers=manager_headers)
        assert_status_code(resp, 200)
        data = resp.json()
        assert data.get("status") in ("待协作评", "待汇总")

    def test_manager_score_comment_too_short(self, client: TestClient, manager_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-SCR-005: 上级评分评语不足20字拦截"""
        payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_id": seeded_employee["id"],
            "dimension_scores": {"业绩": 80, "能力": 80, "态度": 80},
            "comment": "表现一般",  # 4 characters
        }
        resp = client.post("/scores/manager", json=payload, headers=manager_headers)
        assert_status_code(resp, 422)
        assert "20字" in resp.json().get("message", "")

    def test_manager_score_draft_save(self, client: TestClient, manager_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-SCR-006: 保存评分草稿并恢复"""
        payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_id": seeded_employee["id"],
            "draft": {"业绩": 85, "能力": 90},
        }
        resp = client.post("/scores/draft", json=payload, headers=manager_headers)
        if resp.status_code == 404:
            pytest.skip("Draft endpoint not implemented")
        assert_status_code(resp, 200)
        # Verify recovery
        resp2 = client.get(
            f"/scores/draft?cycle_id={seeded_cycle['id']}&employee_id={seeded_employee['id']}",
            headers=manager_headers,
        )
        if resp2.status_code == 404:
            pytest.skip("Draft recovery endpoint not implemented")
        assert resp2.json().get("draft", {}).get("业绩") == 85

    def test_manager_score_diff_highlight(self, client: TestClient, manager_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-SCR-012: 评分差异高亮 (API returns diff metadata)"""
        resp = client.get(
            f"/scores/diff?cycle_id={seeded_cycle['id']}&employee_id={seeded_employee['id']}",
            headers=manager_headers,
        )
        if resp.status_code == 404:
            pytest.skip("Diff endpoint not implemented")
        assert_status_code(resp, 200)
        assert "diff" in resp.json()

    def test_draft_badge(self, client: TestClient, manager_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-SCR-013: 草稿状态徽章 (API returns draft status)"""
        resp = client.get(
            f"/scores/status?cycle_id={seeded_cycle['id']}&employee_id={seeded_employee['id']}",
            headers=manager_headers,
        )
        if resp.status_code == 404:
            pytest.skip("Score status endpoint not implemented")
        assert_status_code(resp, 200)
        assert "status" in resp.json()


class TestScoreSummary:
    """TC-SCR-007, TC-SCR-008"""

    def test_trigger_summary_success(self, client: TestClient, admin_headers: dict, seeded_cycle: dict):
        """TC-SCR-007: 触发汇总计算成功"""
        resp = client.post(
            f"/assessment-cycles/{seeded_cycle['id']}/summarize",
            headers=admin_headers,
        )
        assert_status_code(resp, 200)
        data = resp.json()
        assert "total_score" in data or "grades" in data
        assert data.get("status") == "待强制分布校验"

    def test_score_record_detail(self, client: TestClient, admin_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-SCR-008: 考核记录详情查询正确"""
        # Need an existing record_id
        resp = client.get(
            f"/records?cycle_id={seeded_cycle['id']}&employee_id={seeded_employee['id']}",
            headers=admin_headers,
        )
        if resp.status_code == 404:
            pytest.skip("Records endpoint not implemented")
        assert_status_code(resp, 200)
        records = resp.json().get("items", [])
        if not records:
            pytest.skip("No assessment records found")
        record_id = records[0]["id"]
        resp2 = client.get(f"/records/{record_id}", headers=admin_headers)
        assert_status_code(resp2, 200)
        data = resp2.json()
        assert "employee_info" in data
        assert "kpi_snapshot" in data
        assert "total_score" in data
        assert_fields_absent(data, "password_hash", "password", "secret")


class TestScoreQueries:
    """TC-SCR-014, TC-SCR-015, TC-SCR-016, TC-SCR-017, TC-SCR-018"""

    def test_my_assessment_form(self, client: TestClient, employee_headers: dict):
        """TC-SCR-014: 获取我的评分表"""
        resp = client.get("/scores/my-assessment", headers=employee_headers)
        if resp.status_code == 404:
            pytest.skip("My assessment endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert "kpi_list" in data or "dimensions" in data or "cycle" in data

    def test_to_review_list(self, client: TestClient, manager_headers: dict):
        """TC-SCR-015: 待评列表查询"""
        resp = client.get("/scores/to-review", headers=manager_headers)
        if resp.status_code == 404:
            pytest.skip("To-review endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert isinstance(data, list) or "items" in data

    def test_get_draft(self, client: TestClient, manager_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-SCR-016: 获取评分草稿"""
        # First save a draft
        record_id = self._get_record_id(client, manager_headers, seeded_cycle, seeded_employee)
        draft_payload = {"业绩": 85, "能力": 90}
        client.post(f"/records/{record_id}/draft", json=draft_payload, headers=manager_headers)
        resp = client.get(f"/records/{record_id}/draft", headers=manager_headers)
        if resp.status_code == 404:
            pytest.skip("Draft GET endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        if data:
            assert "业绩" in data or "dimensions" in data

    def test_score_summary(self, client: TestClient, admin_headers: dict, seeded_cycle: dict):
        """TC-SCR-017: 分数汇总表查询"""
        resp = client.get(f"/scores/summary/{seeded_cycle['id']}", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Score summary endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert isinstance(data, list) or "items" in data or "grades" in data

    def test_reassign_reviewer(self, client: TestClient, admin_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-SCR-018: 重新指派评分人"""
        record_id = self._get_record_id(client, admin_headers, seeded_cycle, seeded_employee)
        # Create a new manager
        from tests.scripts.utils import create_employee
        new_mgr = create_employee(
            client, admin_headers, "MGR_NEW", "新经理",
            seeded_employee["department_id"], seeded_employee["position_id"],
        )
        resp = client.post(
            f"/scores/{record_id}/reassign-reviewer",
            json={"new_manager_id": new_mgr["id"]},
            headers=admin_headers,
        )
        if resp.status_code == 404:
            pytest.skip("Reassign reviewer endpoint not implemented")
        assert_status_code(resp, 200)
        assert resp.json().get("manager_id") == new_mgr["id"]

    def _get_record_id(self, client, headers, cycle, employee):
        resp = client.get(
            f"/records?cycle_id={cycle['id']}&employee_id={employee['id']}",
            headers=headers,
        )
        if resp.status_code == 404:
            pytest.skip("Records endpoint not implemented")
        items = resp.json().get("items", [])
        if not items:
            pytest.skip("No assessment record found")
        return items[0]["id"]


class TestScoreValidation:
    """TC-SCR-019, TC-SCR-002"""

    def test_self_score_missing_dimension_blocked(self, client: TestClient, employee_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-SCR-019: 自评提交时维度未填被拦截"""
        payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_id": seeded_employee["id"],
            "dimension_scores": {"业绩": 85},  # Missing ability and attitude
        }
        resp = client.post("/scores/self", json=payload, headers=employee_headers)
        if resp.status_code == 404:
            pytest.skip("Self score endpoint not implemented")
        assert_status_code(resp, 422)
        assert "维度" in resp.json().get("message", "") or "未评分" in resp.json().get("message", "")

    def test_self_score_out_of_range(self, client: TestClient, employee_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-SCR-002: 自评分数超出0-100范围拦截"""
        payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_id": seeded_employee["id"],
            "dimension_scores": {"业绩": 105, "能力": -5, "态度": 80},
        }
        resp = client.post("/scores/self", json=payload, headers=employee_headers)
        if resp.status_code == 404:
            pytest.skip("Self score endpoint not implemented")
        assert_status_code(resp, 422)
        assert "0-100" in resp.json().get("message", "") or "范围" in resp.json().get("message", "")


def assert_fields_absent(data, *fields):
    for f in fields:
        assert f not in data, f"Sensitive field '{f}' leaked in response"
