import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.models import Base, ApprovalRecord, PeerReviewer, PeerReviewTask, SystemConfig, OperationLog, AppealRecord, InterviewRecord, ScoreDetail, KpiAdjustment, CycleEmployee, Notification
from sqlalchemy import inspect, JSON, Text


class TestModelImport:
    """验证 P0-07 模型可导入"""

    def test_import_approval_record(self):
        from app.models import ApprovalRecord
        assert ApprovalRecord is not None

    def test_import_peer_reviewer(self):
        from app.models import PeerReviewer
        assert PeerReviewer is not None

    def test_import_peer_review_task(self):
        from app.models import PeerReviewTask
        assert PeerReviewTask is not None

    def test_import_system_config(self):
        from app.models import SystemConfig
        assert SystemConfig is not None

    def test_import_operation_log(self):
        from app.models import OperationLog
        assert OperationLog is not None

    def test_import_appeal_record(self):
        from app.models import AppealRecord
        assert AppealRecord is not None

    def test_import_interview_record(self):
        from app.models import InterviewRecord
        assert InterviewRecord is not None

    def test_import_score_detail(self):
        from app.models import ScoreDetail
        assert ScoreDetail is not None

    def test_import_kpi_adjustment(self):
        from app.models import KpiAdjustment
        assert KpiAdjustment is not None

    def test_import_cycle_employee(self):
        from app.models import CycleEmployee
        assert CycleEmployee is not None

    def test_import_notification(self):
        from app.models import Notification
        assert Notification is not None


class TestAllTablesCreation:
    """验证 Base.metadata.create_all 可创建全部 18 张表"""

    def test_create_all_18_tables(self, tmp_path):
        from sqlalchemy import create_engine

        tmp_db = tmp_path / "test_p0_07.db"
        tmp_url = f"sqlite:///{tmp_db.as_posix()}"
        tmp_engine = create_engine(tmp_url, connect_args={"check_same_thread": False})

        try:
            Base.metadata.create_all(bind=tmp_engine)
        except Exception as e:
            pytest.fail(f"Base.metadata.create_all 抛出异常: {e}")

        inspector = inspect(tmp_engine)
        tables = set(inspector.get_table_names())

        expected_tables = {
            "departments", "positions", "employees", "users",
            "assessment_cycles", "kpi_templates", "assessment_records",
            "score_details", "kpi_adjustments", "approval_records",
            "cycle_employees", "peer_reviewers", "operation_logs",
            "appeal_records", "interview_records", "system_configs",
            "notifications", "peer_review_tasks"
        }

        assert expected_tables.issubset(tables), f"缺少表: {expected_tables - tables}"
        assert len(tables) >= 18, f"表数量不足，期望 >= 18，实际 {len(tables)}"


class TestApprovalRecordModel:
    """验证 ApprovalRecord 模型结构"""

    def test_tablename(self):
        assert ApprovalRecord.__tablename__ == "approval_records"

    def test_columns(self):
        cols = {c.name for c in ApprovalRecord.__table__.columns}
        expected = {"id", "record_id", "approver_id", "approver_role", "step_index", "approval_type", "action", "comment", "created_at"}
        assert expected.issubset(cols)

    def test_record_id_not_nullable(self):
        col = ApprovalRecord.__table__.c.record_id
        assert col.nullable is False

    def test_approver_id_not_nullable(self):
        col = ApprovalRecord.__table__.c.approver_id
        assert col.nullable is False

    def test_step_index_default(self):
        col = ApprovalRecord.__table__.c.step_index
        assert col.default is not None
        assert col.default.arg == 1

    def test_approval_type_default(self):
        col = ApprovalRecord.__table__.c.approval_type
        assert col.default is not None
        assert col.default.arg == "normal"

    def test_record_id_fk(self):
        col = ApprovalRecord.__table__.c.record_id
        fks = list(col.foreign_keys)
        assert any("assessment_records.id" in str(fk) for fk in fks)

    def test_approver_id_fk(self):
        col = ApprovalRecord.__table__.c.approver_id
        fks = list(col.foreign_keys)
        assert any("employees.id" in str(fk) for fk in fks)


