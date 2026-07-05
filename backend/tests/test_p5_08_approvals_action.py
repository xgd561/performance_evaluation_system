import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.models import (
    AssessmentRecord, AssessmentCycle, Employee, Department, Position, User,
    ApprovalRecord, SystemConfig
)
from app.auth import get_password_hash
from app.database import SessionLocal

client = TestClient


@pytest.fixture(scope="module")
def db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TestP5_08ApprovalsAction:
    """P5-08: 审批动作端点重构测试"""

    def _login(self, client: TestClient, username: str, password: str):
        resp = client.post("/auth/login", json={"username": username, "password": password})
        assert resp.status_code == 200, resp.text
        return resp.json()["access_token"]

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

    def _create_assessment_record(self, db_session: Session, cycle_id: int, employee_id: int, status: str = "pending_approval"):
        """创建考核记录"""
        emp = db_session.query(Employee).filter(Employee.id == employee_id).first()
        record = AssessmentRecord(
            cycle_id=cycle_id,
            employee_id=employee_id,
            department_id=emp.department_id if emp else None,
            position_id=emp.position_id if emp else None,
            status=status,
            self_scores='{"performance": 80, "ability": 85, "attitude": 90}',
            manager_scores='{"performance": 85, "ability": 88, "attitude": 92}',
            peer_scores='{"ability": 87}',
            total_score=88.5,
            grade="B",
            original_grade="B",
            manager_comment="该员工表现良好",
            manager_draft_scores='{"performance": 84, "ability": 87, "attitude": 91}',
        )
        db_session.add(record)
        db_session.flush()
        return record

    def _create_cycle(self, db_session: Session):
        """创建考核周期"""
        cycle = AssessmentCycle(
            name="P5-08测试周期",
            type="monthly",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )
        db_session.add(cycle)
        db_session.flush()
        return cycle

    def _ensure_approval_chain(self, db_session: Session):
        """确保审批链配置为默认"""
        cfg = db_session.query(SystemConfig).filter(SystemConfig.key == "approval_chain").first()
        if not cfg:
            cfg = SystemConfig(key="approval_chain", value='["direct_manager", "dept_head", "hr_head"]')
            db_session.add(cfg)
            db_session.flush()
        return cfg

    def test_approve_step1_success_status_stays_pending_approval(self, client: TestClient, db_session: Session):
        """1. 第一步审批通过，状态保持 pending_approval"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p508_mgr1", "P508_M1", "经理1", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p508_emp1", "P508_E1", "员工1", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_approval")
        self._ensure_approval_chain(db_session)
        db_session.commit()

        token = self._login(client, "p508_mgr1", "Test@123")
        resp = client.post(
            f"/approvals/{record.id}/approve",
            json={"comment": "该员工工作表现优秀，项目交付质量高，建议通过审批。"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending_approval"

        db_session.refresh(record)
        assert record.status == "pending_approval"

    def test_approve_step2_success_status_becomes_pending_interview(self, client: TestClient, db_session: Session):
        """2. 第二步审批通过，状态变为 pending_interview"""
        # 使用2步审批链，使第二步成为最后一步
        cfg = db_session.query(SystemConfig).filter(SystemConfig.key == "approval_chain").first()
        if cfg:
            cfg.value = '["direct_manager", "dept_head"]'
        else:
            cfg = SystemConfig(key="approval_chain", value='["direct_manager", "dept_head"]')
            db_session.add(cfg)
        db_session.flush()

        # 创建部门负责人（同时是经理）
        dept = db_session.query(Department).filter(Department.code == "TEST").first()
        if not dept:
            dept = Department(name="测试部", code="TEST")
            db_session.add(dept)
            db_session.flush()

        head_emp, head_user = self._create_employee_with_user(db_session, "p508_head", "P508_HEAD", "部门负责人", "manager")
        dept.head_id = head_emp.id
        db_session.flush()

        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p508_mgr2", "P508_M2", "经理2", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p508_emp2", "P508_E2", "员工2", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_approval")

        # 先完成第一步审批（direct_manager）
        approval1 = ApprovalRecord(
            record_id=record.id,
            approver_id=mgr_emp.id,
            approver_role="direct_manager",
            step_index=1,
            action="approved",
            comment="第一步审批通过",
        )
        db_session.add(approval1)
        db_session.flush()

        db_session.commit()

        # 第二步用 dept_head 审批
        token = self._login(client, "p508_head", "Test@123")
        resp = client.post(
            f"/approvals/{record.id}/approve",
            json={"comment": "该员工工作表现优秀，项目交付质量高，建议通过审批。"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending_interview"

        db_session.refresh(record)
        assert record.status == "pending_interview"

    def test_reject_keeps_status_pending_approval(self, client: TestClient, db_session: Session):
        """3. 驳回保持状态为 pending_approval"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p508_mgr3", "P508_M3", "经理3", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p508_emp3", "P508_E3", "员工3", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_approval")
        self._ensure_approval_chain(db_session)
        db_session.commit()

        token = self._login(client, "p508_mgr3", "Test@123")
        resp = client.post(
            f"/approvals/{record.id}/reject",
            json={"reason": "该员工绩效考核数据存在明显错误，需要重新核对后提交。"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        db_session.refresh(record)
        assert record.status == "pending_approval"

    def test_rollback_clears_only_manager_data_and_status_pending_manager(self, client: TestClient, db_session: Session):
        """4. 打回仅清除经理数据，状态变为 pending_manager，保留自评和协作评分"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p508_mgr4", "P508_M4", "经理4", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p508_emp4", "P508_E4", "员工4", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_approval")
        self._ensure_approval_chain(db_session)
        db_session.commit()

        token = self._login(client, "p508_mgr4", "Test@123")
        resp = client.post(
            f"/approvals/{record.id}/rollback",
            json={"reason": "该员工绩效考核数据存在明显错误，需要重新核对后提交。"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        db_session.refresh(record)
        assert record.status == "pending_manager"
        # 自评和协作评分应保留
        assert record.self_scores is not None
        assert record.peer_scores is not None
        # 经理相关数据应被清除
        assert record.manager_scores is None
        assert record.manager_draft_scores is None
        assert record.manager_comment is None
        assert record.total_score is None
        assert record.grade is None
        assert record.original_grade is None

    def test_approve_comment_too_short_returns_422(self, client: TestClient, db_session: Session):
        """5. comment 少于 10 字符返回 422"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p508_mgr5", "P508_M5", "经理5", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p508_emp5", "P508_E5", "员工5", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_approval")
        self._ensure_approval_chain(db_session)
        db_session.commit()

        token = self._login(client, "p508_mgr5", "Test@123")
        resp = client.post(
            f"/approvals/{record.id}/approve",
            json={"comment": "太短"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_duplicate_approval_returns_409(self, client: TestClient, db_session: Session):
        """6. 重复审批返回 409"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p508_mgr6", "P508_M6", "经理6", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p508_emp6", "P508_E6", "员工6", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_approval")
        self._ensure_approval_chain(db_session)

        # 手动创建一个 approval record（使用 override 类型，使 existing 查询找不到，但 duplicate 查询能找到）
        approval = ApprovalRecord(
            record_id=record.id,
            approver_id=mgr_emp.id,
            approver_role="direct_manager",
            step_index=1,
            action="approved",
            approval_type="override",
            comment="手动创建的审批记录",
        )
        db_session.add(approval)
        db_session.commit()

        token = self._login(client, "p508_mgr6", "Test@123")
        resp = client.post(
            f"/approvals/{record.id}/approve",
            json={"comment": "该员工工作表现优秀，项目交付质量高，建议通过审批。"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409

    def test_unauthorized_user_returns_403(self, client: TestClient, db_session: Session):
        """7. 无权限用户返回 403"""
        # 创建经理A和员工（经理A是员工的直接上级）
        mgr_a, mgr_a_user = self._create_employee_with_user(db_session, "p508_mgra", "P508_MA", "经理A", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p508_emp7", "P508_E7", "员工7", "employee", manager_id=mgr_a.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_approval")
        self._ensure_approval_chain(db_session)

        # 创建经理B（不是该员工的上级）
        mgr_b, mgr_b_user = self._create_employee_with_user(db_session, "p508_mgrb", "P508_MB", "经理B", "manager")
        db_session.commit()

        # 用经理B尝试审批
        token = self._login(client, "p508_mgrb", "Test@123")
        resp = client.post(
            f"/approvals/{record.id}/approve",
            json={"comment": "该员工工作表现优秀，项目交付质量高，建议通过审批。"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_non_pending_approval_status_returns_422(self, client: TestClient, db_session: Session):
        """8. 非 pending_approval 状态返回 422"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p508_mgr8", "P508_M8", "经理8", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p508_emp8", "P508_E8", "员工8", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_self")
        self._ensure_approval_chain(db_session)
        db_session.commit()

        token = self._login(client, "p508_mgr8", "Test@123")
        resp = client.post(
            f"/approvals/{record.id}/approve",
            json={"comment": "该员工工作表现优秀，项目交付质量高，建议通过审批。"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422
