import os
import sys
import pytest
from datetime import datetime, date
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.database import engine, init_db, SessionLocal
from app.models import Base, AssessmentCycle, AssessmentRecord, KpiTemplate
from sqlalchemy import inspect, JSON


class TestModelImport:
    """验证 P0-06 模型可导入"""

    def test_import_assessment_cycle(self):
        from app.models import AssessmentCycle
        assert AssessmentCycle is not None

    def test_import_assessment_record(self):
        from app.models import AssessmentRecord
        assert AssessmentRecord is not None

    def test_import_kpi_template(self):
        from app.models import KpiTemplate
        assert KpiTemplate is not None


class TestTableCreation:
    """验证 Base.metadata.create_all 可创建表"""

    def test_create_all_tables(self, tmp_path):
        from sqlalchemy import create_engine

        tmp_db = tmp_path / "test_p0_06.db"
        tmp_url = f"sqlite:///{tmp_db.as_posix()}"
        tmp_engine = create_engine(tmp_url, connect_args={"check_same_thread": False})

        try:
            Base.metadata.create_all(bind=tmp_engine)
        except Exception as e:
            pytest.fail(f"Base.metadata.create_all 抛出异常: {e}")

        inspector = inspect(tmp_engine)
        tables = inspector.get_table_names()
        assert "assessment_cycles" in tables
        assert "assessment_records" in tables
        assert "kpi_templates" in tables


class TestAssessmentCycleModel:
    """验证 AssessmentCycle 模型结构"""

    def test_tablename(self):
        assert AssessmentCycle.__tablename__ == "assessment_cycles"

    def test_columns(self):
        cols = {c.name for c in AssessmentCycle.__table__.columns}
        expected = {
            "id", "name", "type", "start_date", "end_date",
            "self_due_date", "manager_due_date", "peer_due_date",
            "status", "dimension_weights", "reviewer_weights",
            "grade_rules", "is_distribution_enabled", "small_dept_exemption",
            "peer_review_enabled", "approval_chain_config", "is_locked",
            "created_at", "updated_at"
        }
        assert expected.issubset(cols)

    def test_primary_key(self):
        pk = [c.name for c in AssessmentCycle.__table__.primary_key]
        assert "id" in pk

    def test_name_not_nullable(self):
        col = AssessmentCycle.__table__.c.name
        assert col.nullable is False

    def test_type_not_nullable(self):
        col = AssessmentCycle.__table__.c.type
        assert col.nullable is False

    def test_start_date_not_nullable(self):
        col = AssessmentCycle.__table__.c.start_date
        assert col.nullable is False

    def test_end_date_not_nullable(self):
        col = AssessmentCycle.__table__.c.end_date
        assert col.nullable is False

    def test_json_fields_use_json_type(self):
        """断言 JSON 字段使用 SQLAlchemy JSON 类型"""
        assert isinstance(AssessmentCycle.__table__.c.dimension_weights.type, JSON)
        assert isinstance(AssessmentCycle.__table__.c.reviewer_weights.type, JSON)
        assert isinstance(AssessmentCycle.__table__.c.grade_rules.type, JSON)
        assert isinstance(AssessmentCycle.__table__.c.approval_chain_config.type, JSON)

    def test_json_defaults(self):
        """断言 JSON 字段默认值为 Python dict"""
        dw = AssessmentCycle.__table__.c.dimension_weights
        assert dw.default is not None
        assert dw.default.arg == {"performance": 0.6, "ability": 0.2, "attitude": 0.2}

    def test_status_default(self):
        col = AssessmentCycle.__table__.c.status
        assert col.default is not None
        assert col.default.arg == "not_started"


class TestKpiTemplateModel:
    """验证 KpiTemplate 模型结构"""

    def test_tablename(self):
        assert KpiTemplate.__tablename__ == "kpi_templates"

    def test_columns(self):
        cols = {c.name for c in KpiTemplate.__table__.columns}
        expected = {"id", "position_id", "name", "weight", "target_value", "scoring_method", "description", "is_active", "created_at"}
        assert expected.issubset(cols)

    def test_position_id_not_nullable(self):
        col = KpiTemplate.__table__.c.position_id
        assert col.nullable is False

    def test_name_not_nullable(self):
        col = KpiTemplate.__table__.c.name
        assert col.nullable is False

    def test_weight_not_nullable(self):
        col = KpiTemplate.__table__.c.weight
        assert col.nullable is False

    def test_position_id_fk(self):
        col = KpiTemplate.__table__.c.position_id
        fks = list(col.foreign_keys)
        assert any("positions.id" in str(fk) for fk in fks)

    def test_scoring_method_default(self):
        col = KpiTemplate.__table__.c.scoring_method
        assert col.default is not None
        assert col.default.arg == "percentage"

    def test_relationships(self):
        assert hasattr(KpiTemplate, "position")


