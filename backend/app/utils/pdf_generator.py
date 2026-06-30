from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from sqlalchemy.orm import Session

from app.models import AssessmentRecord, Employee, Department, Position, AssessmentCycle


def generate_performance_pdf(record_id: int, db: Session) -> bytes:
    """Generate a PDF performance archive for the given assessment record."""
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        return b""

    emp = db.query(Employee).filter(Employee.id == record.employee_id).first()
    dept = db.query(Department).filter(Department.id == record.department_id).first()
    pos = db.query(Position).filter(Position.id == record.position_id).first()
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == record.cycle_id).first()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=2 * cm, leftMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=1,  # center
        spaceAfter=20,
    )
    heading_style = ParagraphStyle(
        'Heading2',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=10,
    )
    normal_style = styles['Normal']

    story = []

    # Title
    story.append(Paragraph("绩效考核档案", title_style))
    story.append(Spacer(1, 0.5 * cm))

    # Basic Info
    story.append(Paragraph("基本信息", heading_style))
    info_data = [
        ["员工姓名", emp.name if emp else "", "工号", emp.employee_no if emp else ""],
        ["部门", dept.name if dept else "", "岗位", pos.name if pos else ""],
        ["考核周期", cycle.name if cycle else "", "考核状态", record.status or ""],
    ]
    info_table = Table(info_data, colWidths=[4 * cm, 4 * cm, 4 * cm, 4 * cm])
    info_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('BACKGROUND', (2, 0), (2, -1), colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5 * cm))

    # Scores
    story.append(Paragraph("考核得分", heading_style))
    score_data = [
        ["总分", str(record.total_score) if record.total_score else "-"],
        ["绩效等级", record.grade or "-"],
        ["加权业绩分", str(record.weighted_performance) if record.weighted_performance else "-"],
        ["加权能力分", str(record.weighted_ability) if record.weighted_ability else "-"],
        ["加权态度分", str(record.weighted_attitude) if record.weighted_attitude else "-"],
    ]
    score_table = Table(score_data, colWidths=[6 * cm, 10 * cm])
    score_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.5 * cm))

    # Comments
    if record.manager_comment:
        story.append(Paragraph("上级评语", heading_style))
        story.append(Paragraph(record.manager_comment, normal_style))
        story.append(Spacer(1, 0.5 * cm))

    # Footer
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("本档案由绩效考核评分系统自动生成，仅供内部使用。", normal_style))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
