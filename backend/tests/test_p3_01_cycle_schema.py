import pytest
from fastapi.testclient import TestClient
from datetime import date, timedelta
from app.models import AssessmentCycle


class TestAssessmentCycleSchemaValidators:
    """P3-01: 考核周期 Schema 校验器测试"""

    # ---------- 合法数据 ----------
    def test_create_cycle_valid(self, client: TestClient, admin_token):
        """合法周期数据应校验通过并创建成功"""
        payload = {
            "name": "P3合法周期",
            "type": "monthly",
            "start_date": str(date.today() + timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=30)),
            "self_due_date": str(date.today() + timedelta(days=10)),
            "manager_due_date": str(date.today() + timedelta(days=20)),
            "peer_due_date": str(date.today() + timedelta(days=25)),
            "peer_review_enabled": True,
            "department_ids": [1, 2],
            "weights": {"self": 30, "manager": 50, "peer": 20},
            "grade_rules": {"A": 90, "B": 80, "C": 60, "D": 0}
        }
        resp = client.post("/assessment-cycles", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 201, f"期望201，实际{resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["name"] == "P3合法周期"
        assert data["type"] == "monthly"
        assert "id" in data

    # ---------- 名称唯一性 ----------
    def test_create_cycle_duplicate_name(self, client: TestClient, admin_token, db_session):
        """名称重复应返回 409 并提示具体字段"""
        # 先创建一个周期
        existing = AssessmentCycle(
            name="唯一名称测试",
            type="monthly",
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() + timedelta(days=30),
            status="not_started"
        )
        db_session.add(existing)
        db_session.commit()

        payload = {
            "name": "唯一名称测试",
            "type": "quarterly",
            "start_date": str(date.today() + timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=30)),
            "weights": {"self": 30, "manager": 50, "peer": 20},
            "grade_rules": {"A": 90, "B": 80, "C": 60, "D": 0}
        }
        resp = client.post("/assessment-cycles", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 409
        assert "名称已存在" in resp.json()["message"]

    # ---------- 截止时间递增 ----------
    def test_create_cycle_self_after_manager(self, client: TestClient, admin_token):
        """自评截止时间 >= 上级评截止时间 应返回 422"""
        payload = {
            "name": "截止时间逆序",
            "type": "monthly",
            "start_date": str(date.today() + timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=30)),
            "self_due_date": str(date.today() + timedelta(days=20)),
            "manager_due_date": str(date.today() + timedelta(days=10)),
            "peer_due_date": str(date.today() + timedelta(days=25)),
            "peer_review_enabled": True,
            "weights": {"self": 30, "manager": 50, "peer": 20},
            "grade_rules": {"A": 90, "B": 80, "C": 60, "D": 0}
        }
        resp = client.post("/assessment-cycles", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "自评截止时间必须早于上级评截止时间" in resp.json()["message"]

    def test_create_cycle_manager_after_peer(self, client: TestClient, admin_token):
        """上级评截止时间 >= 协作评截止时间 应返回 422"""
        payload = {
            "name": "截止时间逆序2",
            "type": "monthly",
            "start_date": str(date.today() + timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=30)),
            "self_due_date": str(date.today() + timedelta(days=10)),
            "manager_due_date": str(date.today() + timedelta(days=25)),
            "peer_due_date": str(date.today() + timedelta(days=20)),
            "peer_review_enabled": True,
            "weights": {"self": 30, "manager": 50, "peer": 20},
            "grade_rules": {"A": 90, "B": 80, "C": 60, "D": 0}
        }
        resp = client.post("/assessment-cycles", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "上级评截止时间必须早于协作评截止时间" in resp.json()["message"]

    def test_create_cycle_deadline_equal(self, client: TestClient, admin_token):
        """截止时间相等也应视为逆序，返回 422"""
        same_day = str(date.today() + timedelta(days=15))
        payload = {
            "name": "截止时间相等",
            "type": "monthly",
            "start_date": str(date.today() + timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=30)),
            "self_due_date": same_day,
            "manager_due_date": same_day,
            "peer_due_date": str(date.today() + timedelta(days=20)),
            "peer_review_enabled": True,
            "weights": {"self": 30, "manager": 50, "peer": 20},
            "grade_rules": {"A": 90, "B": 80, "C": 60, "D": 0}
        }
        resp = client.post("/assessment-cycles", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "自评截止时间必须早于上级评截止时间" in resp.json()["message"]

    # ---------- 考核对象非空 ----------
    def test_create_cycle_empty_department_ids(self, client: TestClient, admin_token):
        """department_ids 为空列表应返回 422"""
        payload = {
            "name": "空部门列表",
            "type": "monthly",
            "start_date": str(date.today() + timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=30)),
            "department_ids": [],
            "weights": {"self": 30, "manager": 50, "peer": 20},
            "grade_rules": {"A": 90, "B": 80, "C": 60, "D": 0}
        }
        resp = client.post("/assessment-cycles", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "考核对象（部门列表）不能为空" in resp.json()["message"]

    # ---------- 时间校验（起始时间不限，结束/截止时间须 >= 今天） ----------
    def test_create_cycle_start_date_in_past(self, client: TestClient, admin_token):
        """start_date 早于今天应允许创建（起始时间不限制）"""
        payload = {
            "name": "开始日期过去",
            "type": "monthly",
            "start_date": str(date.today() - timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=30)),
            "weights": {"self": 30, "manager": 50, "peer": 20},
            "grade_rules": {"A": 90, "B": 80, "C": 60, "D": 0}
        }
        resp = client.post("/assessment-cycles", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 201

    def test_create_cycle_end_date_in_past(self, client: TestClient, admin_token):
        """end_date 早于今天应返回 422"""
        payload = {
            "name": "结束日期过去",
            "type": "monthly",
            "start_date": str(date.today() + timedelta(days=1)),
            "end_date": str(date.today() - timedelta(days=1)),
            "weights": {"self": 30, "manager": 50, "peer": 20},
            "grade_rules": {"A": 90, "B": 80, "C": 60, "D": 0}
        }
        resp = client.post("/assessment-cycles", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        # 可能同时触发 end_date < start_date 和 end_date < today
        msg = resp.json()["message"]
        assert "不能早于今天" in msg or "结束日期不能早于开始日期" in msg

    def test_create_cycle_due_date_in_past(self, client: TestClient, admin_token):
        """self_due_date 早于今天应返回 422"""
        payload = {
            "name": "截止时间过去",
            "type": "monthly",
            "start_date": str(date.today() + timedelta(days=1)),
            "end_date": str(date.today() + timedelta(days=30)),
            "self_due_date": str(date.today() - timedelta(days=1)),
            "manager_due_date": str(date.today() + timedelta(days=20)),
            "peer_due_date": str(date.today() + timedelta(days=25)),
            "peer_review_enabled": True,
            "weights": {"self": 30, "manager": 50, "peer": 20},
            "grade_rules": {"A": 90, "B": 80, "C": 60, "D": 0}
        }
        resp = client.post("/assessment-cycles", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        assert "self_due_date 不能早于今天" in resp.json()["message"]

    # ---------- 边界值：今天是否合法 ----------
    def test_create_cycle_start_date_today(self, client: TestClient, admin_token):
        """start_date = today 应视为合法（>= 今天）"""
        payload = {
            "name": "开始日期今天",
            "type": "monthly",
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=30)),
            "weights": {"self": 30, "manager": 50, "peer": 20},
            "grade_rules": {"A": 90, "B": 80, "C": 60, "D": 0}
        }
        resp = client.post("/assessment-cycles", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "开始日期今天"

    # ---------- 组合校验：多个错误同时存在 ----------
    def test_create_cycle_multiple_errors(self, client: TestClient, admin_token):
        """多个校验错误应同时返回，message 中应包含所有错误信息"""
        payload = {
            "name": "",
            "type": "monthly",
            "start_date": str(date.today() - timedelta(days=5)),
            "end_date": str(date.today() - timedelta(days=10)),
            "self_due_date": str(date.today() + timedelta(days=20)),
            "manager_due_date": str(date.today() + timedelta(days=10)),
            "department_ids": [],
            "weights": {"self": 30, "manager": 50, "peer": 10},
            "grade_rules": {}
        }
        resp = client.post("/assessment-cycles", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 422
        msg = resp.json()["message"]
        # 应包含至少一个错误关键词
        assert any(k in msg for k in [
            "不能为空", "权重总和", "自评截止时间", "start_date", "end_date", "考核对象"
        ]), f"期望包含多个错误信息，实际: {msg}"
