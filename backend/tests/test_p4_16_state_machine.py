import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.models import (
    AssessmentRecord, AssessmentCycle, Employee, Department, Position, User,
    PeerReviewer, PeerReviewTask
)
from app.auth import get_password_hash
from app.utils.workflow_state_machine import WorkflowStateMachine
from app.core.exceptions import BizError


class TestWorkflowStateMachineUnit:
    """P4-16: 状态机单元测试——评分相关状态转换"""

    def test_submit_self_pending_self_to_pending_manager(self):
        """1. submit_self 从 pending_self → pending_manager"""
        next_state = WorkflowStateMachine.transition(
            current_state="pending_self",
            action="submit_self",
        )
        assert next_state == "pending_manager"

    def test_submit_manager_with_peer_review_enabled_to_pending_peer(self):
        """2. submit_manager 从 pending_manager，peer_review_enabled=True → pending_peer"""
        next_state = WorkflowStateMachine.transition(
            current_state="pending_manager",
            action="submit_manager",
            peer_review_enabled=True,
        )
        assert next_state == "pending_peer"

    def test_submit_manager_with_peer_review_disabled_to_pending_summary(self):
        """3. submit_manager 从 pending_manager，peer_review_enabled=False → pending_summary"""
        next_state = WorkflowStateMachine.transition(
            current_state="pending_manager",
            action="submit_manager",
            peer_review_enabled=False,
        )
        assert next_state == "pending_summary"

    def test_complete_peer_pending_peer_to_pending_summary(self):
        """4. complete_peer 从 pending_peer → pending_summary"""
        next_state = WorkflowStateMachine.transition(
            current_state="pending_peer",
            action="complete_peer",
        )
        assert next_state == "pending_summary"

    def test_invalid_transition_pending_self_to_submit_manager_raises(self):
        """5. 非法转换：pending_self → submit_manager 应抛出 BizError(code=1101)"""
        with pytest.raises(BizError) as exc_info:
            WorkflowStateMachine.transition(
                current_state="pending_self",
                action="submit_manager",
            )
        assert exc_info.value.code == 1101
        assert "不允许执行动作" in exc_info.value.message

    def test_unknown_state_transition_raises(self):
        """6. 未知状态转换应抛出 BizError(code=1100)"""
        with pytest.raises(BizError) as exc_info:
            WorkflowStateMachine.transition(
                current_state="unknown",
                action="submit_self",
            )
        assert exc_info.value.code == 1100
        assert "未知状态" in exc_info.value.message