class TestPeerReviewerModel:
    """验证 PeerReviewer 模型结构"""

    def test_tablename(self):
        assert PeerReviewer.__tablename__ == "peer_reviewers"

    def test_columns(self):
        cols = {c.name for c in PeerReviewer.__table__.columns}
        expected = {"id", "cycle_id", "employee_id", "reviewer_id", "reviewer_department_id", "status"}
        assert expected.issubset(cols)

    def test_unique_constraint(self):
        constraints = [c.name for c in PeerReviewer.__table__.constraints if hasattr(c, "name")]
        assert "_peer_reviewer_uc" in constraints

    def test_cycle_id_fk(self):
        col = PeerReviewer.__table__.c.cycle_id
        fks = list(col.foreign_keys)
        assert any("assessment_cycles.id" in str(fk) for fk in fks)

    def test_reviewer_id_fk(self):
        col = PeerReviewer.__table__.c.reviewer_id
        fks = list(col.foreign_keys)
        assert any("employees.id" in str(fk) for fk in fks)


class TestPeerReviewTaskModel:
    """验证 PeerReviewTask 模型结构"""

    def test_tablename(self):
        assert PeerReviewTask.__tablename__ == "peer_review_tasks"

    def test_columns(self):
        cols = {c.name for c in PeerReviewTask.__table__.columns}
        expected = {"id", "record_id", "reviewer_id", "ability_score", "comment", "status", "submitted_at", "created_at"}
        assert expected.issubset(cols)

    def test_record_id_not_nullable(self):
        col = PeerReviewTask.__table__.c.record_id
        assert col.nullable is False

    def test_reviewer_id_not_nullable(self):
        col = PeerReviewTask.__table__.c.reviewer_id
        assert col.nullable is False

    def test_status_default(self):
        col = PeerReviewTask.__table__.c.status
        assert col.default is not None
        assert col.default.arg == "pending"

    def test_record_id_fk(self):
        col = PeerReviewTask.__table__.c.record_id
        fks = list(col.foreign_keys)
        assert any("assessment_records.id" in str(fk) for fk in fks)

    def test_reviewer_id_fk(self):
        col = PeerReviewTask.__table__.c.reviewer_id
        fks = list(col.foreign_keys)
        assert any("employees.id" in str(fk) for fk in fks)


class TestSystemConfigModel:
    """验证 SystemConfig 模型结构"""

    def test_tablename(self):
        assert SystemConfig.__tablename__ == "system_configs"

    def test_columns(self):
        cols = {c.name for c in SystemConfig.__table__.columns}
        expected = {"id", "key", "value", "updated_at"}
        assert expected.issubset(cols)

    def test_key_unique(self):
        col = SystemConfig.__table__.c.key
        assert col.unique is True
        assert col.nullable is False

    def test_value_not_nullable(self):
        col = SystemConfig.__table__.c.value
        assert col.nullable is False


class TestOperationLogModel:
    """验证 OperationLog 模型结构"""

    def test_tablename(self):
        assert OperationLog.__tablename__ == "operation_logs"

    def test_columns(self):
        cols = {c.name for c in OperationLog.__table__.columns}
        expected = {"id", "user_id", "action", "target_type", "target_id", "old_value", "new_value", "ip_address", "created_at"}
        assert expected.issubset(cols)

    def test_user_id_not_nullable(self):
        col = OperationLog.__table__.c.user_id
        assert col.nullable is False

    def test_action_not_nullable(self):
        col = OperationLog.__table__.c.action
        assert col.nullable is False

    def test_user_id_fk(self):
        col = OperationLog.__table__.c.user_id
        fks = list(col.foreign_keys)
        assert any("users.id" in str(fk) for fk in fks)


