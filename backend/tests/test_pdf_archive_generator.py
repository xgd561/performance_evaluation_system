import os
import pytest
from datetime import date
from app.models import AssessmentCycle, AssessmentRecord, Employee, Department, Position
from app.services.pdf_archive_generator import generate_archive_pdf


@pytest.fixture
def pdf_test_data(db_session):
    """创建 PDF 生成测试所需的基础数据"""
    dept = Department(name="PDF测试部", code="PDF_TEST")
    db_session.add(dept)
    db_session.flush()

    pos = Position(name="PDF测试岗位", department_id=dept.id)
    db_session.add(pos)
    db_session.flush()

    emp = Employee(employee_no="PDF001", name="PDF测试员工", department_id=dept.id, position_id=pos.id)
    db_session.add(emp)
    db_session.flush()

    cycle = AssessmentCycle(
        name="PDF测试周期",
        type="annual",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="published",
        is_locked=False,
    )
    db_session.add(cycle)
    db_session.flush()

    record = AssessmentRecord(
        cycle_id=cycle.id,
        employee_id=emp.id,
        position_id=pos.id,
        department_id=dept.id,
        total_score=88.5,
        grade="B",
        status="published",
        is_locked=False,
        self_scores={"performance": 85, "ability": 80, "attitude": 90},
        manager_scores={"performance": 88, "ability": 85, "attitude": 92},
        peer_scores={"performance": 87, "ability": 82, "attitude": 91},
        weighted_performance=86.5,
        weighted_ability=83.0,
        weighted_attitude=91.0,
        manager_comment="工作表现良好，建议继续保持。",
    )
    db_session.add(record)
    db_session.commit()

    return {"record": record, "cycle": cycle, "emp": emp, "dept": dept, "pos": pos}


class TestPdfArchiveGenerator:
    """P6-11: PDF 归档生成器服务测试"""

    def test_generate_pdf_success(self, db_session, pdf_test_data):
        """成功生成 PDF 文件并返回正确路径"""
        record = pdf_test_data["record"]
        output_dir = os.path.join("test_uploads", "archives", str(record.cycle_id))

        path = generate_archive_pdf(record.id, db_session, output_dir=output_dir)

        assert path != ""
        assert os.path.exists(path)
        assert path.endswith(f"{pdf_test_data['emp'].employee_no}_archive.pdf")

    def test_generate_pdf_returns_empty_for_nonexistent_record(self, db_session):
        """记录不存在时应返回空字符串"""
        path = generate_archive_pdf(99999, db_session)
        assert path == ""

    def test_generate_pdf_creates_output_dir(self, db_session, pdf_test_data):
        """输出目录不存在时应自动创建"""
        import uuid
        record = pdf_test_data["record"]
        output_dir = os.path.join("test_uploads", f"archives_new_{uuid.uuid4().hex}", str(record.cycle_id))

        assert not os.path.exists(output_dir)

        path = generate_archive_pdf(record.id, db_session, output_dir=output_dir)

        assert os.path.exists(output_dir)
        assert os.path.exists(path)

    def test_generate_pdf_with_distribution_override(self, db_session, pdf_test_data):
        """强制调整记录应正确反映在 PDF 中"""
        record = pdf_test_data["record"]
        record.is_distribution_override = True
        record.original_grade = "C"
        record.grade = "B"
        record.override_reason = "部门比例调整"
        db_session.commit()

        output_dir = os.path.join("test_uploads", "archives_override", str(record.cycle_id))
        path = generate_archive_pdf(record.id, db_session, output_dir=output_dir)

        assert os.path.exists(path)

    def test_generate_pdf_with_interview_record(self, db_session, pdf_test_data):
        """包含面谈记录时应正确生成 PDF"""
        record = pdf_test_data["record"]
        record.interview_record = {
            "interview_time": "2026-06-15 14:00",
            "location": "会议室A",
            "interviewer_name": "李经理",
            "content": "讨论了Q2的工作表现",
            "improvement_plan": "提升技术深度",
        }
        db_session.commit()

        output_dir = os.path.join("test_uploads", "archives_interview", str(record.cycle_id))
        path = generate_archive_pdf(record.id, db_session, output_dir=output_dir)

        assert os.path.exists(path)

    def test_generate_pdf_with_appeal_record(self, db_session, pdf_test_data):
        """包含申诉记录时应正确生成 PDF"""
        record = pdf_test_data["record"]
        record.appeal_record = {
            "appeal_id": 1,
            "reason": "评分不公",
            "detail": "我认为我的业绩评分应该更高",
            "status": "resolved",
            "created_at": "2026-06-10",
        }
        db_session.commit()

        output_dir = os.path.join("test_uploads", "archives_appeal", str(record.cycle_id))
        path = generate_archive_pdf(record.id, db_session, output_dir=output_dir)

        assert os.path.exists(path)
