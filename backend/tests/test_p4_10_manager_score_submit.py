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
def mgr_token():
    return login("mgr001", "Mgr001@123")


@pytest.fixture(scope="module")
def employee_token():
    return login("emp001", "Emp001@123")


@pytest.fixture(scope="function")
def pending_manager_record(db: Session):
    """创建待经理评分的考核记录"""
    mgr = db.query(User).filter(User.username == "mgr001").first()
    emp = db.query(User).filter(User.username == "emp001").first()
    if not mgr or not emp:
        pytest.skip("缺少 mgr001 或 emp001")

    mgr_emp = db.query(Employee).filter(Employee.id == mgr.employee_id).first()
    emp_emp = db.query(Employee).filter(Employee.id == emp.employee_id).first()
    if not mgr_emp or not emp_emp:
        pytest.skip("缺少员工数据")

    # 设置上下级关系
    old_manager_id = emp_emp.manager_id
    emp_emp.manager_id = mgr_emp.id
    db.commit()

    # 确保有考核周期
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

    # 创建记录
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
            status="pending_manager",
            self_scores='{"performance": 80, "ability": 85, "attitude": 90}',
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
    else:
        rec.status = "pending_manager"
        rec.self_scores = '{"performance": 80, "ability": 85, "attitude": 90}'
        rec.manager_scores = None
        rec.manager_comment = None
        rec.manager_submitted = False
        db.commit()
        db.refresh(rec)

    # 创建协作评分人
    peer = db.query(User).filter(User.username == "peer001").first()
    if peer:
        peer_emp = db.query(Employee).filter(Employee.id == peer.employee_id).first()
        if peer_emp:
            existing = db.query(PeerReviewer).filter(
                PeerReviewer.cycle_id == cycle.id,
                PeerReviewer.employee_id == emp_emp.id,
                PeerReviewer.reviewer_id == peer_emp.id
            ).first()
            if not existing:
                pr = PeerReviewer(
                    cycle_id=cycle.id,
                    employee_id=emp_emp.id,
                    reviewer_id=peer_emp.id
                )
                db.add(pr)
                db.commit()

    yield {
        "record": rec,
        "cycle": cycle,
        "employee": emp_emp,
        "manager": mgr_emp,
    }

    # cleanup
    emp_emp.manager_id = old_manager_id
    rec.status = "pending_manager"
    rec.manager_scores = None
    rec.manager_comment = None
    rec.manager_submitted = False
    db.commit()

    # 清理 PeerReviewTask
    db.query(PeerReviewTask).filter(PeerReviewTask.record_id == rec.id).delete()
    db.commit()

    # 清理 Notification
    emp_user = db.query(User).filter(User.employee_id == emp_emp.id).first()
    if emp_user:
        db.query(Notification).filter(Notification.user_id == emp_user.id).delete()
        db.commit()


