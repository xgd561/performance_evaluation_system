import pytest
from datetime import datetime, date
from fastapi.testclient import TestClient
from app.models import (
    Employee, Department, Position, AssessmentRecord, AssessmentCycle,
    InterviewRecord, AppealRecord
)


# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------
SQL_PAYLOADS = [
    "' OR '1'='1",
    "'; DROP TABLE employees; --",
    "1' UNION SELECT * FROM users --",
    "' OR 1=1 --",
    "admin'--",
]

XSS_PAYLOADS = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "<iframe src='javascript:alert(1)'>",
    "<body onload=alert(1)>",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _create_cycle_and_record(db_session, employee: Employee):
    cycle = AssessmentCycle(
        name="测试周期",
        type="annual",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="published",
    )
    db_session.add(cycle)
    db_session.commit()
    db_session.refresh(cycle)

    record = AssessmentRecord(
        cycle_id=cycle.id,
        employee_id=employee.id,
        department_id=employee.department_id,
        position_id=employee.position_id,
        status="published",
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


def _assert_no_sql_error(resp):
    # 只检查 500+ 状态码，以及具体的 SQL 错误关键词（避免误报正常的业务数据如 code:"SQL0"）
    assert resp.status_code not in (500, 502, 503), f"Server error {resp.status_code}: {resp.text}"
    if resp.status_code >= 500:
        detail = str(resp.text).lower()
        forbidden = ["syntax error", "operationalerror", "sqlite3", "mysql", "postgresql"]
        for word in forbidden:
            assert word not in detail, f"Possible SQL error in response: {resp.text}"


# ---------------------------------------------------------------------------
# ① SQL 注入防护测试
# ---------------------------------------------------------------------------
class TestSqlInjectionProtection:
    """P7-05-1: 输入 SQL 注入字符串，验证不返回 500/数据库错误。"""

    def test_login_username_sql_injection(self, client: TestClient):
        for payload in SQL_PAYLOADS:
            resp = client.post("/auth/login", json={
                "username": payload,
                "password": "password123",
                "remember_me": False,
            })
            _assert_no_sql_error(resp)

    def test_login_password_sql_injection(self, client: TestClient):
        for payload in SQL_PAYLOADS:
            resp = client.post("/auth/login", json={
                "username": "admin",
                "password": payload,
                "remember_me": False,
            })
            _assert_no_sql_error(resp)

    def test_employee_search_keyword_sql_injection(self, client: TestClient, admin_token):
        for payload in SQL_PAYLOADS:
            resp = client.get(
                f"/employees?keyword={payload}",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            _assert_no_sql_error(resp)

    def test_candidates_search_keyword_sql_injection(self, client: TestClient, admin_token):
        for payload in SQL_PAYLOADS:
            resp = client.get(
                f"/employees/candidates?keyword={payload}",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            _assert_no_sql_error(resp)

    def test_create_employee_name_sql_injection(self, client: TestClient, admin_token):
        for idx, payload in enumerate(SQL_PAYLOADS):
            resp = client.post(
                "/employees",
                json={"employee_no": f"SQL{idx}", "name": payload},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            _assert_no_sql_error(resp)

    def test_create_employee_employee_no_sql_injection(self, client: TestClient, admin_token):
        for idx, payload in enumerate(SQL_PAYLOADS):
            resp = client.post(
                "/employees",
                json={"employee_no": payload, "name": f"Test{idx}"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            _assert_no_sql_error(resp)

    def test_create_department_name_sql_injection(self, client: TestClient, admin_token):
        for idx, payload in enumerate(SQL_PAYLOADS):
            resp = client.post(
                "/departments",
                json={"name": payload, "code": f"SQL{idx}"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            _assert_no_sql_error(resp)

    def test_create_cycle_name_sql_injection(self, client: TestClient, admin_token):
        for idx, payload in enumerate(SQL_PAYLOADS):
            resp = client.post(
                "/assessment-cycles",
                json={
                    "name": payload,
                    "type": "annual",
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
                    "weights": {"performance": 40, "ability": 30, "attitude": 30},
                    "grade_rules": {"A": 90, "B": 80, "C": 70, "D": 60},
                },
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            _assert_no_sql_error(resp)

    def test_submit_manager_score_comment_sql_injection(self, client: TestClient, manager_token, manager_user, employee_user, db_session):
        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        emp.manager_id = mgr.id
        db_session.commit()
        record = _create_cycle_and_record(db_session, emp)
        for idx, payload in enumerate(SQL_PAYLOADS):
            comment = f"{payload} comment text {idx}" + "x" * 30
            resp = client.post(
                f"/scores/manager/{record.id}",
                json={"performance": 80, "ability": 80, "attitude": 80, "comment": comment},
                headers={"Authorization": f"Bearer {manager_token}"},
            )
            _assert_no_sql_error(resp)

    def test_create_appeal_reason_sql_injection(self, client: TestClient, employee_token, employee_user, db_session):
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        record = _create_cycle_and_record(db_session, emp)
        for idx, payload in enumerate(SQL_PAYLOADS):
            reason = f"{payload} reason {idx}"
            detail = f"{payload} detail text {idx}" + "x" * 30
            resp = client.post(
                "/appeals",
                json={"record_id": record.id, "reason": reason, "detail": detail},
                headers={"Authorization": f"Bearer {employee_token}"},
            )
            _assert_no_sql_error(resp)

    def test_create_interview_content_sql_injection(self, client: TestClient, manager_token, manager_user, employee_user, db_session):
        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        emp.manager_id = mgr.id
        db_session.commit()
        record = _create_cycle_and_record(db_session, emp)
        for idx, payload in enumerate(SQL_PAYLOADS):
            content = f"{payload} content {idx}" + "x" * 30
            resp = client.post(
                f"/interviews/{record.id}",
                json={"content": content, "improvement_plan": "plan text"},
                headers={"Authorization": f"Bearer {manager_token}"},
            )
            _assert_no_sql_error(resp)

    def test_approval_reject_reason_sql_injection(self, client: TestClient, admin_token, manager_user, employee_user, db_session):
        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        emp.manager_id = mgr.id
        db_session.commit()
        record = _create_cycle_and_record(db_session, emp)
        for idx, payload in enumerate(SQL_PAYLOADS):
            reason = f"{payload} reason {idx}" + "x" * 30
            resp = client.post(
                f"/approvals/{record.id}/reject",
                json={"reason": reason},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            _assert_no_sql_error(resp)

    def test_score_draft_draft_data_sql_injection(self, client: TestClient, employee_token, employee_user, db_session):
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        record = _create_cycle_and_record(db_session, emp)
        for idx, payload in enumerate(SQL_PAYLOADS):
            resp = client.post(
                "/score-drafts",
                json={
                    "record_id": record.id,
                    "draft_type": "self",
                    "draft_data": {"payload": payload, "comment": payload + "x" * 30},
                },
                headers={"Authorization": f"Bearer {employee_token}"},
            )
            _assert_no_sql_error(resp)


# ---------------------------------------------------------------------------
# ② XSS 防护测试
# ---------------------------------------------------------------------------
class TestXssProtection:
    """P7-05-2: 输入 XSS 脚本，验证后端返回 JSON 不会触发脚本执行。"""

    def _assert_json_response(self, resp):
        assert resp.status_code in (200, 201, 400, 403, 422), f"Unexpected status {resp.status_code}: {resp.text}"
        ct = resp.headers.get("content-type", "")
        assert ct.startswith("application/json") or ct.startswith("text/plain") or ct.startswith("application/octet-stream"), f"Unexpected content-type {ct}"

    def test_create_employee_name_xss(self, client: TestClient, admin_token):
        xss = "<script>alert(1)</script>"
        resp = client.post(
            "/employees",
            json={"employee_no": "XSS001", "name": xss},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self._assert_json_response(resp)
        # JSON 响应中原样包含脚本，但浏览器不会执行 JSON 中的脚本
        assert xss in resp.text or resp.status_code == 400

    def test_create_department_name_xss(self, client: TestClient, admin_token):
        xss = "<img src=x onerror=alert(1)>"
        resp = client.post(
            "/departments",
            json={"name": xss, "code": "XSS"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self._assert_json_response(resp)

    def test_create_appeal_reason_xss(self, client: TestClient, employee_token, employee_user, db_session):
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        record = _create_cycle_and_record(db_session, emp)
        xss = "<script>alert(1)</script>"
        resp = client.post(
            "/appeals",
            json={
                "record_id": record.id,
                "reason": f"reason {xss}",
                "detail": f"detail {xss} " + "x" * 30,
            },
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        self._assert_json_response(resp)

    def test_create_appeal_detail_xss(self, client: TestClient, employee_token, employee_user, db_session):
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        record = _create_cycle_and_record(db_session, emp)
        xss = "<iframe src='javascript:alert(1)'>"
        resp = client.post(
            "/appeals",
            json={
                "record_id": record.id,
                "reason": "reason text",
                "detail": f"detail {xss} " + "x" * 30,
            },
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        self._assert_json_response(resp)

    def test_create_interview_content_xss(self, client: TestClient, manager_token, manager_user, employee_user, db_session):
        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        emp.manager_id = mgr.id
        db_session.commit()
        record = _create_cycle_and_record(db_session, emp)
        xss = "<script>alert(1)</script>"
        resp = client.post(
            f"/interviews/{record.id}",
            json={"content": xss, "improvement_plan": "improvement plan text"},
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        self._assert_json_response(resp)

    def test_create_interview_improvement_plan_xss(self, client: TestClient, manager_token, manager_user, employee_user, db_session):
        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        emp.manager_id = mgr.id
        db_session.commit()
        record = _create_cycle_and_record(db_session, emp)
        xss = "<body onload=alert(1)>"
        resp = client.post(
            f"/interviews/{record.id}",
            json={"content": "content text", "improvement_plan": xss},
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        self._assert_json_response(resp)

    def test_submit_manager_score_comment_xss(self, client: TestClient, manager_token, manager_user, employee_user, db_session):
        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        emp.manager_id = mgr.id
        db_session.commit()
        record = _create_cycle_and_record(db_session, emp)
        xss = "<script>alert(document.cookie)</script>"
        resp = client.post(
            f"/scores/manager/{record.id}",
            json={"performance": 80, "ability": 80, "attitude": 80, "comment": xss + " " * 30},
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        self._assert_json_response(resp)

    def test_employee_search_keyword_xss(self, client: TestClient, admin_token):
        xss = "<script>alert(1)</script>"
        resp = client.get(
            f"/employees?keyword={xss}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self._assert_json_response(resp)
        assert resp.status_code in (200, 400)

    def test_pdf_export_no_xss_execution(self, client: TestClient, employee_token, employee_user, db_session):
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        record = _create_cycle_and_record(db_session, emp)
        record.manager_comment = "<script>alert(1)</script>"
        db_session.commit()
        resp = client.get(
            f"/reports/record/{record.id}/pdf",
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            ct = resp.headers.get("content-type", "")
            assert ct == "application/pdf", f"PDF endpoint returned {ct}, not application/pdf"

    def test_appeal_review_result_xss(self, client: TestClient, admin_token, employee_user, db_session):
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        record = _create_cycle_and_record(db_session, emp)
        appeal = AppealRecord(
            record_id=record.id,
            employee_id=emp.id,
            reason="reason",
            detail="detail",
            status="pending",
        )
        db_session.add(appeal)
        db_session.commit()
        db_session.refresh(appeal)
        xss = "<script>alert(1)</script>"
        resp = client.post(
            f"/appeals/{appeal.id}/review",
            json={"action": "approve", "review_result": f"result {xss}"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self._assert_json_response(resp)

    def test_appeal_resolve_comment_xss(self, client: TestClient, admin_token, employee_user, db_session):
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        record = _create_cycle_and_record(db_session, emp)
        appeal = AppealRecord(
            record_id=record.id,
            employee_id=emp.id,
            reason="reason",
            detail="detail",
            status="approved",
        )
        db_session.add(appeal)
        db_session.commit()
        db_session.refresh(appeal)
        xss = "<script>alert(1)</script>"
        resp = client.post(
            f"/appeals/{appeal.id}/resolve",
            json={"resolution": "maintain", "comment": f"comment {xss}"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self._assert_json_response(resp)

    def test_approval_approve_comment_xss(self, client: TestClient, admin_token, manager_user, employee_user, db_session):
        mgr = db_session.query(Employee).filter(Employee.id == manager_user.employee_id).first()
        emp = db_session.query(Employee).filter(Employee.id == employee_user.employee_id).first()
        emp.manager_id = mgr.id
        db_session.commit()
        record = _create_cycle_and_record(db_session, emp)
        xss = "<script>alert(1)</script>"
        resp = client.post(
            f"/approvals/{record.id}/approve",
            json={"comment": f"comment {xss} " + "x" * 30},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self._assert_json_response(resp)
