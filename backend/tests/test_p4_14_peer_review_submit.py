import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime

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
    """创建一条 pending 状态的 PeerReviewTask 给 peer001"""
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
            start_date="2026-07-01",
            end_date="2026-07-31",
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
        rec.peer_scores = None
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

    # 创建或重置 PeerReviewTask
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
    rec.status = "pending_peer"
    rec.peer_scores = None
    db.commit()

    # 清理通知
    db.query(Notification).filter(Notification.type == "peer_completed").delete()
    db.commit()


def test_submit_peer_review_success(peer_token, peer_review_task, db: Session):
    """peer 成功提交协作评分"""
    task = peer_review_task["task"]
    payload = {
        "ability": 88,
        "comment": "该员工工作能力较强，技术方案设计合理，团队协作积极，沟通顺畅。",
    }
    resp = client.post(
        f"/api/v1/scores/peer/review-tasks/{task.id}/submit",
        json=payload,
        headers={"Authorization": f"Bearer {peer_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["task_id"] == task.id
    assert data["ability"] == 88
    assert data["status"] == "completed"

    db.refresh(task)
    assert task.status == "completed"
    assert task.ability_score == 88
    assert task.comment == payload["comment"]


def test_submit_peer_review_404(peer_token):
    """任务不存在返回 404"""
    payload = {
        "ability": 88,
        "comment": "该员工工作能力较强，技术方案设计合理，团队协作积极，沟通顺畅。",
    }
    resp = client.post(
        "/api/v1/scores/peer/review-tasks/999999/submit",
        json=payload,
        headers={"Authorization": f"Bearer {peer_token}"},
    )
    assert resp.status_code == 404
    assert "协作评分任务不存在" in resp.json()["message"]


def test_submit_peer_review_403_wrong_reviewer(mgr_token, peer_review_task):
    """非 reviewer 不能提交"""
    task = peer_review_task["task"]
    payload = {
        "ability": 88,
        "comment": "该员工工作能力较强，技术方案设计合理，团队协作积极，沟通顺畅。",
    }
    resp = client.post(
        f"/api/v1/scores/peer/review-tasks/{task.id}/submit",
        json=payload,
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert resp.status_code == 403
    assert "权限" in resp.json()["message"]


def test_submit_peer_review_422_already_submitted(peer_token, peer_review_task, db: Session):
    """已提交的任务不能重复提交"""
    task = peer_review_task["task"]
    task.status = "completed"
    task.ability_score = 88
    task.comment = "已提交"
    db.commit()

    payload = {
        "ability": 90,
        "comment": "该员工工作能力较强，技术方案设计合理，团队协作积极，沟通顺畅。",
    }
    resp = client.post(
        f"/api/v1/scores/peer/review-tasks/{task.id}/submit",
        json=payload,
        headers={"Authorization": f"Bearer {peer_token}"},
    )
    assert resp.status_code == 422
    assert "已提交" in resp.json()["message"]

    # 恢复
    task.status = "pending"
    task.ability_score = None
    task.comment = None
    db.commit()


def test_submit_peer_review_422_invalid_ability(peer_token, peer_review_task):
    """ability 超出 0-100 范围"""
    task = peer_review_task["task"]
    for bad_score in [-1, 101]:
        payload = {
            "ability": bad_score,
            "comment": "该员工工作能力较强，技术方案设计合理，团队协作积极，沟通顺畅。",
        }
        resp = client.post(
            f"/api/v1/scores/peer/review-tasks/{task.id}/submit",
            json=payload,
            headers={"Authorization": f"Bearer {peer_token}"},
        )
        assert resp.status_code == 422, f"score={bad_score} should fail"
        assert "0-100" in resp.json()["message"]


def test_submit_peer_review_422_short_comment(peer_token, peer_review_task):
    """评语少于20字"""
    task = peer_review_task["task"]
    payload = {
        "ability": 88,
        "comment": "评语太短",
    }
    resp = client.post(
        f"/api/v1/scores/peer/review-tasks/{task.id}/submit",
        json=payload,
        headers={"Authorization": f"Bearer {peer_token}"},
    )
    assert resp.status_code == 422
    assert "不少于20字" in resp.json()["message"]


def test_submit_peer_review_422_long_comment(peer_token, peer_review_task):
    """评语超过500字"""
    task = peer_review_task["task"]
    payload = {
        "ability": 88,
        "comment": "评" * 501,
    }
    resp = client.post(
        f"/api/v1/scores/peer/review-tasks/{task.id}/submit",
        json=payload,
        headers={"Authorization": f"Bearer {peer_token}"},
    )
    assert resp.status_code == 422
    assert "不超过500字" in resp.json()["message"]


def test_submit_peer_review_all_completed(peer_token, peer_review_task, db: Session):
    """所有协作任务完成后 record 状态变为 pending_summary"""
    task = peer_review_task["task"]
    rec = peer_review_task["record"]

    # 确保只有这一个任务
    db.query(PeerReviewTask).filter(
        PeerReviewTask.record_id == rec.id,
        PeerReviewTask.id != task.id
    ).delete()
    db.commit()

    payload = {
        "ability": 88,
        "comment": "该员工工作能力较强，技术方案设计合理，团队协作积极，沟通顺畅。",
    }
    resp = client.post(
        f"/api/v1/scores/peer/review-tasks/{task.id}/submit",
        json=payload,
        headers={"Authorization": f"Bearer {peer_token}"},
    )
    assert resp.status_code == 200

    db.refresh(rec)
    assert rec.status == "pending_summary"

    # 验证通知
    notif = db.query(Notification).filter(Notification.type == "peer_completed").first()
    assert notif is not None
    assert "协作评分" in notif.title

    # 恢复
    task.status = "pending"
    task.ability_score = None
    task.comment = None
    task.submitted_at = None
    db.commit()
    rec.status = "pending_peer"
    rec.peer_scores = None
    db.commit()
    db.query(Notification).filter(Notification.type == "peer_completed").delete()
    db.commit()


def test_submit_peer_review_peer_scores_avg(peer_token, peer_review_task, db: Session):
    """多位协作人时取平均值"""
    task = peer_review_task["task"]
    rec = peer_review_task["record"]

    # 创建另一个 reviewer 的任务并已完成
    emp = peer_review_task["employee"]
    other_reviewer = db.query(Employee).filter(Employee.id != emp.id, Employee.id != task.reviewer_id).first()
    if other_reviewer:
        other_task = PeerReviewTask(
            record_id=rec.id,
            reviewer_id=other_reviewer.id,
            status="completed",
            ability_score=92,
            comment="另一位协作人的评语，长度足够通过校验。",
            submitted_at=datetime.utcnow(),
        )
        db.add(other_task)
        db.commit()

        payload = {
            "ability": 88,
            "comment": "该员工工作能力较强，技术方案设计合理，团队协作积极，沟通顺畅。",
        }
        resp = client.post(
            f"/api/v1/scores/peer/review-tasks/{task.id}/submit",
            json=payload,
            headers={"Authorization": f"Bearer {peer_token}"},
        )
        assert resp.status_code == 200

        db.refresh(rec)
        peer_scores = json.loads(rec.peer_scores) if rec.peer_scores else {}
        # 平均值 (88 + 92) / 2 = 90
        assert peer_scores.get("ability") == 90

        # 清理
        db.delete(other_task)
        db.commit()

    # 恢复
    task.status = "pending"
    task.ability_score = None
    task.comment = None
    task.submitted_at = None
    db.commit()
    rec.status = "pending_peer"
    rec.peer_scores = None
    db.commit()


def test_submit_peer_review_boundary_values(peer_token, peer_review_task, db: Session):
    """边界值 0 和 100 应被接受"""
    rec = peer_review_task["record"]
    # 确保只有这一个任务，避免状态变为 pending_summary
    db.query(PeerReviewTask).filter(
        PeerReviewTask.record_id == rec.id,
        PeerReviewTask.id != peer_review_task["task"].id
    ).delete()
    db.commit()

    for boundary in [0, 100]:
        task = db.query(PeerReviewTask).filter(PeerReviewTask.id == peer_review_task["task"].id).first()
        task.status = "pending"
        task.ability_score = None
        task.comment = None
        task.submitted_at = None
        db.commit()
        db.refresh(task)

        payload = {
            "ability": boundary,
            "comment": "该员工工作能力较强，技术方案设计合理，团队协作积极，沟通顺畅。",
        }
        resp = client.post(
            f"/api/v1/scores/peer/review-tasks/{task.id}/submit",
            json=payload,
            headers={"Authorization": f"Bearer {peer_token}"},
        )
        assert resp.status_code == 200, f"boundary={boundary} should pass"

    # final restore
    task = db.query(PeerReviewTask).filter(PeerReviewTask.id == peer_review_task["task"].id).first()
    task.status = "pending"
    task.ability_score = None
    task.comment = None
    task.submitted_at = None
    db.commit()
    rec = db.query(AssessmentRecord).filter(AssessmentRecord.id == rec.id).first()
    rec.status = "pending_peer"
    rec.peer_scores = None
    db.commit()


def test_submit_peer_review_notification_to_hr(peer_token, peer_review_task, db: Session):
    """所有协作任务完成后应发送通知给 HR"""
    task = peer_review_task["task"]
    rec = peer_review_task["record"]

    # 确保只有这一个任务
    db.query(PeerReviewTask).filter(
        PeerReviewTask.record_id == rec.id,
        PeerReviewTask.id != task.id
    ).delete()
    db.commit()

    # 清理已有的通知
    db.query(Notification).filter(Notification.type == "peer_completed").delete()
    db.commit()

    payload = {
        "ability": 88,
        "comment": "该员工工作能力较强，技术方案设计合理，团队协作积极，沟通顺畅。",
    }
    resp = client.post(
        f"/api/v1/scores/peer/review-tasks/{task.id}/submit",
        json=payload,
        headers={"Authorization": f"Bearer {peer_token}"},
    )
    assert resp.status_code == 200

    # 验证 HR 通知
    notif = db.query(Notification).filter(Notification.type == "peer_completed").first()
    assert notif is not None
    assert "协作评分" in notif.title

    # 恢复
    task.status = "pending"
    task.ability_score = None
    task.comment = None
    task.submitted_at = None
    db.commit()
    rec.status = "pending_peer"
    rec.peer_scores = None
    db.commit()
    db.query(Notification).filter(Notification.type == "peer_completed").delete()
    db.commit()


def test_submit_peer_review_record_peer_scores_updated(peer_token, peer_review_task, db: Session):
    """提交后考核记录的 peer_scores 应被更新"""
    task = peer_review_task["task"]
    rec = peer_review_task["record"]

    # 确保只有这一个任务
    db.query(PeerReviewTask).filter(
        PeerReviewTask.record_id == rec.id,
        PeerReviewTask.id != task.id
    ).delete()
    db.commit()

    payload = {
        "ability": 77,
        "comment": "该员工工作能力较强，技术方案设计合理，团队协作积极，沟通顺畅。",
    }
    resp = client.post(
        f"/api/v1/scores/peer/review-tasks/{task.id}/submit",
        json=payload,
        headers={"Authorization": f"Bearer {peer_token}"},
    )
    assert resp.status_code == 200

    db.refresh(rec)
    peer_scores = json.loads(rec.peer_scores) if rec.peer_scores else {}
    assert peer_scores.get("ability") == 77

    # 恢复
    task.status = "pending"
    task.ability_score = None
    task.comment = None
    task.submitted_at = None
    db.commit()
    rec.status = "pending_peer"
    rec.peer_scores = None
    db.commit()


def test_submit_peer_review_boundary_values(peer_token, peer_review_task, db: Session):
    """边界值 0 和 100 应被接受"""
    task = peer_review_task["task"]
    rec = peer_review_task["record"]

    # 确保只有这一个任务，避免状态变为 pending_summary
    db.query(PeerReviewTask).filter(
        PeerReviewTask.record_id == rec.id,
        PeerReviewTask.id != task.id
    ).delete()
    db.commit()

    for boundary in [0, 100]:
        db.expire_all()
        t = db.query(PeerReviewTask).filter(PeerReviewTask.id == task.id).first()
        t.status = "pending"
        t.ability_score = None
        t.comment = None
        t.submitted_at = None
        db.commit()
        # 重置考核记录状态，避免状态机二次转换失败
        r = db.query(AssessmentRecord).filter(AssessmentRecord.id == rec.id).first()
        r.status = "pending_peer"
        r.peer_scores = None
        db.commit()

        payload = {
            "ability": boundary,
            "comment": "该员工工作能力较强，技术方案设计合理，团队协作积极，沟通顺畅。",
        }
        resp = client.post(
            f"/api/v1/scores/peer/review-tasks/{t.id}/submit",
            json=payload,
            headers={"Authorization": f"Bearer {peer_token}"},
        )
        assert resp.status_code == 200, f"boundary={boundary} should pass"

    # final restore
    t = db.query(PeerReviewTask).filter(PeerReviewTask.id == task.id).first()
    t.status = "pending"
    t.ability_score = None
    t.comment = None
    t.submitted_at = None
    db.commit()
    r = db.query(AssessmentRecord).filter(AssessmentRecord.id == rec.id).first()
    r.status = "pending_peer"
    r.peer_scores = None
    db.commit()


def test_submit_peer_review_notification_to_hr(peer_token, peer_review_task, db: Session):
    """所有协作任务完成后应发送通知给 HR"""
    task = peer_review_task["task"]
    rec = peer_review_task["record"]

    # 确保只有这一个任务
    db.query(PeerReviewTask).filter(
        PeerReviewTask.record_id == rec.id,
        PeerReviewTask.id != task.id
    ).delete()
    db.commit()

    # 清理已有通知
    db.query(Notification).filter(Notification.type == "peer_completed").delete()
    db.commit()

    payload = {
        "ability": 88,
        "comment": "该员工工作能力较强，技术方案设计合理，团队协作积极，沟通顺畅。",
    }
    resp = client.post(
        f"/api/v1/scores/peer/review-tasks/{task.id}/submit",
        json=payload,
        headers={"Authorization": f"Bearer {peer_token}"},
    )
    assert resp.status_code == 200

    # 验证通知
    notif = db.query(Notification).filter(Notification.type == "peer_completed").first()
    assert notif is not None
    assert "协作评分" in notif.title

    # 恢复
    task.status = "pending"
    task.ability_score = None
    task.comment = None
    task.submitted_at = None
    db.commit()
    rec.status = "pending_peer"
    rec.peer_scores = None
    db.commit()
    db.query(Notification).filter(Notification.type == "peer_completed").delete()
    db.commit()


def test_submit_peer_review_record_peer_scores_updated(peer_token, peer_review_task, db: Session):
    """提交后 record.peer_scores 应被更新"""
    task = peer_review_task["task"]
    rec = peer_review_task["record"]

    # 确保只有这一个任务
    db.query(PeerReviewTask).filter(
        PeerReviewTask.record_id == rec.id,
        PeerReviewTask.id != task.id
    ).delete()
    db.commit()

    payload = {
        "ability": 77,
        "comment": "该员工工作能力较强，技术方案设计合理，团队协作积极，沟通顺畅。",
    }
    resp = client.post(
        f"/api/v1/scores/peer/review-tasks/{task.id}/submit",
        json=payload,
        headers={"Authorization": f"Bearer {peer_token}"},
    )
    assert resp.status_code == 200

    db.refresh(rec)
    peer_scores = json.loads(rec.peer_scores) if rec.peer_scores else {}
    assert peer_scores.get("ability") == 77

    # 恢复
    task.status = "pending"
    task.ability_score = None
    task.comment = None
    task.submitted_at = None
    db.commit()
    rec.status = "pending_peer"
    rec.peer_scores = None
    db.commit()


from datetime import datetime