def test_submit_manager_score_success(mgr_token, pending_manager_record, db: Session):
    """经理成功提交评分，manager_submitted=True，状态变为 pending_peer"""
    rec = pending_manager_record["record"]
    payload = {
        "performance": 85,
        "ability": 88,
        "attitude": 92,
        "comment": "该员工工作积极主动，项目交付质量高，团队协作良好，建议继续保持。",
    }
    resp = client.post(
        f"/api/v1/scores/manager/{rec.id}",
        json=payload,
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["record_id"] == rec.id
    assert data["manager_scores"] == {"performance": 85, "ability": 88, "attitude": 92}
    assert data["status"] == "pending_peer"  # peer_review_enabled=True by default

    db.refresh(rec)
    assert rec.manager_submitted is True
    assert rec.status == "pending_peer"
    assert rec.manager_comment == payload["comment"]


def test_submit_manager_score_peer_tasks_created(mgr_token, pending_manager_record, db: Session):
    """peer_review_enabled=True 时创建 PeerReviewTask"""
    rec = pending_manager_record["record"]
    # 确保状态是 pending_manager
    rec.status = "pending_manager"
    rec.manager_submitted = False
    rec.manager_scores = None
    rec.manager_comment = None
    db.commit()

    # 清理已有的 PeerReviewTask
    db.query(PeerReviewTask).filter(PeerReviewTask.record_id == rec.id).delete()
    db.commit()

    payload = {
        "performance": 85,
        "ability": 88,
        "attitude": 92,
        "comment": "该员工工作积极主动，项目交付质量高，团队协作良好，建议继续保持。",
    }
    resp = client.post(
        f"/api/v1/scores/manager/{rec.id}",
        json=payload,
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert resp.status_code == 200

    # 验证 PeerReviewTask 创建
    tasks = db.query(PeerReviewTask).filter(PeerReviewTask.record_id == rec.id).all()
    assert len(tasks) >= 1


def test_submit_manager_score_no_peer_review(mgr_token, pending_manager_record, db: Session):
    """peer_review_enabled=False 时状态变为 pending_summary"""
    rec = pending_manager_record["record"]
    cycle = pending_manager_record["cycle"]

    # 设置 peer_review_enabled=False
    cycle.peer_review_enabled = False
    db.commit()

    rec.status = "pending_manager"
    rec.manager_submitted = False
    rec.manager_scores = None
    rec.manager_comment = None
    db.commit()

    payload = {
        "performance": 85,
        "ability": 88,
        "attitude": 92,
        "comment": "该员工工作积极主动，项目交付质量高，团队协作良好，建议继续保持。",
    }
    resp = client.post(
        f"/api/v1/scores/manager/{rec.id}",
        json=payload,
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending_summary"

    db.refresh(rec)
    assert rec.status == "pending_summary"

    # 恢复
    cycle.peer_review_enabled = True
    db.commit()


def test_submit_manager_score_notification(mgr_token, pending_manager_record, db: Session):
    """提交后发送通知给员工"""
    rec = pending_manager_record["record"]
    emp = pending_manager_record["employee"]

    rec.status = "pending_manager"
    rec.manager_submitted = False
    rec.manager_scores = None
    rec.manager_comment = None
    db.commit()

    # 清理通知
    emp_user = db.query(User).filter(User.employee_id == emp.id).first()
    if emp_user:
        db.query(Notification).filter(Notification.user_id == emp_user.id).delete()
        db.commit()

    payload = {
        "performance": 85,
        "ability": 88,
        "attitude": 92,
        "comment": "该员工工作积极主动，项目交付质量高，团队协作良好，建议继续保持。",
    }
    resp = client.post(
        f"/api/v1/scores/manager/{rec.id}",
        json=payload,
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert resp.status_code == 200

    # 验证通知
    if emp_user:
        notif = db.query(Notification).filter(Notification.user_id == emp_user.id).first()
        assert notif is not None
        assert "上级评分已完成" in notif.title


def test_submit_manager_score_422_short_comment(mgr_token, pending_manager_record):
    """评语少于20字返回 422"""
    rec = pending_manager_record["record"]
    payload = {
        "performance": 85,
        "ability": 88,
        "attitude": 92,
        "comment": "评语太短",
    }
    resp = client.post(
        f"/api/v1/scores/manager/{rec.id}",
        json=payload,
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert resp.status_code == 422
    assert "综合评语不少于20字" in resp.json()["message"]


def test_submit_manager_score_422_invalid_score(mgr_token, pending_manager_record):
    """分数超出范围返回 422"""
    rec = pending_manager_record["record"]
    for bad_score in [-1, 101]:
        payload = {
            "performance": bad_score,
            "ability": 88,
            "attitude": 92,
            "comment": "该员工工作积极主动，项目交付质量高，团队协作良好，建议继续保持。",
        }
        resp = client.post(
            f"/api/v1/scores/manager/{rec.id}",
            json=payload,
            headers={"Authorization": f"Bearer {mgr_token}"},
        )
        assert resp.status_code == 422, f"score={bad_score} should fail"
        assert "分数需在0-100之间" in resp.json()["message"]


def test_submit_manager_score_403_non_subordinate(mgr_token, pending_manager_record, db: Session):
    """非直属下属不能评分"""
    rec = pending_manager_record["record"]
    # 将记录的 employee_id 改为非下属
    old_emp_id = rec.employee_id
    admin = db.query(User).filter(User.username == "admin").first()
    if admin and admin.employee_id:
        rec.employee_id = admin.employee_id
        db.commit()

        payload = {
            "performance": 85,
            "ability": 88,
            "attitude": 92,
            "comment": "该员工工作积极主动，项目交付质量高，团队协作良好，建议继续保持。",
        }
        resp = client.post(
            f"/api/v1/scores/manager/{rec.id}",
            json=payload,
            headers={"Authorization": f"Bearer {mgr_token}"},
        )
        assert resp.status_code == 403
        assert "无权为此员工评分" in resp.json()["message"]

        rec.employee_id = old_emp_id
        db.commit()
    else:
        pytest.skip("缺少 admin 员工数据")


def test_submit_manager_score_boundary_values(mgr_token, pending_manager_record, db: Session):
    """边界值 0 和 100 应被接受"""
    for boundary in [0, 100]:
        db.expire_all()
        rec = db.query(AssessmentRecord).filter(AssessmentRecord.id == pending_manager_record["record"].id).first()
        rec.status = "pending_manager"
        rec.manager_submitted = False
        rec.manager_scores = None
        rec.manager_comment = None
        db.commit()
        db.refresh(rec)

        payload = {
            "performance": boundary,
            "ability": boundary,
            "attitude": boundary,
            "comment": "该员工工作积极主动，项目交付质量高，团队协作良好，建议继续保持。",
        }
        resp = client.post(
            f"/api/v1/scores/manager/{rec.id}",
            json=payload,
            headers={"Authorization": f"Bearer {mgr_token}"},
        )
        assert resp.status_code == 200, f"boundary={boundary} should pass"

    # final restore
    db.expire_all()
    rec = db.query(AssessmentRecord).filter(AssessmentRecord.id == pending_manager_record["record"].id).first()
    rec.status = "pending_manager"
    rec.manager_submitted = False
    rec.manager_scores = None
    rec.manager_comment = None
    db.commit()


def test_submit_manager_score_with_kpi(mgr_token, pending_manager_record, db: Session):
    """提交上级评分时携带 KPI 分数"""
    rec = pending_manager_record["record"]
    rec.status = "pending_manager"
    rec.manager_submitted = False
    rec.manager_scores = None
    rec.manager_comment = None
    rec.kpi_snapshot = '[{"name": "项目交付率", "weight": 60, "target": "100%"}, {"name": "代码质量", "weight": 40, "target": "95%"}]'
    db.commit()

    # 清理已有的 ScoreDetail
    from app.models import ScoreDetail
    db.query(ScoreDetail).filter(ScoreDetail.record_id == rec.id).delete()
    db.commit()

    payload = {
        "performance": 85,
        "ability": 88,
        "attitude": 92,
        "comment": "该员工工作积极主动，项目交付质量高，团队协作良好，建议继续保持。",
        "kpi_scores": [88, 92],
    }
    resp = client.post(
        f"/api/v1/scores/manager/{rec.id}",
        json=payload,
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert resp.status_code == 200

    # 验证 ScoreDetail 记录
    details = db.query(ScoreDetail).filter(ScoreDetail.record_id == rec.id).all()
    assert len(details) == 2
    assert float(details[0].manager_score) == 88
    assert float(details[1].manager_score) == 92

    # cleanup
    for d in details:
        db.delete(d)
    db.commit()
    rec.status = "pending_manager"
    rec.manager_submitted = False
    rec.manager_scores = None
    rec.manager_comment = None
    db.commit()


def test_submit_manager_score_alert_large_diff(mgr_token, pending_manager_record, db: Session):
    """上级评分与自评分差异超过20分时应返回 alerts"""
    rec = pending_manager_record["record"]
    rec.status = "pending_manager"
    rec.manager_submitted = False
    rec.manager_scores = None
    rec.manager_comment = None
    rec.self_scores = '{"performance": 80, "ability": 85, "attitude": 90}'
    db.commit()

    payload = {
        "performance": 40,  # diff = 40
        "ability": 60,      # diff = 25
        "attitude": 92,    # diff = 2
        "comment": "该员工工作积极主动，项目交付质量高，团队协作良好，建议继续保持。",
    }
    resp = client.post(
        f"/api/v1/scores/manager/{rec.id}",
        json=payload,
        headers={"Authorization": f"Bearer {mgr_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "alerts" in data
    assert len(data["alerts"]) == 2
    assert any("performance" in alert for alert in data["alerts"])
    assert any("ability" in alert for alert in data["alerts"])

    # restore
    rec.status = "pending_manager"
    rec.manager_submitted = False
    rec.manager_scores = None
    rec.manager_comment = None
    db.commit()


def test_submit_manager_score_employee_role_rejected(employee_token, pending_manager_record):
    """employee 角色不能提交上级评分"""
    rec = pending_manager_record["record"]
    payload = {
        "performance": 85,
        "ability": 88,
        "attitude": 92,
        "comment": "该员工工作积极主动，项目交付质量高，团队协作良好，建议继续保持。",
    }
    resp = client.post(
        f"/api/v1/scores/manager/{rec.id}",
        json=payload,
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 403