class TestAssessmentRecordModel:
    """验证 AssessmentRecord 模型结构"""

    def test_tablename(self):
        assert AssessmentRecord.__tablename__ == "assessment_records"

    def test_columns(self):
        cols = {c.name for c in AssessmentRecord.__table__.columns}
        expected = {
            "id", "cycle_id", "employee_id", "position_id", "department_id",
            "kpi_snapshot", "self_scores", "manager_scores", "peer_scores",
            "weighted_performance", "weighted_ability", "weighted_attitude",
            "total_score", "grade", "original_grade", "is_distribution_override",
            "override_reason", "manager_comment", "manager_draft_scores",
            "self_draft_scores", "peer_draft_scores", "interview_record",
            "appeal_record", "status", "created_at", "updated_at"
        }
        assert expected.issubset(cols)

    def test_cycle_id_not_nullable(self):
        col = AssessmentRecord.__table__.c.cycle_id
        assert col.nullable is False

    def test_employee_id_not_nullable(self):
        col = AssessmentRecord.__table__.c.employee_id
        assert col.nullable is False

    def test_json_fields_use_json_type(self):
        """断言 JSON 字段使用 SQLAlchemy JSON 类型"""
        assert isinstance(AssessmentRecord.__table__.c.kpi_snapshot.type, JSON)
        assert isinstance(AssessmentRecord.__table__.c.self_scores.type, JSON)
        assert isinstance(AssessmentRecord.__table__.c.manager_scores.type, JSON)
        assert isinstance(AssessmentRecord.__table__.c.peer_scores.type, JSON)
        assert isinstance(AssessmentRecord.__table__.c.manager_draft_scores.type, JSON)
        assert isinstance(AssessmentRecord.__table__.c.self_draft_scores.type, JSON)
        assert isinstance(AssessmentRecord.__table__.c.peer_draft_scores.type, JSON)
        assert isinstance(AssessmentRecord.__table__.c.interview_record.type, JSON)
        assert isinstance(AssessmentRecord.__table__.c.appeal_record.type, JSON)

    def test_status_default(self):
        col = AssessmentRecord.__table__.c.status
        assert col.default is not None
        assert col.default.arg == "pending_self"

    def test_cycle_id_fk(self):
        col = AssessmentRecord.__table__.c.cycle_id
        fks = list(col.foreign_keys)
        assert any("assessment_cycles.id" in str(fk) for fk in fks)

    def test_employee_id_fk(self):
        col = AssessmentRecord.__table__.c.employee_id
        fks = list(col.foreign_keys)
        assert any("employees.id" in str(fk) for fk in fks)

    def test_position_id_fk(self):
        col = AssessmentRecord.__table__.c.position_id
        fks = list(col.foreign_keys)
        assert any("positions.id" in str(fk) for fk in fks)

    def test_department_id_fk(self):
        col = AssessmentRecord.__table__.c.department_id
        fks = list(col.foreign_keys)
        assert any("departments.id" in str(fk) for fk in fks)


class TestCrudOperations:
    """验证基础 CRUD 可正常工作"""

    def test_create_assessment_cycle(self, tmp_path):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        tmp_db = tmp_path / "test_crud_p0_06.db"
        tmp_url = f"sqlite:///{tmp_db.as_posix()}"
        tmp_engine = create_engine(tmp_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=tmp_engine)
        Session = sessionmaker(bind=tmp_engine)
        session = Session()

        cycle = AssessmentCycle(
            name="2026Q1",
            type="quarterly",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            dimension_weights={"performance": 0.5, "ability": 0.3, "attitude": 0.2}
        )
        session.add(cycle)
        session.commit()
        session.refresh(cycle)

        assert cycle.id is not None
        assert cycle.name == "2026Q1"
        assert cycle.dimension_weights == {"performance": 0.5, "ability": 0.3, "attitude": 0.2}
        session.close()

    def test_create_kpi_template(self, tmp_path):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        tmp_db = tmp_path / "test_crud_p0_06_2.db"
        tmp_url = f"sqlite:///{tmp_db.as_posix()}"
        tmp_engine = create_engine(tmp_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=tmp_engine)
        Session = sessionmaker(bind=tmp_engine)
        session = Session()

        tpl = KpiTemplate(position_id=1, name="销售额", weight=Decimal("30.00"))
        session.add(tpl)
        session.commit()
        session.refresh(tpl)

        assert tpl.id is not None
        assert tpl.name == "销售额"
        assert tpl.weight == Decimal("30.00")
        session.close()

    def test_create_assessment_record(self, tmp_path):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        tmp_db = tmp_path / "test_crud_p0_06_3.db"
        tmp_url = f"sqlite:///{tmp_db.as_posix()}"
        tmp_engine = create_engine(tmp_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=tmp_engine)
        Session = sessionmaker(bind=tmp_engine)
        session = Session()

        record = AssessmentRecord(
            cycle_id=1,
            employee_id=1,
            self_scores={"performance": 82, "ability": 84, "attitude": 88}
        )
        session.add(record)
        session.commit()
        session.refresh(record)

        assert record.id is not None
        assert record.self_scores == {"performance": 82, "ability": 84, "attitude": 88}
        assert record.status == "pending_self"
        session.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
