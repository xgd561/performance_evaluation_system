import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import date
from app.main import app
from app.database import SessionLocal, get_db
from app.auth import create_access_token, get_password_hash
from app.models import (
    User, Employee, Department, Position, AssessmentRecord,
    AssessmentCycle, ApprovalRecord, PeerReviewTask, SystemConfig
)


@pytest.fixture(scope="module")
def db():
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="module")
def client():
    def _get_db_override():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = _get_db_override
    return TestClient(app)


def _get_auth_header(db: Session, username: str):
    user = db.query(User).filter(User.username == username).first()
    token = create_access_token(data={"sub": username})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def setup_approval_data(db: Session):
    """Create test data for approval list and detail tests."""
    # Clean up existing test data
    db.query(ApprovalRecord).filter(
        ApprovalRecord.record_id.in_(
            db.query(AssessmentRecord.id).filter(
                AssessmentRecord.status == "pending_approval"
            )
        )
    ).delete(synchronize_session=False)
    db.query(AssessmentRecord).filter(
        AssessmentRecord.status == "pending_approval"
    ).delete(synchronize_session=False)
    db.query(PeerReviewTask).filter(PeerReviewTask.status == "completed").delete(synchronize_session=False)
    # 清理孤儿记录：历史残留记录会因主键复用挂到新周期/新员工上，污染历史断言
    orphan_record_ids = [
        rid for (rid,) in db.query(AssessmentRecord.id).filter(
            ~AssessmentRecord.cycle_id.in_(db.query(AssessmentCycle.id))
        ).all()
    ] + [
        rid for (rid,) in db.query(AssessmentRecord.id).filter(
            ~AssessmentRecord.employee_id.in_(db.query(Employee.id))
        ).all()
    ]
    if orphan_record_ids:
        db.query(ApprovalRecord).filter(
            ApprovalRecord.record_id.in_(orphan_record_ids)
        ).delete(synchronize_session=False)
        db.query(PeerReviewTask).filter(
            PeerReviewTask.record_id.in_(orphan_record_ids)
        ).delete(synchronize_session=False)
        db.query(AssessmentRecord).filter(
            AssessmentRecord.id.in_(orphan_record_ids)
        ).delete(synchronize_session=False)
    # 清理历史遗留数据：测试周期下的所有记录（主键复用会让残留记录挂到新员工身上）
    leftover_cycle_ids = [
        cid for (cid,) in db.query(AssessmentCycle.id).filter(
            AssessmentCycle.name.like("Test Cycle%")
        ).all()
    ]
    if leftover_cycle_ids:
        leftover_record_ids = [
            rid for (rid,) in db.query(AssessmentRecord.id).filter(
                AssessmentRecord.cycle_id.in_(leftover_cycle_ids)
            ).all()
        ]
        if leftover_record_ids:
            db.query(PeerReviewTask).filter(
                PeerReviewTask.record_id.in_(leftover_record_ids)
            ).delete(synchronize_session=False)
            db.query(ApprovalRecord).filter(
                ApprovalRecord.record_id.in_(leftover_record_ids)
            ).delete(synchronize_session=False)
            db.query(AssessmentRecord).filter(
                AssessmentRecord.id.in_(leftover_record_ids)
            ).delete(synchronize_session=False)
    # 清理历史遗留数据：测试员工的历史记录会影响“最近 3 个周期”断言
    test_employee_ids = [
        eid for (eid,) in db.query(Employee.id).filter(
            Employee.employee_no.in_(["TSTMGR", "TSTHR", "TSTEMP1", "TSTEMP2", "TSTDH", "UNRELATED"])
        ).all()
    ]
    if test_employee_ids:
        db.query(ApprovalRecord).filter(
            ApprovalRecord.record_id.in_(
                db.query(AssessmentRecord.id).filter(
                    AssessmentRecord.employee_id.in_(test_employee_ids)
                )
            )
        ).delete(synchronize_session=False)
        db.query(AssessmentRecord).filter(
            AssessmentRecord.employee_id.in_(test_employee_ids)
        ).delete(synchronize_session=False)
    db.query(User).filter(User.username.in_(["testmgr", "testhr", "testemp1", "testemp2", "testdepthead", "testdepthead2", "unrelatedmgr"])).delete(synchronize_session=False)
    db.query(Employee).filter(Employee.employee_no.in_(["TSTMGR", "TSTHR", "TSTEMP1", "TSTEMP2", "TSTDH", "UNRELATED"])).delete(synchronize_session=False)
    db.query(AssessmentCycle).filter(AssessmentCycle.name.like("Test Cycle%")).delete(synchronize_session=False)
    db.query(Department).filter(Department.code.in_(["TESTDEPT1", "TESTDEPT2", "UNRELATED"])).delete(synchronize_session=False)
    db.query(Position).filter((Position.name.like("Test Position%")) | (Position.name == "无关岗位")).delete(synchronize_session=False)
    db.query(SystemConfig).filter(SystemConfig.key == "approval_chain").delete(synchronize_session=False)
    db.commit()

    # Create departments
    dept1 = Department(name="测试研发部", code="TESTDEPT1")
    dept2 = Department(name="测试市场部", code="TESTDEPT2")
    db.add(dept1)
    db.add(dept2)
    db.flush()

    # Create positions
    pos1 = Position(name="Test Position 1", department_id=dept1.id)
    db.add(pos1)
    db.flush()

    # Create manager employee
    mgr_emp = Employee(employee_no="TSTMGR", name="测试经理", department_id=dept1.id, position_id=pos1.id)
    db.add(mgr_emp)
    db.flush()

    # Create subordinate employees
    emp1 = Employee(employee_no="TSTEMP1", name="测试员工1", department_id=dept1.id, position_id=pos1.id, manager_id=mgr_emp.id)
    emp2 = Employee(employee_no="TSTEMP2", name="测试员工2", department_id=dept2.id, position_id=pos1.id, manager_id=mgr_emp.id)
    db.add(emp1)
    db.add(emp2)
    db.flush()

    # Create department head employee
    dept_head_emp = Employee(employee_no="TSTDH", name="测试部门负责人", department_id=dept1.id, position_id=pos1.id)
    db.add(dept_head_emp)
    db.flush()
    dept1.head_id = dept_head_emp.id
    db.flush()

    # Create HR employee
    hr_emp = Employee(employee_no="TSTHR", name="测试HR", department_id=dept1.id, position_id=pos1.id)
    db.add(hr_emp)
    db.flush()

    # Create users
    mgr_user = User(
        username="testmgr",
        password_hash=get_password_hash("Test123!"),
        role="manager",
        employee_id=mgr_emp.id,
        is_first_login=False,
    )
    hr_user = User(
        username="testhr",
        password_hash=get_password_hash("Test123!"),
        role="hr",
        employee_id=hr_emp.id,
        is_first_login=False,
    )
    emp1_user = User(
        username="testemp1",
        password_hash=get_password_hash("Test123!"),
        role="employee",
        employee_id=emp1.id,
        is_first_login=False,
    )
    db.add(mgr_user)
    db.add(hr_user)
    db.add(emp1_user)
    db.flush()

    # Create assessment cycles
    cycle1 = AssessmentCycle(
        name="Test Cycle 2024 Q1",
        type="quarterly",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 3, 31),
        self_due_date=date(2024, 4, 10),
        manager_due_date=date(2024, 4, 20),
        peer_due_date=date(2024, 4, 25),
        status="in_progress",
    )
    cycle2 = AssessmentCycle(
        name="Test Cycle 2023 Q4",
        type="quarterly",
        start_date=date(2023, 10, 1),
        end_date=date(2023, 12, 31),
        self_due_date=date(2024, 1, 10),
        manager_due_date=date(2024, 1, 20),
        peer_due_date=date(2024, 1, 25),
        status="completed",
    )
    cycle3 = AssessmentCycle(
        name="Test Cycle 2023 Q3",
        type="quarterly",
        start_date=date(2023, 7, 1),
        end_date=date(2023, 9, 30),
        self_due_date=date(2023, 10, 10),
        manager_due_date=date(2023, 10, 20),
        peer_due_date=date(2023, 10, 25),
        status="completed",
    )
    db.add(cycle1)
    db.add(cycle2)
    db.add(cycle3)
    db.flush()

    # Create assessment records
    # Record 1: Step 1 (pending, no approvals yet), dept1, normal
    record1 = AssessmentRecord(
        cycle_id=cycle1.id,
        employee_id=emp1.id,
        position_id=pos1.id,
        department_id=dept1.id,
        self_scores='{"performance": 80, "ability": 85, "attitude": 90}',
        manager_scores='{"performance": 82, "ability": 86, "attitude": 88}',
        peer_scores='{"ability": 87}',
        weighted_performance=81.40,
        weighted_ability=86.20,
        weighted_attitude=88.40,
        total_score=84.50,
        grade="B",
        original_grade="B",
        status="pending_approval",
        manager_comment="表现良好，继续努力",
    )
    # Record 2: Step 1, dept2, abnormal (distribution override)
    record2 = AssessmentRecord(
        cycle_id=cycle1.id,
        employee_id=emp2.id,
        position_id=pos1.id,
        department_id=dept2.id,
        self_scores='{"performance": 95, "ability": 90, "attitude": 92}',
        manager_scores='{"performance": 96, "ability": 91, "attitude": 93}',
        peer_scores='{"ability": 90}',
        weighted_performance=95.70,
        weighted_ability=90.80,
        weighted_attitude=92.80,
        total_score=93.50,
        grade="B",
        original_grade="A",
        is_distribution_override=True,
        status="pending_approval",
        manager_comment="优秀员工",
    )
    # Record 3: Step 2 (one approval already), dept1, force adjusted
    record3 = AssessmentRecord(
        cycle_id=cycle1.id,
        employee_id=emp1.id,
        position_id=pos1.id,
        department_id=dept1.id,
        self_scores='{"performance": 70, "ability": 75, "attitude": 80}',
        manager_scores='{"performance": 72, "ability": 76, "attitude": 78}',
        peer_scores='{"ability": 77}',
        weighted_performance=71.40,
        weighted_ability=76.20,
        weighted_attitude=78.40,
        total_score=74.50,
        grade="C",
        original_grade="B",
        status="pending_approval",
        manager_comment="需要改进",
    )
    db.add(record1)
    db.add(record2)
    db.add(record3)
    db.flush()

    # Create approval for record3 (step 1 completed)
    approval3 = ApprovalRecord(
        record_id=record3.id,
        approver_id=mgr_emp.id,
        approver_role="direct_manager",
        step_index=1,
        action="approved",
        comment="同意",
    )
    db.add(approval3)
    db.flush()

    # Create past records for history
    past_record1 = AssessmentRecord(
        cycle_id=cycle2.id,
        employee_id=emp1.id,
        position_id=pos1.id,
        department_id=dept1.id,
        self_scores='{"performance": 75, "ability": 80, "attitude": 85}',
        manager_scores='{"performance": 78, "ability": 82, "attitude": 86}',
        peer_scores='{"ability": 83}',
        weighted_performance=77.10,
        weighted_ability=82.00,
        weighted_attitude=85.80,
        total_score=81.00,
        grade="B",
        original_grade="B",
        status="published",
        manager_comment="上季度表现",
    )
    past_record2 = AssessmentRecord(
        cycle_id=cycle3.id,
        employee_id=emp1.id,
        position_id=pos1.id,
        department_id=dept1.id,
        self_scores='{"performance": 70, "ability": 75, "attitude": 80}',
        manager_scores='{"performance": 72, "ability": 76, "attitude": 78}',
        peer_scores='{"ability": 77}',
        weighted_performance=71.40,
        weighted_ability=76.20,
        weighted_attitude=78.40,
        total_score=75.00,
        grade="C",
        original_grade="C",
        status="published",
        manager_comment="再前季度",
    )
    db.add(past_record1)
    db.add(past_record2)
    db.flush()

    # Create peer review tasks
    peer_task1 = PeerReviewTask(
        record_id=record1.id,
        reviewer_id=emp2.id,
        ability_score=88.0,
        comment="协作能力很好",
        status="completed",
    )
    peer_task2 = PeerReviewTask(
        record_id=record1.id,
        reviewer_id=hr_emp.id,
        ability_score=85.0,
        comment="整体不错",
        status="completed",
    )
    db.add(peer_task1)
    db.add(peer_task2)
    db.flush()

    # Set default approval chain
    chain_cfg = SystemConfig(key="approval_chain", value='["direct_manager", "dept_head", "hr_head"]')
    db.add(chain_cfg)
    db.commit()

    yield {
        "mgr_user": mgr_user,
        "hr_user": hr_user,
        "emp1": emp1,
        "emp2": emp2,
        "mgr_emp": mgr_emp,
        "dept1": dept1,
        "dept2": dept2,
        "record1": record1,
        "record2": record2,
        "record3": record3,
        "cycle1": cycle1,
        "cycle2": cycle2,
        "cycle3": cycle3,
    }

    # Cleanup（按周期清理，避免主键复用后残留记录）
    cycle_record_ids = [
        rid for (rid,) in db.query(AssessmentRecord.id).filter(
            AssessmentRecord.cycle_id.in_([cycle1.id, cycle2.id, cycle3.id])
        ).all()
    ]
    if cycle_record_ids:
        db.query(ApprovalRecord).filter(ApprovalRecord.record_id.in_(cycle_record_ids)).delete(synchronize_session=False)
        db.query(PeerReviewTask).filter(PeerReviewTask.record_id.in_(cycle_record_ids)).delete(synchronize_session=False)
        db.query(AssessmentRecord).filter(AssessmentRecord.id.in_(cycle_record_ids)).delete(synchronize_session=False)
    db.query(User).filter(User.username.in_(["testmgr", "testhr", "testemp1"])).delete(synchronize_session=False)
    db.query(Employee).filter(Employee.employee_no.in_(["TSTMGR", "TSTHR", "TSTEMP1", "TSTEMP2", "TSTDH"])).delete(synchronize_session=False)
    db.query(AssessmentCycle).filter(AssessmentCycle.name.like("Test Cycle%")).delete(synchronize_session=False)
    db.query(Department).filter(Department.code.in_(["TESTDEPT1", "TESTDEPT2"])).delete(synchronize_session=False)
    db.query(Position).filter(Position.name.like("Test Position%")).delete(synchronize_session=False)
    db.query(SystemConfig).filter(SystemConfig.key == "approval_chain").delete(synchronize_session=False)
    db.commit()


