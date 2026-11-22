import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date, timedelta
import json

from app.models import (
    AssessmentRecord, AssessmentCycle, Employee, Department, Position, User, PeerReviewer, ScoreDetail
)
from app.auth import get_password_hash
from app.utils.json_columns import load_json


# ---------------------------------------------------------------------------
# Additional fixtures for peer reviewer
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def peer_user(db_session: Session):
    """Create a peer reviewer user with employee."""
    dept = db_session.query(Department).filter(Department.code == "PEER").first()
    if not dept:
        dept = Department(name="协作部", code="PEER")
        db_session.add(dept)
        db_session.flush()
    pos = db_session.query(Position).filter(Position.name == "协作专员", Position.department_id == dept.id).first()
    if not pos:
        pos = Position(name="协作专员", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
    emp = db_session.query(Employee).filter(Employee.employee_no == "PEER001").first()
    if not emp:
        emp = Employee(employee_no="PEER001", name="赵协作", department_id=dept.id, position_id=pos.id)
        db_session.add(emp)
        db_session.flush()
    user = db_session.query(User).filter(User.username == "peer001").first()
    if not user:
        user = User(
            username="peer001",
            password_hash=get_password_hash("Peer001@123"),
            role="peer",
            employee_id=emp.id,
            is_first_login=False,
        )
        db_session.add(user)
        db_session.commit()
    return user


@pytest.fixture(scope="function")
def peer_token(client: TestClient, peer_user):
    """Get peer access token."""
    resp = client.post("/auth/login", json={"username": "peer001", "password": "Peer001@123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture(scope="function")
def subordinate_user(db_session: Session, manager_user):
    """Create a subordinate employee under manager_user."""
    dept = db_session.query(Department).filter(Department.code == "TECH").first()
    if not dept:
        dept = Department(name="技术部", code="TECH")
        db_session.add(dept)
        db_session.flush()
    pos = db_session.query(Position).filter(Position.name == "Java工程师", Position.department_id == dept.id).first()
    if not pos:
        pos = Position(name="Java工程师", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
    # manager_user is in the same dept but we need to link manager-subordinate
    # manager_user fixture creates mgr001 emp with id available via manager_user.employee_id
    emp = db_session.query(Employee).filter(Employee.employee_no == "SUB001").first()
    if not emp:
        emp = Employee(
            employee_no="SUB001",
            name="下属员工",
            department_id=dept.id,
            position_id=pos.id,
            manager_id=manager_user.employee_id,
        )
        db_session.add(emp)
        db_session.flush()
    user = db_session.query(User).filter(User.username == "sub001").first()
    if not user:
        user = User(
            username="sub001",
            password_hash=get_password_hash("Sub001@123"),
            role="employee",
            employee_id=emp.id,
            is_first_login=False,
        )
        db_session.add(user)
        db_session.commit()
    return user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_cycle(db_session: Session, status: str = "pending_self"):
    cycle = AssessmentCycle(
        name="测试考核周期",
        type="monthly",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        self_due_date=date.today() + timedelta(days=10),
        manager_due_date=date.today() + timedelta(days=20),
        peer_due_date=date.today() + timedelta(days=25),
        status=status,
        dimension_weights='{"performance":0.6,"ability":0.2,"attitude":0.2}',
        reviewer_weights='{"performance":{"self":0.3,"manager":0.7},"ability":{"self":0.2,"manager":0.6,"peer":0.2},"attitude":{"self":0.2,"manager":0.8}}',
        grade_rules='{"A":{"min":90,"max":100,"ratio_limit":0.2},"B":{"min":80,"max":89.9,"ratio_limit":0.5},"C":{"min":60,"max":79.9,"ratio_limit":0.25},"D":{"min":0,"max":59.9,"ratio_limit":0.05}}',
    )
    db_session.add(cycle)
    db_session.commit()
    db_session.refresh(cycle)
    return cycle


def _create_record(db_session: Session, cycle_id: int, employee_id: int, status: str = "pending_self", self_scores: str = None, manager_scores: str = None, peer_scores: str = None):
    record = AssessmentRecord(
        cycle_id=cycle_id,
        employee_id=employee_id,
        status=status,
        self_scores=self_scores,
        manager_scores=manager_scores,
        peer_scores=peer_scores,
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


# ---------------------------------------------------------------------------
# 1. Happy path: self assessment submission
# ---------------------------------------------------------------------------

class TestSelfAssessment:
    """Tests for POST /scores/self/{record_id} and GET /scores/my-assessment"""

    def test_submit_self_score_success(self, client: TestClient, employee_token, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="pending_self")

        payload = {"performance": 85, "ability": 90, "attitude": 88}
        resp = client.post(f"/scores/self/{record.id}", json=payload, headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["record_id"] == record.id
        assert data["self_scores"] == payload
        assert data["status"] == "pending_manager"

        # Verify DB state
        db_session.refresh(record)
        assert record.status == "pending_manager"
        assert load_json(record.self_scores, {}) == payload

    def test_get_my_assessment(self, client: TestClient, employee_token, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="pending_manager")

        resp = client.get("/scores/my-assessment", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        item = next(i for i in data["items"] if i["record_id"] == record.id)
        assert item["cycle_id"] == cycle.id
        assert item["cycle_name"] == "测试考核周期"
        assert item["status"] == "pending_manager"

    def test_self_score_out_of_range_high(self, client: TestClient, employee_token, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="pending_self")

        payload = {"performance": 101, "ability": 90, "attitude": 88}
        resp = client.post(f"/scores/self/{record.id}", json=payload, headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 422
        assert "performance分数需在0-100之间" in resp.json()["message"]

    def test_self_score_out_of_range_low(self, client: TestClient, employee_token, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="pending_self")

        payload = {"performance": 85, "ability": -1, "attitude": 88}
        resp = client.post(f"/scores/self/{record.id}", json=payload, headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 422
        assert "ability分数需在0-100之间" in resp.json()["message"]

    def test_self_score_wrong_status(self, client: TestClient, employee_token, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="pending_manager")

        payload = {"performance": 85, "ability": 90, "attitude": 88}
        resp = client.post(f"/scores/self/{record.id}", json=payload, headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 422
        assert "当前状态不允许提交自评" in resp.json()["message"]

    def test_self_score_unauthorized(self, client: TestClient, manager_token, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="pending_self")

        payload = {"performance": 85, "ability": 90, "attitude": 88}
        resp = client.post(f"/scores/self/{record.id}", json=payload, headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 403

    def test_self_score_not_found(self, client: TestClient, employee_token):
        payload = {"performance": 85, "ability": 90, "attitude": 88}
        resp = client.post("/scores/self/99999", json=payload, headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 404

    def test_self_score_forbidden_other_employee(self, client: TestClient, employee_token, employee_user, db_session: Session):
        # Create another employee's record
        dept = Department(name="其他部", code="OTHER")
        db_session.add(dept)
        db_session.flush()
        pos = Position(name="其他岗", department_id=dept.id)
        db_session.add(pos)
        db_session.flush()
        other_emp = Employee(employee_no="OTHER001", name="其他员工", department_id=dept.id, position_id=pos.id)
        db_session.add(other_emp)
        db_session.flush()
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, other_emp.id, status="pending_self")

        payload = {"performance": 85, "ability": 90, "attitude": 88}
        resp = client.post(f"/scores/self/{record.id}", json=payload, headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403
        assert "无权操作此考核记录" in resp.json()["message"]


# ---------------------------------------------------------------------------
# 2. Happy path: manager score submission
# ---------------------------------------------------------------------------

class TestManagerScore:
    """Tests for POST /scores/manager/{record_id} and GET /scores/to-review"""

    def test_submit_manager_score_success(self, client: TestClient, manager_token, manager_user, subordinate_user, db_session: Session):
        cycle = _create_cycle(db_session)
        self_scores = json.dumps({"performance": 80, "ability": 85, "attitude": 90})
        record = _create_record(db_session, cycle.id, subordinate_user.employee_id, status="pending_manager", self_scores=self_scores)

        payload = {
            "performance": 85,
            "ability": 88,
            "attitude": 86,
            "comment": "该员工本月表现良好，业绩指标基本达成，能力有提升空间，态度积极主动。"
        }
        resp = client.post(f"/scores/manager/{record.id}", json=payload, headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["record_id"] == record.id
        assert data["manager_scores"] == {"performance": 85, "ability": 88, "attitude": 86}
        assert data["comment"] == payload["comment"]
        assert data["status"] == "pending_peer"
        assert "alerts" in data

        db_session.refresh(record)
        assert record.status == "pending_peer"
        assert load_json(record.manager_scores, {}) == {"performance": 85, "ability": 88, "attitude": 86}

    def test_get_to_review_list(self, client: TestClient, manager_token, manager_user, subordinate_user, db_session: Session):
        cycle = _create_cycle(db_session)
        self_scores = json.dumps({"performance": 80, "ability": 85, "attitude": 90})
        record = _create_record(db_session, cycle.id, subordinate_user.employee_id, status="pending_manager", self_scores=self_scores)

        resp = client.get("/scores/to-review", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        item = next(i for i in data if i["record_id"] == record.id)
        assert item["employee_name"] == "下属员工"
        assert item["status"] == "pending_manager"
        assert item["self_scores"] == json.loads(self_scores)

    def test_manager_score_missing_comment(self, client: TestClient, manager_token, manager_user, subordinate_user, db_session: Session):
        cycle = _create_cycle(db_session)
        self_scores = json.dumps({"performance": 80, "ability": 85, "attitude": 90})
        record = _create_record(db_session, cycle.id, subordinate_user.employee_id, status="pending_manager", self_scores=self_scores)

        payload = {"performance": 85, "ability": 88, "attitude": 86, "comment": "太短"}
        resp = client.post(f"/scores/manager/{record.id}", json=payload, headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 422
        assert "综合评语不少于20字" in resp.json()["message"]

    def test_manager_score_out_of_range(self, client: TestClient, manager_token, manager_user, subordinate_user, db_session: Session):
        cycle = _create_cycle(db_session)
        self_scores = json.dumps({"performance": 80, "ability": 85, "attitude": 90})
        record = _create_record(db_session, cycle.id, subordinate_user.employee_id, status="pending_manager", self_scores=self_scores)

        payload = {
            "performance": 150,
            "ability": 88,
            "attitude": 86,
            "comment": "该员工本月表现良好，业绩指标基本达成，能力有提升空间，态度积极主动。"
        }
        resp = client.post(f"/scores/manager/{record.id}", json=payload, headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 422
        assert "performance分数需在0-100之间" in resp.json()["message"]

    def test_manager_score_wrong_status(self, client: TestClient, manager_token, manager_user, subordinate_user, db_session: Session):
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, subordinate_user.employee_id, status="pending_self")

        payload = {
            "performance": 85,
            "ability": 88,
            "attitude": 86,
            "comment": "该员工本月表现良好，业绩指标基本达成，能力有提升空间，态度积极主动。"
        }
        resp = client.post(f"/scores/manager/{record.id}", json=payload, headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 422
        assert "当前状态不允许提交上级评分" in resp.json()["message"]

    def test_manager_score_forbidden_not_subordinate(self, client: TestClient, manager_token, manager_user, employee_user, db_session: Session):
        # employee_user is not a subordinate of manager_user
        cycle = _create_cycle(db_session)
        self_scores = json.dumps({"performance": 80, "ability": 85, "attitude": 90})
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="pending_manager", self_scores=self_scores)

        payload = {
            "performance": 85,
            "ability": 88,
            "attitude": 86,
            "comment": "该员工本月表现良好，业绩指标基本达成，能力有提升空间，态度积极主动。"
        }
        resp = client.post(f"/scores/manager/{record.id}", json=payload, headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 403
        assert "无权为此员工评分" in resp.json()["message"]

    def test_manager_score_not_found(self, client: TestClient, manager_token):
        payload = {
            "performance": 85,
            "ability": 88,
            "attitude": 86,
            "comment": "该员工本月表现良好，业绩指标基本达成，能力有提升空间，态度积极主动。"
        }
        resp = client.post("/scores/manager/99999", json=payload, headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 404

    def test_manager_score_alert_large_diff(self, client: TestClient, manager_token, manager_user, subordinate_user, db_session: Session):
        cycle = _create_cycle(db_session)
        self_scores = json.dumps({"performance": 50, "ability": 85, "attitude": 90})
        record = _create_record(db_session, cycle.id, subordinate_user.employee_id, status="pending_manager", self_scores=self_scores)

        payload = {
            "performance": 85,
            "ability": 88,
            "attitude": 86,
            "comment": "该员工本月表现良好，业绩指标基本达成，能力有提升空间，态度积极主动。"
        }
        resp = client.post(f"/scores/manager/{record.id}", json=payload, headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert any("performance" in alert for alert in data["alerts"])


# ---------------------------------------------------------------------------
# 3. Happy path: peer score submission
# ---------------------------------------------------------------------------

class TestPeerScore:
    """Tests for POST /scores/peer/{record_id}"""

    def test_submit_peer_score_success(self, client: TestClient, peer_token, peer_user, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        # Create peer reviewer relation
        pr = PeerReviewer(cycle_id=cycle.id, employee_id=employee_user.employee_id, reviewer_id=peer_user.employee_id)
        db_session.add(pr)
        db_session.commit()

        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="pending_peer")

        payload = {"ability": 92}
        resp = client.post(f"/scores/peer/{record.id}", json=payload, headers={"Authorization": f"Bearer {peer_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["record_id"] == record.id
        assert data["peer_scores"] == {"ability": 92}

        db_session.refresh(pr)
        assert pr.status == "completed"

    def test_peer_score_out_of_range(self, client: TestClient, peer_token, peer_user, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        pr = PeerReviewer(cycle_id=cycle.id, employee_id=employee_user.employee_id, reviewer_id=peer_user.employee_id)
        db_session.add(pr)
        db_session.commit()

        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="pending_peer")

        payload = {"ability": 101}
        resp = client.post(f"/scores/peer/{record.id}", json=payload, headers={"Authorization": f"Bearer {peer_token}"})
        assert resp.status_code == 422
        assert "能力分数需在0-100之间" in resp.json()["message"]

    def test_peer_score_forbidden_not_assigned(self, client: TestClient, peer_token, peer_user, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        # No peer reviewer relation created
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="pending_peer")

        payload = {"ability": 92}
        resp = client.post(f"/scores/peer/{record.id}", json=payload, headers={"Authorization": f"Bearer {peer_token}"})
        assert resp.status_code == 403
        assert "您未被分配为当前员工的协作评分人" in resp.json()["message"]

    def test_peer_score_not_found(self, client: TestClient, peer_token):
        payload = {"ability": 92}
        resp = client.post("/scores/peer/99999", json=payload, headers={"Authorization": f"Bearer {peer_token}"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 4. Score calculation endpoint
# ---------------------------------------------------------------------------

class TestScoreCalculation:
    """Tests for POST /scores/calculate/{cycle_id}"""

    def test_calculate_scores_success(self, client: TestClient, admin_token, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        self_scores = json.dumps({"performance": 80, "ability": 85, "attitude": 90})
        manager_scores = json.dumps({"performance": 90, "ability": 88, "attitude": 85})
        peer_scores = json.dumps({"ability": 92})
        record = _create_record(
            db_session, cycle.id, employee_user.employee_id,
            status="pending_peer", self_scores=self_scores,
            manager_scores=manager_scores, peer_scores=peer_scores,
        )

        resp = client.post(f"/scores/calculate/{cycle.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["calculated"] == 1
        assert data["status"] == "completed"
        assert "abnormal_count" in data
        assert "pending_distribution_review_count" in data
        assert "pending_approval_count" in data

        db_session.refresh(record)
        assert record.status in ["pending_distribution_review", "pending_approval"]
        assert record.total_score is not None
        assert record.grade is not None
        assert record.weighted_performance is not None
        assert record.weighted_ability is not None
        assert record.weighted_attitude is not None

    def test_calculate_scores_unauthorized_employee(self, client: TestClient, employee_token, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        resp = client.post(f"/scores/calculate/{cycle.id}", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403

    def test_calculate_scores_unauthorized_manager(self, client: TestClient, manager_token, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        resp = client.post(f"/scores/calculate/{cycle.id}", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 403

    def test_calculate_scores_cycle_not_found(self, client: TestClient, admin_token):
        resp = client.post("/scores/calculate/99999", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404

    def test_calculate_scores_empty_records(self, client: TestClient, admin_token, db_session: Session):
        cycle = _create_cycle(db_session)
        resp = client.post(f"/scores/calculate/{cycle.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["calculated"] == 0


# ---------------------------------------------------------------------------
# 5. Score summary endpoint
# ---------------------------------------------------------------------------

class TestScoreSummary:
    """Tests for GET /scores/summary/{cycle_id}"""

    def test_get_summary_success(self, client: TestClient, admin_token, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        self_scores = json.dumps({"performance": 80, "ability": 85, "attitude": 90})
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="pending_summary", self_scores=self_scores)

        resp = client.get(f"/scores/summary/{cycle.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        item = next(i for i in data if i["record_id"] == record.id)
        assert item["employee_id"] == employee_user.employee_id
        assert item["self_scores"] == json.loads(self_scores)
        assert "status" in item

    def test_get_summary_with_department_filter(self, client: TestClient, admin_token, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        record = _create_record(
            db_session, cycle.id, employee_user.employee_id, status="pending_summary",
            self_scores='{"performance":80,"ability":70,"attitude":90}',
            manager_scores='{"performance":85,"ability":75,"attitude":95}',
        )
        # employee_user is in 技术部 (dept id from fixture), but record has no department_id set by default
        # Let's set it explicitly
        dept = db_session.query(Department).filter(Department.code == "TECH").first()
        if dept:
            record.department_id = dept.id
            db_session.commit()

        resp = client.get(f"/scores/summary/{cycle.id}?department_id={dept.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert all(i["department_id"] == dept.id for i in data)

    def test_get_summary_unauthorized_employee(self, client: TestClient, employee_token, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        resp = client.get(f"/scores/summary/{cycle.id}", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403

    def test_get_summary_cycle_not_found(self, client: TestClient, admin_token):
        resp = client.get("/scores/summary/99999", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 6. Role-based access control
# ---------------------------------------------------------------------------

class TestRoleBasedAccessControl:
    """Tests ensuring employees cannot access manager endpoints, etc."""

    def test_employee_cannot_access_manager_to_review(self, client: TestClient, employee_token):
        resp = client.get("/scores/to-review", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403

    def test_employee_cannot_access_calculate(self, client: TestClient, employee_token, db_session: Session):
        cycle = _create_cycle(db_session)
        resp = client.post(f"/scores/calculate/{cycle.id}", headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 403

    def test_manager_cannot_access_peer_endpoint(self, client: TestClient, manager_token, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="pending_peer")
        payload = {"ability": 92}
        resp = client.post(f"/scores/peer/{record.id}", json=payload, headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 403

    def test_peer_cannot_access_self_endpoint(self, client: TestClient, peer_token, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="pending_self")
        payload = {"performance": 85, "ability": 90, "attitude": 88}
        resp = client.post(f"/scores/self/{record.id}", json=payload, headers={"Authorization": f"Bearer {peer_token}"})
        assert resp.status_code == 403

    def test_hr_can_access_calculate(self, client: TestClient, hr_token, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        self_scores = json.dumps({"performance": 80, "ability": 85, "attitude": 90})
        manager_scores = json.dumps({"performance": 90, "ability": 88, "attitude": 85})
        peer_scores = json.dumps({"ability": 92})
        _create_record(
            db_session, cycle.id, employee_user.employee_id,
            status="pending_peer", self_scores=self_scores,
            manager_scores=manager_scores, peer_scores=peer_scores,
        )
        resp = client.post(f"/scores/calculate/{cycle.id}", headers={"Authorization": f"Bearer {hr_token}"})
        assert resp.status_code == 200

    def test_hr_can_access_summary(self, client: TestClient, hr_token, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        _create_record(db_session, cycle.id, employee_user.employee_id, status="pending_summary")
        resp = client.get(f"/scores/summary/{cycle.id}", headers={"Authorization": f"Bearer {hr_token}"})
        assert resp.status_code == 200

    def test_manager_can_access_summary(self, client: TestClient, manager_token, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        _create_record(db_session, cycle.id, employee_user.employee_id, status="pending_summary")
        resp = client.get(f"/scores/summary/{cycle.id}", headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200

    def test_admin_can_access_all(self, client: TestClient, admin_token, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        record = _create_record(
            db_session, cycle.id, employee_user.employee_id,
            status="pending_summary",
            self_scores='{"performance":80,"ability":70,"attitude":90}',
            manager_scores='{"performance":85,"ability":75,"attitude":95}',
            peer_scores='{"performance":82,"ability":72,"attitude":92}'
        )

        resp_summary = client.get(f"/scores/summary/{cycle.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp_summary.status_code == 200

        resp_calc = client.post(f"/scores/calculate/{cycle.id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp_calc.status_code == 200


# ---------------------------------------------------------------------------
# 7. Edge cases and error handling
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Additional edge case tests."""

    def test_self_score_no_auth(self, client: TestClient, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="pending_self")
        payload = {"performance": 85, "ability": 90, "attitude": 88}
        resp = client.post(f"/scores/self/{record.id}", json=payload)
        assert resp.status_code == 401

    def test_manager_score_no_auth(self, client: TestClient, subordinate_user, db_session: Session):
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, subordinate_user.employee_id, status="pending_manager")
        payload = {
            "performance": 85,
            "ability": 88,
            "attitude": 86,
            "comment": "该员工本月表现良好，业绩指标基本达成，能力有提升空间，态度积极主动。"
        }
        resp = client.post(f"/scores/manager/{record.id}", json=payload)
        assert resp.status_code == 401

    def test_peer_score_no_auth(self, client: TestClient, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="pending_peer")
        payload = {"ability": 92}
        resp = client.post(f"/scores/peer/{record.id}", json=payload)
        assert resp.status_code == 401

    def test_calculate_no_auth(self, client: TestClient, db_session: Session):
        cycle = _create_cycle(db_session)
        resp = client.post(f"/scores/calculate/{cycle.id}")
        assert resp.status_code == 401

    def test_summary_no_auth(self, client: TestClient, db_session: Session):
        cycle = _create_cycle(db_session)
        resp = client.get(f"/scores/summary/{cycle.id}")
        assert resp.status_code == 401

    def test_my_assessment_no_auth(self, client: TestClient):
        resp = client.get("/scores/my-assessment")
        assert resp.status_code == 401

    def test_to_review_no_auth(self, client: TestClient):
        resp = client.get("/scores/to-review")
        assert resp.status_code == 401

    def test_self_score_not_started_status(self, client: TestClient, employee_token, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="not_started")
        payload = {"performance": 85, "ability": 90, "attitude": 88}
        resp = client.post(f"/scores/self/{record.id}", json=payload, headers={"Authorization": f"Bearer {employee_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending_manager"

    def test_peer_score_updates_existing_peer_scores(self, client: TestClient, peer_token, peer_user, employee_user, db_session: Session):
        cycle = _create_cycle(db_session)
        pr = PeerReviewer(cycle_id=cycle.id, employee_id=employee_user.employee_id, reviewer_id=peer_user.employee_id)
        db_session.add(pr)
        db_session.commit()

        record = _create_record(db_session, cycle.id, employee_user.employee_id, status="pending_peer", peer_scores=json.dumps({"ability": 50}))

        payload = {"ability": 92}
        resp = client.post(f"/scores/peer/{record.id}", json=payload, headers={"Authorization": f"Bearer {peer_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["peer_scores"] == {"ability": 92}

    def test_manager_score_with_kpi_scores(self, client: TestClient, manager_token, manager_user, subordinate_user, db_session: Session):
        cycle = _create_cycle(db_session)
        self_scores = json.dumps({"performance": 80, "ability": 85, "attitude": 90})
        record = _create_record(db_session, cycle.id, subordinate_user.employee_id, status="pending_manager", self_scores=self_scores)

        payload = {
            "performance": 85,
            "ability": 88,
            "attitude": 86,
            "comment": "该员工本月表现良好，业绩指标基本达成，能力有提升空间，态度积极主动。",
            "kpi_scores": [{"kpi_id": 1, "score": 90}]
        }
        resp = client.post(f"/scores/manager/{record.id}", json=payload, headers={"Authorization": f"Bearer {manager_token}"})
        assert resp.status_code == 200

    def test_to_review_empty_subordinates(self, client: TestClient, admin_token, db_session: Session):
        # admin has no subordinates in default fixture
        resp = client.get("/scores/to-review", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data == []