class TestCycleEmployeeModel:
    """验证 CycleEmployee 模型结构"""

    def test_tablename(self):
        assert CycleEmployee.__tablename__ == "cycle_employees"

    def test_unique_constraint(self):
        constraints = [c.name for c in CycleEmployee.__table__.constraints if hasattr(c, "name")]
        assert "_cycle_employee_uc" in constraints

    def test_cycle_id_fk(self):
        col = CycleEmployee.__table__.c.cycle_id
        fks = list(col.foreign_keys)
        assert any("assessment_cycles.id" in str(fk) for fk in fks)

    def test_employee_id_fk(self):
        col = CycleEmployee.__table__.c.employee_id
        fks = list(col.foreign_keys)
        assert any("employees.id" in str(fk) for fk in fks)


class TestNotificationModel:
    """验证 Notification 模型结构"""

    def test_tablename(self):
        assert Notification.__tablename__ == "notifications"

    def test_columns(self):
        cols = {c.name for c in Notification.__table__.columns}
        expected = {"id", "user_id", "title", "content", "type", "is_read", "created_at"}
        assert expected.issubset(cols)

    def test_user_id_not_nullable(self):
        col = Notification.__table__.c.user_id
        assert col.nullable is False

    def test_title_not_nullable(self):
        col = Notification.__table__.c.title
        assert col.nullable is False

    def test_is_read_default(self):
        col = Notification.__table__.c.is_read
        assert col.default is not None
        assert col.default.arg is False

    def test_user_id_fk(self):
        col = Notification.__table__.c.user_id
        fks = list(col.foreign_keys)
        assert any("users.id" in str(fk) for fk in fks)


class TestCrudOperations:
    """验证基础 CRUD 可正常工作"""

    def test_create_system_config(self, tmp_path):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        tmp_db = tmp_path / "test_crud_p0_07.db"
        tmp_url = f"sqlite:///{tmp_db.as_posix()}"
        tmp_engine = create_engine(tmp_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=tmp_engine)
        Session = sessionmaker(bind=tmp_engine)
        session = Session()

        config = SystemConfig(key="grade_rules", value='{"A": {"min": 90}}')
        session.add(config)
        session.commit()
        session.refresh(config)

        assert config.id is not None
        assert config.key == "grade_rules"
        session.close()

    def test_create_operation_log(self, tmp_path):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        tmp_db = tmp_path / "test_crud_p0_07_2.db"
        tmp_url = f"sqlite:///{tmp_db.as_posix()}"
        tmp_engine = create_engine(tmp_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=tmp_engine)
        Session = sessionmaker(bind=tmp_engine)
        session = Session()

        log = OperationLog(user_id=1, action="create_cycle", target_type="cycle", target_id=1)
        session.add(log)
        session.commit()
        session.refresh(log)

        assert log.id is not None
        assert log.action == "create_cycle"
        session.close()

    def test_create_peer_review_task(self, tmp_path):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        tmp_db = tmp_path / "test_crud_p0_07_3.db"
        tmp_url = f"sqlite:///{tmp_db.as_posix()}"
        tmp_engine = create_engine(tmp_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=tmp_engine)
        Session = sessionmaker(bind=tmp_engine)
        session = Session()

        task = PeerReviewTask(record_id=1, reviewer_id=2)
        session.add(task)
        session.commit()
        session.refresh(task)

        assert task.id is not None
        assert task.status == "pending"
        session.close()

    def test_create_notification(self, tmp_path):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        tmp_db = tmp_path / "test_crud_p0_07_4.db"
        tmp_url = f"sqlite:///{tmp_db.as_posix()}"
        tmp_engine = create_engine(tmp_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=tmp_engine)
        Session = sessionmaker(bind=tmp_engine)
        session = Session()

        notif = Notification(user_id=1, title="考核已启动", content="您有新的考核任务")
        session.add(notif)
        session.commit()
        session.refresh(notif)

        assert notif.id is not None
        assert notif.is_read is False
        assert notif.title == "考核已启动"
        session.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