class TestWorkflowStateMachineIntegration:
    """P4-16: 状态机与评分端点集成测试"""

    def _create_cycle(self, db_session: Session, peer_review_enabled: bool = True):
        """创建考核周期"""
        cycle = AssessmentCycle(
            name="P4-16测试周期",
            type="monthly",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            peer_review_enabled=peer_review_enabled,
        )
        db_session.add(cycle)
        db_session.flush()
        return cycle

    def _create_employee_with_user(self, db_session: Session, username: str, employee_no: str, name: str, role: str, manager_id: int = None):
        """创建员工及对应用户"""
        dept = db_session.query(Department).filter(Department.code == "TEST").first()
        if not dept:
            dept = Department(name="测试部", code="TEST")
            db_session.add(dept)
            db_session.flush()
        pos = db_session.query(Position).filter(Position.name == "测试岗", Position.department_id == dept.id).first()
        if not pos:
            pos = Position(name="测试岗", department_id=dept.id)
            db_session.add(pos)
            db_session.flush()
        emp = Employee(employee_no=employee_no, name=name, department_id=dept.id, position_id=pos.id, manager_id=manager_id)
        db_session.add(emp)
        db_session.flush()
        user = User(
            username=username,
            password_hash=get_password_hash("Test@123"),
            role=role,
            employee_id=emp.id,
            is_first_login=False,
        )
        db_session.add(user)
        db_session.flush()
        return emp, user

    def _create_assessment_record(self, db_session: Session, cycle_id: int, employee_id: int, status: str = "pending_self"):
        """创建考核记录"""
        emp = db_session.query(Employee).filter(Employee.id == employee_id).first()
        record = AssessmentRecord(
            cycle_id=cycle_id,
            employee_id=employee_id,
            department_id=emp.department_id if emp else None,
            position_id=emp.position_id if emp else None,
            status=status,
            self_scores='{"performance": 80, "ability": 85, "attitude": 90}',
        )
        db_session.add(record)
        db_session.flush()
        return record

    def test_self_assessment_endpoint_transitions_to_pending_manager(self, client: TestClient, employee_token, db_session: Session):
        """7. 自评提交端点通过状态机将记录从 pending_self 转为 pending_manager"""
        emp, user = self._create_employee_with_user(db_session, "sm_emp", "SM001", "自评员工", "employee")
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp.id, status="pending_self")
        db_session.commit()

        # 使用 employee_token 登录获取 token（但 employee_token 是 conftest 的 fixture，对应 emp001）
        # 这里我们需要用新创建的用户登录，因为 employee_token 固定对应 emp001
        resp = client.post("/auth/login", json={"username": "sm_emp", "password": "Test@123"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        payload = {"performance": 82, "ability": 86, "attitude": 91}
        resp = client.post(
            f"/scores/self/{record.id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending_manager"

        db_session.refresh(record)
        assert record.status == "pending_manager"

    def test_manager_score_endpoint_with_peer_review_enabled_transitions_to_pending_peer(self, client: TestClient, manager_token, db_session: Session):
        """8. 经理评分端点（peer_review_enabled=True）通过状态机转为 pending_peer"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "sm_mgr", "SM_MGR", "经理", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "sm_sub", "SM_SUB", "下属员工", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session, peer_review_enabled=True)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_manager")
        db_session.commit()

        # 使用 manager_token 登录获取 token（但 manager_token 对应 mgr001）
        # 这里我们需要用新创建的经理用户登录
        resp = client.post("/auth/login", json={"username": "sm_mgr", "password": "Test@123"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        payload = {
            "performance": 85,
            "ability": 88,
            "attitude": 92,
            "comment": "该员工工作积极主动，项目交付质量高，团队协作良好，建议继续保持。",
        }
        resp = client.post(
            f"/scores/manager/{record.id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending_peer"

        db_session.refresh(record)
        assert record.status == "pending_peer"

    def test_manager_score_endpoint_with_peer_review_disabled_transitions_to_pending_summary(self, client: TestClient, manager_token, db_session: Session):
        """9. 经理评分端点（peer_review_enabled=False）通过状态机转为 pending_summary"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "sm_mgr2", "SM_MGR2", "经理2", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "sm_sub2", "SM_SUB2", "下属员工2", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session, peer_review_enabled=False)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_manager")
        db_session.commit()

        resp = client.post("/auth/login", json={"username": "sm_mgr2", "password": "Test@123"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        payload = {
            "performance": 85,
            "ability": 88,
            "attitude": 92,
            "comment": "该员工工作积极主动，项目交付质量高，团队协作良好，建议继续保持。",
        }
        resp = client.post(
            f"/scores/manager/{record.id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending_summary"

        db_session.refresh(record)
        assert record.status == "pending_summary"

    def test_peer_review_task_submit_transitions_record_to_pending_summary_when_all_completed(self, client: TestClient, peer_token, db_session: Session):
        """10. 协作评分任务提交端点，当所有任务完成时通过状态机转为 pending_summary"""
        # 创建经理、被评员工、协作人
        mgr_emp, _ = self._create_employee_with_user(db_session, "sm_mgr3", "SM_MGR3", "经理3", "manager")
        emp_emp, _ = self._create_employee_with_user(db_session, "sm_sub3", "SM_SUB3", "被评员工", "employee", manager_id=mgr_emp.id)
        peer_emp, peer_user = self._create_employee_with_user(db_session, "sm_peer", "SM_PEER", "协作人", "peer")
        cycle = self._create_cycle(db_session, peer_review_enabled=True)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_peer")

        # 创建 PeerReviewer 关系
        pr = PeerReviewer(cycle_id=cycle.id, employee_id=emp_emp.id, reviewer_id=peer_emp.id)
        db_session.add(pr)
        db_session.flush()

        # 创建 PeerReviewTask（经理提交后通常会创建，这里直接模拟）
        task = PeerReviewTask(record_id=record.id, reviewer_id=peer_emp.id, status="pending")
        db_session.add(task)
        db_session.commit()

        # 使用 peer_token 登录获取 token（但 peer_token 对应 peer001）
        # 这里我们需要用新创建的协作人用户登录
        resp = client.post("/auth/login", json={"username": "sm_peer", "password": "Test@123"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        payload = {
            "ability": 88,
            "comment": "该员工协作能力优秀，沟通顺畅，项目推进得力，表现非常出色。",
        }
        resp = client.post(
            f"/scores/peer/review-tasks/{task.id}/submit",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"

        db_session.refresh(record)
        assert record.status == "pending_summary"