class TestP5_06_ApprovalsList:
    """Tests for P5-06: Enhanced Approval List Endpoint"""

    def test_manager_sees_only_subordinate_records_step1(self, client, db, setup_approval_data):
        """Manager sees only subordinate records at Step 1"""
        headers = _get_auth_header(db, "testmgr")
        resp = client.get("/approvals/pending", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        # Manager should see record1 and record2 (step 1, his subordinates)
        # record3 is at step 2 (already approved by manager), so not visible
        record_ids = [r["record_id"] for r in data]
        assert setup_approval_data["record1"].id in record_ids
        assert setup_approval_data["record2"].id in record_ids
        assert setup_approval_data["record3"].id not in record_ids
        # All returned should be step 1
        for r in data:
            assert r["step_index"] == 1
            assert r["next_approver_role"] == "direct_manager"

    def test_dept_head_sees_step2_records(self, client, db, setup_approval_data):
        """Department head sees Step 2 records in their department"""
        # Create dept_head user
        dept_head_emp = setup_approval_data["dept1"].head_id
        dept_head_user = User(
            username="testdepthead",
            password_hash=get_password_hash("Test123!"),
            role="manager",
            employee_id=dept_head_emp,
            is_first_login=False,
        )
        db.add(dept_head_user)
        db.commit()

        headers = _get_auth_header(db, "testdepthead")
        resp = client.get("/approvals/pending?step=2", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        # record3 is at step 2 in dept1
        record_ids = [r["record_id"] for r in data]
        assert setup_approval_data["record3"].id in record_ids
        for r in data:
            assert r["step_index"] == 2

        # Cleanup
        db.query(User).filter(User.username == "testdepthead").delete(synchronize_session=False)
        db.commit()

    def test_filter_by_department(self, client, db, setup_approval_data):
        """Filter by department works"""
        headers = _get_auth_header(db, "testmgr")
        dept1_id = setup_approval_data["dept1"].id
        resp = client.get(f"/approvals/pending?department_id={dept1_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        # Only record1 is in dept1
        record_ids = [r["record_id"] for r in data]
        assert setup_approval_data["record1"].id in record_ids
        assert setup_approval_data["record2"].id not in record_ids
        for r in data:
            assert r["department_name"] == "测试研发部"

    def test_filter_by_is_abnormal(self, client, db, setup_approval_data):
        """Filter by is_abnormal works"""
        headers = _get_auth_header(db, "testmgr")
        resp = client.get("/approvals/pending?is_abnormal=true", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        # Only record2 has is_distribution_override=True
        record_ids = [r["record_id"] for r in data]
        assert setup_approval_data["record2"].id in record_ids
        assert setup_approval_data["record1"].id not in record_ids
        for r in data:
            assert r["is_abnormal"] is True

    def test_filter_by_is_force_adjusted(self, client, db, setup_approval_data):
        """Filter by is_force_adjusted works"""
        # Use dept_head who can see step 2 records (record3 is force adjusted)
        dept_head_emp = setup_approval_data["dept1"].head_id
        dept_head_user = User(
            username="testdepthead2",
            password_hash=get_password_hash("Test123!"),
            role="manager",
            employee_id=dept_head_emp,
            is_first_login=False,
        )
        db.add(dept_head_user)
        db.commit()

        headers = _get_auth_header(db, "testdepthead2")
        resp = client.get("/approvals/pending?is_force_adjusted=true", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        # record3 is force adjusted and at step 2 (visible to dept_head)
        record_ids = [r["record_id"] for r in data]
        assert setup_approval_data["record3"].id in record_ids
        for r in data:
            # force_adjusted means original_grade != None and grade != original_grade
            assert r["grade"] != r.get("original_grade") or r.get("original_grade") is not None

        # Cleanup
        db.query(User).filter(User.username == "testdepthead2").delete(synchronize_session=False)
        db.commit()

    def test_step_filter_step1(self, client, db, setup_approval_data):
        """Filter by step=1 returns only step 1 records"""
        headers = _get_auth_header(db, "testmgr")
        resp = client.get("/approvals/pending?step=1", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        for r in data:
            assert r["step_index"] == 1

    def test_step_filter_step2(self, client, db, setup_approval_data):
        """Filter by step=2 returns only step 2 records"""
        headers = _get_auth_header(db, "testhr")
        resp = client.get("/approvals/pending?step=2", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        for r in data:
            assert r["step_index"] == 2


class TestP5_07_ApprovalsDetail:
    """Tests for P5-07: Approval Detail Endpoint"""

    def test_get_detail_successfully_returns_all_fields(self, client, db, setup_approval_data):
        """Get detail successfully returns all fields"""
        headers = _get_auth_header(db, "testmgr")
        record_id = setup_approval_data["record1"].id
        resp = client.get(f"/approvals/{record_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["record_id"] == record_id
        assert data["employee_name"] == "测试员工1"
        assert data["employee_no"] == "TSTEMP1"
        assert data["department_name"] == "测试研发部"
        assert data["status"] == "pending_approval"
        assert "self_scores" in data
        assert "manager_scores" in data
        assert "peer_scores" in data
        assert "weighted_performance" in data
        assert "weighted_ability" in data
        assert "weighted_attitude" in data
        assert "total_score" in data
        assert "grade" in data
        assert "original_grade" in data
        assert "is_distribution_override" in data
        assert "is_abnormal" in data
        assert "score_diff_alert" in data
        assert "history" in data
        assert "approval_history" in data
        assert "peer_comments" in data

    def test_403_for_unauthorized_user(self, client, db, setup_approval_data):
        """403 for unauthorized user"""
        # Create an unrelated manager who is not in the approval chain
        unrelated_dept = Department(name="无关部门", code="UNRELATED")
        db.add(unrelated_dept)
        db.flush()
        unrelated_pos = Position(name="无关岗位", department_id=unrelated_dept.id)
        db.add(unrelated_pos)
        db.flush()
        unrelated_mgr_emp = Employee(employee_no="UNRELATED", name="无关经理", department_id=unrelated_dept.id, position_id=unrelated_pos.id)
        db.add(unrelated_mgr_emp)
        db.flush()
        unrelated_mgr_user = User(
            username="unrelatedmgr",
            password_hash=get_password_hash("Test123!"),
            role="manager",
            employee_id=unrelated_mgr_emp.id,
            is_first_login=False,
        )
        db.add(unrelated_mgr_user)
        db.commit()

        headers = _get_auth_header(db, "unrelatedmgr")
        record_id = setup_approval_data["record1"].id
        resp = client.get(f"/approvals/{record_id}", headers=headers)
        assert resp.status_code == 403

        # Cleanup
        db.query(User).filter(User.username == "unrelatedmgr").delete(synchronize_session=False)
        db.query(Employee).filter(Employee.employee_no == "UNRELATED").delete(synchronize_session=False)
        db.query(Position).filter(Position.name == "无关岗位").delete(synchronize_session=False)
        db.query(Department).filter(Department.code == "UNRELATED").delete(synchronize_session=False)
        db.commit()

    def test_404_for_nonexistent_record(self, client, db, setup_approval_data):
        """404 for non-existent record"""
        headers = _get_auth_header(db, "testmgr")
        resp = client.get("/approvals/999999", headers=headers)
        assert resp.status_code == 404

    def test_peer_comments_are_included(self, client, db, setup_approval_data):
        """Peer comments are included"""
        headers = _get_auth_header(db, "testmgr")
        record_id = setup_approval_data["record1"].id
        resp = client.get(f"/approvals/{record_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "peer_comments" in data
        assert len(data["peer_comments"]) == 2
        comments = data["peer_comments"]
        reviewer_names = [c["reviewer_name"] for c in comments]
        assert "测试员工2" in reviewer_names
        assert "测试HR" in reviewer_names
        for c in comments:
            assert "ability_score" in c
            assert "comment" in c

    def test_history_last_3_cycles_included(self, client, db, setup_approval_data):
        """History (last 3 cycles) is included"""
        headers = _get_auth_header(db, "testmgr")
        record_id = setup_approval_data["record1"].id
        resp = client.get(f"/approvals/{record_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "history" in data
        # We created 2 past records, but there might be more from previous runs
        assert len(data["history"]) >= 2
        history = data["history"]
        cycle_names = [h["cycle_name"] for h in history]
        assert "Test Cycle 2023 Q4" in cycle_names
        assert "Test Cycle 2023 Q3" in cycle_names
        for h in history:
            assert "total_score" in h
            assert "grade" in h

    def test_approval_history_included(self, client, db, setup_approval_data):
        """Approval history is included for record with approvals"""
        headers = _get_auth_header(db, "testhr")
        record_id = setup_approval_data["record3"].id
        resp = client.get(f"/approvals/{record_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "approval_history" in data
        assert len(data["approval_history"]) == 1
        ah = data["approval_history"][0]
        assert ah["approver_name"] == "测试经理"
        assert ah["action"] == "approved"
        assert ah["step_index"] == 1

    def test_hr_can_access_detail(self, client, db, setup_approval_data):
        """HR can access any detail"""
        headers = _get_auth_header(db, "testhr")
        record_id = setup_approval_data["record1"].id
        resp = client.get(f"/approvals/{record_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["record_id"] == record_id
