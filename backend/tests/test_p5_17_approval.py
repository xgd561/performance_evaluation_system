import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date, timedelta, datetime

from app.models import (
    AssessmentRecord, AssessmentCycle, Employee, Department, Position, User,
    ApprovalRecord, SystemConfig, PeerReviewTask
)
from app.auth import get_password_hash


class TestP5_17Approval:
    """P5-17: 汇总与审批模块 — 单元测试（审批+面谈）"""

    def _login(self, client: TestClient, username: str, password: str):
        resp = client.post("/auth/login", json={"username": username, "password": password})
        assert resp.status_code == 200, resp.text
        return resp.json()["access_token"]

    def _create_employee_with_user(self, db_session: Session, username: str, employee_no: str, name: str, role: str, manager_id: int = None, department_id: int = None, position_id: int = None):
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
        emp = Employee(employee_no=employee_no, name=name, department_id=department_id if department_id else dept.id, position_id=position_id if position_id else pos.id, manager_id=manager_id)
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

    def _create_assessment_record(self, db_session: Session, cycle_id: int, employee_id: int, status: str = "pending_approval", grade: str = "B", total_score: float = 88.5):
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
            total_score=total_score,
            grade=grade,
            original_grade=grade,
            manager_comment="该员工表现良好",
            manager_draft_scores='{"performance": 84, "ability": 87, "attitude": 91}',
        )
        db_session.add(record)
        db_session.flush()
        return record

    def _create_cycle(self, db_session: Session):
        """创建考核周期"""
        cycle = AssessmentCycle(
            name="P5-17测试周期",
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

    # ------------------------------------------------------------------
    # 1. 审批列表权限隔离
    # ------------------------------------------------------------------

    def test_approval_list_step1_only_sees_department_records(self, client: TestClient, db_session: Session):
        """部门负责人只能看到本部门待审批记录"""
        # 创建两个部门
        dept_a = Department(name="部门A", code="DEPTA")
        dept_b = Department(name="部门B", code="DEPTB")
        db_session.add(dept_a)
        db_session.add(dept_b)
        db_session.flush()

        pos_a = Position(name="岗位A", department_id=dept_a.id)
        pos_b = Position(name="岗位B", department_id=dept_b.id)
        db_session.add(pos_a)
        db_session.add(pos_b)
        db_session.flush()

        # 部门A负责人
        head_a, head_a_user = self._create_employee_with_user(db_session, "p517_heada", "P517_HA", "负责人A", "manager", department_id=dept_a.id, position_id=pos_a.id)
        dept_a.head_id = head_a.id
        db_session.flush()

        # 部门A员工
        emp_a, emp_a_user = self._create_employee_with_user(db_session, "p517_empa", "P517_EA", "员工A", "employee", manager_id=head_a.id, department_id=dept_a.id, position_id=pos_a.id)
        # 部门B员工
        emp_b, emp_b_user = self._create_employee_with_user(db_session, "p517_empb", "P517_EB", "员工B", "employee", department_id=dept_b.id, position_id=pos_b.id)

        cycle = self._create_cycle(db_session)
        record_a = self._create_assessment_record(db_session, cycle.id, emp_a.id, status="pending_approval")
        record_b = self._create_assessment_record(db_session, cycle.id, emp_b.id, status="pending_approval")
        self._ensure_approval_chain(db_session)
        db_session.commit()

        token = self._login(client, "p517_heada", "Test@123")
        resp = client.get("/approvals/pending", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        record_ids = [r["record_id"] for r in data]
        assert record_a.id in record_ids
        assert record_b.id not in record_ids

    def test_approval_list_step2_sees_all_records(self, client: TestClient, db_session: Session):
        """HR 负责人可以看到全部待审批记录"""
        # 使用默认3步审批链，创建 step1 记录（无 approvals）
        dept_a = Department(name="部门C", code="DEPTC")
        dept_b = Department(name="部门D", code="DEPTD")
        db_session.add(dept_a)
        db_session.add(dept_b)
        db_session.flush()

        pos_a = Position(name="岗位C", department_id=dept_a.id)
        pos_b = Position(name="岗位D", department_id=dept_b.id)
        db_session.add(pos_a)
        db_session.add(pos_b)
        db_session.flush()

        mgr_a, _ = self._create_employee_with_user(db_session, "p517_mgra", "P517_MA", "经理A", "manager", department_id=dept_a.id, position_id=pos_a.id)
        mgr_b, _ = self._create_employee_with_user(db_session, "p517_mgrb", "P517_MB", "经理B", "manager", department_id=dept_b.id, position_id=pos_b.id)

        emp_a, _ = self._create_employee_with_user(db_session, "p517_empc", "P517_EC", "员工C", "employee", manager_id=mgr_a.id, department_id=dept_a.id, position_id=pos_a.id)
        emp_b, _ = self._create_employee_with_user(db_session, "p517_empd", "P517_ED", "员工D", "employee", manager_id=mgr_b.id, department_id=dept_b.id, position_id=pos_b.id)

        # 创建HR用户，并确保该HR员工有下属（使 direct_manager 条件不生效但 hr_head 条件生效）
        hr_emp, hr_user = self._create_employee_with_user(db_session, "p517_hr", "P517_HR", "HR专员", "hr")

        cycle = self._create_cycle(db_session)
        record_a = self._create_assessment_record(db_session, cycle.id, emp_a.id, status="pending_approval")
        record_b = self._create_assessment_record(db_session, cycle.id, emp_b.id, status="pending_approval")
        self._ensure_approval_chain(db_session)
        db_session.commit()

        # 默认审批链 ["direct_manager", "dept_head", "hr_head"] 有3步，step_index=0 对应 step=1
        # HR 角色在 step_idx=0,1,2 时都可以审批，因此能看到所有 pending_approval 且任一 step 的记录
        token = self._login(client, "p517_hr", "Test@123")
        resp = client.get("/approvals/pending", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        record_ids = [r["record_id"] for r in data]
        assert record_a.id in record_ids
        assert record_b.id in record_ids

    def test_approval_list_manager_not_approver_returns_empty(self, client: TestClient, db_session: Session):
        """非审批人角色返回空列表或 403"""
        # 创建一个普通员工用户（不是任何待审批记录的审批人）
        emp, emp_user = self._create_employee_with_user(db_session, "p517_empna", "P517_ENA", "普通员工", "employee")
        cycle = self._create_cycle(db_session)
        self._ensure_approval_chain(db_session)
        db_session.commit()

        token = self._login(client, "p517_empna", "Test@123")
        resp = client.get("/approvals/pending", headers={"Authorization": f"Bearer {token}"})
        # 员工角色不在 require_role 中，应该返回 403
        assert resp.status_code == 403

    # ------------------------------------------------------------------
    # 2. 审批详情数据完整性
    # ------------------------------------------------------------------

    def test_approval_detail_contains_all_fields(self, client: TestClient, db_session: Session):
        """详情返回包含 record、peer_comments、history、approval_history"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p517_mgr1", "P517_M1", "经理1", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p517_emp1", "P517_E1", "员工1", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_approval")
        self._ensure_approval_chain(db_session)
        db_session.commit()

        token = self._login(client, "p517_mgr1", "Test@123")
        resp = client.get(f"/approvals/{record.id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["record_id"] == record.id
        assert "self_scores" in data
        assert "manager_scores" in data
        assert "peer_scores" in data
        assert "peer_comments" in data
        assert "history" in data
        assert "approval_history" in data

    def test_approval_detail_403_for_unauthorized_user(self, client: TestClient, db_session: Session):
        """无权限用户访问返回 403"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p517_mgr2", "P517_M2", "经理2", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p517_emp2", "P517_E2", "员工2", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_approval")
        self._ensure_approval_chain(db_session)

        # 无关经理
        other_mgr, other_user = self._create_employee_with_user(db_session, "p517_omgr", "P517_OM", "其他经理", "manager")
        db_session.commit()

        token = self._login(client, "p517_omgr", "Test@123")
        resp = client.get(f"/approvals/{record.id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_approval_detail_peer_comments_included(self, client: TestClient, db_session: Session):
        """协作评分明细包含 reviewer_name、score、comment"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p517_mgr3", "P517_M3", "经理3", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p517_emp3", "P517_E3", "员工3", "employee", manager_id=mgr_emp.id)
        peer_emp, peer_user = self._create_employee_with_user(db_session, "p517_peer", "P517_PEER", "协作人", "peer")
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_approval")
        self._ensure_approval_chain(db_session)

        peer_task = PeerReviewTask(
            record_id=record.id,
            reviewer_id=peer_emp.id,
            ability_score=88.0,
            comment="协作能力很好",
            status="completed",
        )
        db_session.add(peer_task)
        db_session.commit()

        token = self._login(client, "p517_mgr3", "Test@123")
        resp = client.get(f"/approvals/{record.id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "peer_comments" in data
        assert len(data["peer_comments"]) == 1
        pc = data["peer_comments"][0]
        assert pc["reviewer_name"] == "协作人"
        assert pc["ability_score"] in ("88.0", "88.00")
        assert pc["comment"] == "协作能力很好"

    # ------------------------------------------------------------------
    # 3. 审批动作
    # ------------------------------------------------------------------

    def test_approve_step1_success_status_pending_approval(self, client: TestClient, db_session: Session):
        """Step 1 通过，状态保持 pending_approval，记录审批日志"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p517_mgr4", "P517_M4", "经理4", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p517_emp4", "P517_E4", "员工4", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_approval")
        self._ensure_approval_chain(db_session)
        db_session.commit()

        token = self._login(client, "p517_mgr4", "Test@123")
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

        # 验证审批日志
        approvals = db_session.query(ApprovalRecord).filter(ApprovalRecord.record_id == record.id).all()
        assert len(approvals) == 1
        assert approvals[0].action == "approved"

    def test_approve_step2_success_status_pending_interview(self, client: TestClient, db_session: Session):
        """Step 2 通过，状态变为 pending_interview"""
        # 使用2步审批链，使第二步成为最后一步
        cfg = db_session.query(SystemConfig).filter(SystemConfig.key == "approval_chain").first()
        if cfg:
            cfg.value = '["direct_manager", "dept_head"]'
        else:
            cfg = SystemConfig(key="approval_chain", value='["direct_manager", "dept_head"]')
            db_session.add(cfg)
        db_session.flush()

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

        head_emp, head_user = self._create_employee_with_user(db_session, "p517_head", "P517_HEAD", "部门负责人", "manager", department_id=dept.id, position_id=pos.id)
        dept.head_id = head_emp.id
        db_session.flush()

        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p517_mgr5", "P517_M5", "经理5", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p517_emp5", "P517_E5", "员工5", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_approval")

        # 先完成第一步审批
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

        token = self._login(client, "p517_head", "Test@123")
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

    def test_reject_success_status_pending_approval(self, client: TestClient, db_session: Session):
        """驳回，状态保持 pending_approval"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p517_mgr6", "P517_M6", "经理6", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p517_emp6", "P517_E6", "员工6", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_approval")
        self._ensure_approval_chain(db_session)
        db_session.commit()

        token = self._login(client, "p517_mgr6", "Test@123")
        resp = client.post(
            f"/approvals/{record.id}/reject",
            json={"reason": "该员工绩效考核数据存在明显错误，需要重新核对后提交。"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        db_session.refresh(record)
        assert record.status == "pending_approval"

        # 验证驳回日志
        approvals = db_session.query(ApprovalRecord).filter(ApprovalRecord.record_id == record.id).all()
        assert len(approvals) == 1
        assert approvals[0].action == "rejected"

    def test_rollback_success_status_pending_manager(self, client: TestClient, db_session: Session):
        """打回，状态变为 pending_manager"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p517_mgr7", "P517_M7", "经理7", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p517_emp7", "P517_E7", "员工7", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_approval")
        self._ensure_approval_chain(db_session)
        db_session.commit()

        token = self._login(client, "p517_mgr7", "Test@123")
        resp = client.post(
            f"/approvals/{record.id}/rollback",
            json={"reason": "该员工绩效考核数据存在明显错误，需要重新核对后提交。"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        db_session.refresh(record)
        assert record.status == "pending_manager"

    def test_rollback_clears_manager_scores(self, client: TestClient, db_session: Session):
        """打回后 manager_scores、manager_comment、total_score、grade、original_grade 被清空"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p517_mgr8", "P517_M8", "经理8", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p517_emp8", "P517_E8", "员工8", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_approval")
        self._ensure_approval_chain(db_session)
        db_session.commit()

        token = self._login(client, "p517_mgr8", "Test@123")
        resp = client.post(
            f"/approvals/{record.id}/rollback",
            json={"reason": "该员工绩效考核数据存在明显错误，需要重新核对后提交。"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        db_session.refresh(record)
        assert record.manager_scores is None
        assert record.manager_comment is None
        assert record.total_score is None
        assert record.grade is None
        assert record.original_grade is None
        assert record.manager_draft_scores is None

    def test_rollback_keeps_self_and_peer_scores(self, client: TestClient, db_session: Session):
        """打回后 self_scores 和 peer_scores 仍然保留"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p517_mgr9", "P517_M9", "经理9", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p517_emp9", "P517_E9", "员工9", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_approval")
        self._ensure_approval_chain(db_session)
        db_session.commit()

        token = self._login(client, "p517_mgr9", "Test@123")
        resp = client.post(
            f"/approvals/{record.id}/rollback",
            json={"reason": "该员工绩效考核数据存在明显错误，需要重新核对后提交。"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        db_session.refresh(record)
        assert record.self_scores is not None
        assert record.peer_scores is not None

    def test_duplicate_approval_returns_409(self, client: TestClient, db_session: Session):
        """重复审批返回 409"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p517_mgr10", "P517_M10", "经理10", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p517_emp10", "P517_E10", "员工10", "employee", manager_id=mgr_emp.id)
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

        token = self._login(client, "p517_mgr10", "Test@123")
        resp = client.post(
            f"/approvals/{record.id}/approve",
            json={"comment": "该员工工作表现优秀，项目交付质量高，建议通过审批。"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409

    def test_comment_too_short_returns_422(self, client: TestClient, db_session: Session):
        """审批意见少于10字返回 422"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p517_mgr11", "P517_M11", "经理11", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p517_emp11", "P517_E11", "员工11", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_approval")
        self._ensure_approval_chain(db_session)
        db_session.commit()

        token = self._login(client, "p517_mgr11", "Test@123")
        resp = client.post(
            f"/approvals/{record.id}/approve",
            json={"comment": "太短"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    # ------------------------------------------------------------------
    # 4. 面谈校验与状态转换
    # ------------------------------------------------------------------

    def test_interview_c_grade_missing_improvement_plan_returns_400(self, client: TestClient, db_session: Session):
        """C 等级未填改进计划返回 400"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p517_mgr12", "P517_M12", "经理12", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p517_emp12", "P517_E12", "员工12", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_interview", grade="C", total_score=65.0)
        db_session.commit()

        token = self._login(client, "p517_mgr12", "Test@123")
        resp = client.post(
            f"/api/v1/assessment-records/{record.id}/interview",
            json={
                "interview_time": (datetime.now() - timedelta(days=1)).isoformat(),
                "location": "会议室A",
                "content": "a" * 50,
                "improvement_plan": None,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    def test_interview_success_status_published(self, client: TestClient, db_session: Session):
        """面谈成功提交后状态变为 published"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p517_mgr13", "P517_M13", "经理13", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p517_emp13", "P517_E13", "员工13", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_interview", grade="B", total_score=85.0)
        db_session.commit()

        token = self._login(client, "p517_mgr13", "Test@123")
        resp = client.post(
            f"/api/v1/assessment-records/{record.id}/interview",
            json={
                "interview_time": (datetime.now() - timedelta(days=1)).isoformat(),
                "location": "会议室A",
                "content": "a" * 50,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["status"] == "published"
        assert data["interview_record"] is not None
        assert data["interview_record"]["interviewer_id"] == mgr_emp.id

    def test_interview_content_too_short_returns_422(self, client: TestClient, db_session: Session):
        """沟通内容少于50字返回 422"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p517_mgr14", "P517_M14", "经理14", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p517_emp14", "P517_E14", "员工14", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_interview", grade="B")
        db_session.commit()

        token = self._login(client, "p517_mgr14", "Test@123")
        resp = client.post(
            f"/api/v1/assessment-records/{record.id}/interview",
            json={
                "interview_time": (datetime.now() - timedelta(days=1)).isoformat(),
                "location": "会议室A",
                "content": "太短",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_interview_not_direct_manager_returns_403(self, client: TestClient, db_session: Session):
        """非直属上级提交返回 403"""
        mgr_emp, mgr_user = self._create_employee_with_user(db_session, "p517_mgr15", "P517_M15", "经理15", "manager")
        other_mgr, other_mgr_user = self._create_employee_with_user(db_session, "p517_omgr2", "P517_OM2", "其他经理2", "manager")
        emp_emp, emp_user = self._create_employee_with_user(db_session, "p517_emp15", "P517_E15", "员工15", "employee", manager_id=mgr_emp.id)
        cycle = self._create_cycle(db_session)
        record = self._create_assessment_record(db_session, cycle.id, emp_emp.id, status="pending_interview", grade="B")
        db_session.commit()

        token = self._login(client, "p517_omgr2", "Test@123")
        resp = client.post(
            f"/api/v1/assessment-records/{record.id}/interview",
            json={
                "interview_time": (datetime.now() - timedelta(days=1)).isoformat(),
                "location": "会议室A",
                "content": "a" * 50,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
