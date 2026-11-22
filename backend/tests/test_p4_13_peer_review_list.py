from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import (
    AssessmentRecord, AssessmentCycle, Employee, Department, Position, User,
    PeerReviewer, PeerReviewTask, Notification
)
from app.database import SessionLocal

client = TestClient(app)


def login(username: str, password: str):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def peer_token():
    return login("peer001", "Peer001@123")


@pytest.fixture(scope="module")
def mgr_token():
    return login("mgr001", "Mgr001@123")


@pytest.fixture(scope="function")
def peer_review_task(db: Session):
    """创建一条 PeerReviewTask 给 peer001"""
    peer = db.query(User).filter(User.username == "peer001").first()
    emp = db.query(User).filter(User.username == "emp001").first()
    if not peer or not emp:
        pytest.skip("缺少 peer001 或 emp001")

    peer_emp = db.query(Employee).filter(Employee.id == peer.employee_id).first()
    emp_emp = db.query(Employee).filter(Employee.id == emp.employee_id).first()
    if not peer_emp or not emp_emp:
        pytest.skip("缺少员工数据")

    cycle = db.query(AssessmentCycle).first()
    if not cycle:
        cycle = AssessmentCycle(
            name="test-cycle",
            type="annual",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            peer_review_enabled=True,
        )
        db.add(cycle)
        db.flush()

    rec = db.query(AssessmentRecord).filter(
        AssessmentRecord.employee_id == emp_emp.id,
        AssessmentRecord.cycle_id == cycle.id
    ).first()
    if not rec:
        rec = AssessmentRecord(
            cycle_id=cycle.id,
            employee_id=emp_emp.id,
            department_id=emp_emp.department_id,
            position_id=emp_emp.position_id,
            status="pending_peer",
            self_scores='{"performance": 80, "ability": 85, "attitude": 90}',
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
    else:
        rec.status = "pending_peer"
        db.commit()
        db.refresh(rec)

    # 确保 PeerReviewer 存在
    existing_reviewer = db.query(PeerReviewer).filter(
        PeerReviewer.cycle_id == cycle.id,
        PeerReviewer.employee_id == emp_emp.id,
        PeerReviewer.reviewer_id == peer_emp.id
    ).first()
    if not existing_reviewer:
        pr = PeerReviewer(
            cycle_id=cycle.id,
            employee_id=emp_emp.id,
            reviewer_id=peer_emp.id
        )
        db.add(pr)
        db.commit()

    # 创建或获取 PeerReviewTask
    task = db.query(PeerReviewTask).filter(
        PeerReviewTask.record_id == rec.id,
        PeerReviewTask.reviewer_id == peer_emp.id
    ).first()
    if not task:
        task = PeerReviewTask(
            record_id=rec.id,
            reviewer_id=peer_emp.id,
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
    else:
        task.status = "pending"
        task.ability_score = None
        task.comment = None
        task.submitted_at = None
        db.commit()
        db.refresh(task)

    yield {
        "task": task,
        "record": rec,
        "cycle": cycle,
        "employee": emp_emp,
        "reviewer": peer_emp,
    }

    # cleanup
    task.status = "pending"
    task.ability_score = None
    task.comment = None
    task.submitted_at = None
    db.commit()


def test_peer_review_list_success(peer_token, peer_review_task):
    """peer 可以查看自己的待评列表"""
    resp = client.get(
        "/api/v1/scores/peer/review-list",
        headers={"Authorization": f"Bearer {peer_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    # 验证返回字段
    item = data["items"][0]
    assert "task_id" in item
    assert "record_id" in item
    assert "employee_name" in item
    assert "status" in item


def test_peer_review_list_role_restriction(mgr_token):
    """非 peer 角色不能访问"""
    resp = client.get(
        "/api/v1/scores/peer/review-list",
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert resp.status_code == 403
    assert "权限" in resp.json()["message"]


def test_peer_review_list_empty(peer_token, db: Session):
    """没有任务时返回空列表"""
    peer = db.query(User).filter(User.username == "peer001").first()
    if peer and peer.employee_id:
        # 临时删除 peer 的所有任务
        db.query(PeerReviewTask).filter(PeerReviewTask.reviewer_id == peer.employee_id).delete()
        db.commit()

    resp = client.get(
        "/api/v1/scores/peer/review-list",
        headers={"Authorization": f"Bearer {peer_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_peer_review_list_status_filter(peer_token, peer_review_task, db: Session):
    """列表中包含 pending 和 completed 任务"""
    task = peer_review_task["task"]
    # 将任务改为 completed
    task.status = "completed"
    task.ability_score = 88
    task.comment = "测试评语，长度必须超过二十字才能通过校验。"
    task.submitted_at = datetime.utcnow()
    db.commit()

    resp = client.get(
        "/api/v1/scores/peer/review-list",
        headers={"Authorization": f"Bearer {peer_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    statuses = [item["status"] for item in data["items"]]
    assert "completed" in statuses

    # 恢复
    task.status = "pending"
    task.ability_score = None
    task.comment = None
    task.submitted_at = None
    db.commit()


def test_peer_review_list_peer_due_date(peer_token, peer_review_task):
    """列表返回中应包含 peer_due_date 字段"""
    resp = client.get(
        "/api/v1/scores/peer/review-list",
        headers={"Authorization": f"Bearer {peer_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    item = data["items"][0]
    assert "peer_due_date" in item


def test_peer_review_list_multiple_tasks(peer_token, peer_review_task, db: Session):
    """多个任务时 total 应正确统计"""
    rec = peer_review_task["record"]
    reviewer = peer_review_task["reviewer"]
    # 创建第二个任务
    task2 = PeerReviewTask(
        record_id=rec.id,
        reviewer_id=reviewer.id,
        status="pending",
    )
    db.add(task2)
    db.commit()

    resp = client.get(
        "/api/v1/scores/peer/review-list",
        headers={"Authorization": f"Bearer {peer_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2

    # cleanup
    db.delete(task2)
    db.commit()


def test_peer_review_list_contains_scores(peer_token, peer_review_task):
    """列表返回中应包含 self_scores 和 manager_scores"""
    resp = client.get(
        "/api/v1/scores/peer/review-list",
        headers={"Authorization": f"Bearer {peer_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    item = data["items"][0]
    assert "self_scores" in item
    assert "manager_scores" in item
    assert "peer_scores" in item


from datetime import datetime
