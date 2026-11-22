import os
from datetime import datetime
from io import BytesIO
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from sqlalchemy.orm import Session

from app.models import AssessmentRecord, Employee, Department, Position, AssessmentCycle

# 归档目录固定在 backend/uploads，避免随进程 CWD 漂移导致文件散落
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")


def _ensure_fonts():
    """尝试注册中文字体，用于 PDF 中显示中文"""
    try:
        # 常见 Linux 中文字体
        pdfmetrics.registerFont(TTFont('SimSun', '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'))
        return 'SimSun'
    except Exception:
        try:
            pdfmetrics.registerFont(TTFont('SimSun', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
            return 'SimSun'
        except Exception:
            return 'Helvetica'


FONT_NAME = _ensure_fonts()


def _safe_json(value):
    """安全解析 JSON 字段"""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        import json
        try:
            return json.loads(value)
        except Exception:
            return {}
    return {}


def generate_archive_pdf(record_id: int, db: Session, output_dir: Optional[str] = None) -> str:
    """
    生成完整的绩效考核档案 PDF，并保存到文件系统。
    返回生成的文件路径。
    """
    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        return ""

    emp = db.query(Employee).filter(Employee.id == record.employee_id).first()
    dept = db.query(Department).filter(Department.id == record.department_id).first()
    pos = db.query(Position).filter(Position.id == record.position_id).first()
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == record.cycle_id).first()

    # 准备输出目录
    if output_dir is None:
        output_dir = os.path.join(UPLOAD_DIR, "archives", str(record.cycle_id))
    os.makedirs(output_dir, exist_ok=True)

    filename = f"{emp.employee_no if emp else 'unknown'}_archive.pdf"
    filepath = os.path.join(output_dir, filename)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=20,
        alignment=1,  # center
        spaceAfter=30,
        fontName=FONT_NAME,
    )
    heading_style = ParagraphStyle(
        'Heading2',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=10,
        fontName=FONT_NAME,
    )
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10,
        fontName=FONT_NAME,
    )
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=10,
        fontName=FONT_NAME,
        textColor=colors.grey,
    )

    story = []

    # ==================== 封面 ====================
    story.append(Spacer(1, 4 * cm))
    story.append(Paragraph("绩效考核档案", title_style))
    story.append(Spacer(1, 1 * cm))

    cover_data = [
        [Paragraph("员工姓名", label_style), Paragraph(emp.name if emp else "-", normal_style)],
        [Paragraph("工　　号", label_style), Paragraph(emp.employee_no if emp else "-", normal_style)],
        [Paragraph("部　　门", label_style), Paragraph(dept.name if dept else "-", normal_style)],
        [Paragraph("岗　　位", label_style), Paragraph(pos.name if pos else "-", normal_style)],
        [Paragraph("考核周期", label_style), Paragraph(cycle.name if cycle else "-", normal_style)],
        [Paragraph("周期类型", label_style), Paragraph(cycle.type if cycle else "-", normal_style)],
        [Paragraph("起止日期", label_style), Paragraph(
            f"{cycle.start_date} 至 {cycle.end_date}" if cycle else "-", normal_style)],
        [Paragraph("生成时间", label_style), Paragraph(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), normal_style)],
    ]
    cover_table = Table(cover_data, colWidths=[4 * cm, 10 * cm])
    cover_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(cover_table)
    story.append(PageBreak())

    # ==================== 基本信息 ====================
    story.append(Paragraph("一、基本信息", heading_style))
    info_data = [
        ["员工姓名", emp.name if emp else "", "工号", emp.employee_no if emp else ""],
        ["部门", dept.name if dept else "", "岗位", pos.name if pos else ""],
        ["考核周期", cycle.name if cycle else "", "考核状态", record.status or ""],
        ["总　　分", str(record.total_score) if record.total_score else "-", "等　　级", record.grade or "-"],
    ]
    info_table = Table(info_data, colWidths=[4 * cm, 4 * cm, 4 * cm, 4 * cm])
    info_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('BACKGROUND', (2, 0), (2, -1), colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5 * cm))

    # ==================== 评分详情 ====================
    story.append(Paragraph("二、评分详情", heading_style))
    self_scores = _safe_json(record.self_scores)
    manager_scores = _safe_json(record.manager_scores)
    peer_scores = _safe_json(record.peer_scores)

    score_data = [
        ["维度", "自评分", "上级评分", "协作评分"],
    ]
    for dim in ["performance", "ability", "attitude"]:
        dim_label = {"performance": "业绩", "ability": "能力", "attitude": "态度"}.get(dim, dim)
        score_data.append([
            dim_label,
            str(self_scores.get(dim, "-")) if self_scores else "-",
            str(manager_scores.get(dim, "-")) if manager_scores else "-",
            str(peer_scores.get(dim, "-")) if peer_scores else "-",
        ])

    score_table = Table(score_data, colWidths=[4 * cm, 4 * cm, 4 * cm, 4 * cm])
    score_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.5 * cm))

    # ==================== 加权结果 ====================
    story.append(Paragraph("三、加权结果", heading_style))
    result_data = [
        ["加权业绩分", str(record.weighted_performance) if record.weighted_performance else "-"],
        ["加权能力分", str(record.weighted_ability) if record.weighted_ability else "-"],
        ["加权态度分", str(record.weighted_attitude) if record.weighted_attitude else "-"],
        ["总　　分", str(record.total_score) if record.total_score else "-"],
        ["绩效等级", record.grade or "-"],
    ]
    result_table = Table(result_data, colWidths=[6 * cm, 10 * cm])
    result_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    story.append(result_table)
    story.append(Spacer(1, 0.5 * cm))

    # ==================== 强制调整记录 ====================
    story.append(Paragraph("四、强制调整记录", heading_style))
    if record.is_distribution_override:
        adjust_data = [
            ["是否调整", "是"],
            ["原始等级", record.original_grade or "-"],
            ["调整后等级", record.grade or "-"],
            ["调整原因", record.override_reason or "-"],
        ]
    else:
        adjust_data = [
            ["是否调整", "否"],
            ["原始等级", record.original_grade or record.grade or "-"],
            ["调整后等级", record.grade or "-"],
            ["调整原因", "-"],
        ]
    adjust_table = Table(adjust_data, colWidths=[6 * cm, 10 * cm])
    adjust_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    story.append(adjust_table)
    story.append(Spacer(1, 0.5 * cm))

    # ==================== 面谈记录 ====================
    story.append(Paragraph("五、绩效面谈记录", heading_style))
    interview = _safe_json(record.interview_record)
    if interview:
        interview_data = [
            ["面谈时间", interview.get("interview_time", "-")],
            ["地　　点", interview.get("location", "-")],
            ["面谈人", interview.get("interviewer_name", "-")],
            ["沟通内容", interview.get("content", "-")],
            ["改进计划", interview.get("improvement_plan", "-")],
        ]
    else:
        interview_data = [["面谈记录", "暂无"]]
    interview_table = Table(interview_data, colWidths=[4 * cm, 12 * cm])
    interview_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    story.append(interview_table)
    story.append(Spacer(1, 0.5 * cm))

    # ==================== 申诉记录 ====================
    story.append(Paragraph("六、申诉记录", heading_style))
    appeal = _safe_json(record.appeal_record)
    if appeal:
        appeal_data = [
            ["申诉编号", str(appeal.get("appeal_id", "-"))],
            ["申诉原因", appeal.get("reason", "-")],
            ["详细说明", appeal.get("detail", "-")],
            ["处理状态", appeal.get("status", "-")],
            ["创建时间", appeal.get("created_at", "-")],
        ]
    else:
        appeal_data = [["申诉记录", "暂无"]]
    appeal_table = Table(appeal_data, colWidths=[4 * cm, 12 * cm])
    appeal_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    story.append(appeal_table)
    story.append(Spacer(1, 0.5 * cm))

    # ==================== 上级评语 ====================
    if record.manager_comment:
        story.append(Paragraph("七、上级评语", heading_style))
        story.append(Paragraph(record.manager_comment, normal_style))
        story.append(Spacer(1, 0.5 * cm))

    # ==================== 页脚声明 ====================
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("本档案由绩效考核评分系统自动生成，仅供内部使用。", normal_style))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    with open(filepath, 'wb') as f:
        f.write(pdf_bytes)

    return filepath
