from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from collections import Counter
import json

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models import User, AssessmentCycle, AssessmentRecord, Employee, Department
from app.routers.employees import _is_in_subordinate_chain, get_all_dept_ids
from fastapi.responses import StreamingResponse
from app.utils.pdf_generator import generate_performance_pdf
from io import BytesIO

from app.utils.json_columns import load_json

router = APIRouter()


@router.get("/cycle/{cycle_id}/distribution")
def get_distribution(
    cycle_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr", "manager")),
):
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核周期不存在")

    records = db.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == cycle_id).all()

    # 数据隔离：manager 可查看自己下属及本部门及子部门的记录
    current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if user.role == "manager" and current_employee:
        subordinate_ids = db.query(Employee.id).filter(
            Employee.manager_id == current_employee.id
        ).all()
        subordinate_ids = [sid[0] for sid in subordinate_ids]
        dept_ids = get_all_dept_ids(db, current_employee.department_id)
        records = [
            r for r in records
            if r.employee_id in subordinate_ids or r.department_id in dept_ids
        ] if (subordinate_ids or dept_ids) else []

    # Group by department
    dept_stats = {}
    for r in records:
        dept_id = r.department_id or 0
        if dept_id not in dept_stats:
            dept = db.query(Department).filter(Department.id == dept_id).first()
            dept_stats[dept_id] = {
                "department_name": dept.name if dept else "未分配",
                "total": 0,
                "grades": Counter(),
                "avg_score": 0,
                "scores": [],
            }
        dept_stats[dept_id]["total"] += 1
        dept_stats[dept_id]["grades"][r.grade or "未评级"] += 1
        if r.total_score:
            dept_stats[dept_id]["scores"].append(float(r.total_score))

    for d in dept_stats.values():
        if d["scores"]:
            d["avg_score"] = round(sum(d["scores"]) / len(d["scores"]), 1)
        del d["scores"]

    overall_grades = Counter(r.grade or "未评级" for r in records)

    return {
        "cycle_id": cycle_id,
        "cycle_name": cycle.name,
        "total_records": len(records),
        "overall_distribution": dict(overall_grades),
        "department_stats": [
            {
                "department_id": k,
                "department_name": v["department_name"],
                "total": v["total"],
                "grades": dict(v["grades"]),
                "avg_score": v["avg_score"],
            }
            for k, v in dept_stats.items()
        ],
    }


@router.get("/cycle/{cycle_id}/export")
def export_cycle_report(
    cycle_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr", "executive")),
):
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核周期不存在")

    records = db.query(AssessmentRecord).filter(AssessmentRecord.cycle_id == cycle_id).all()

    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "考核结果"

    headers = ["工号", "姓名", "部门", "总分", "等级", "原始等级", "业绩分", "能力分", "态度分", "状态", "是否特批"]
    ws.append(headers)

    # Style header row
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin")
    )

    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    for r in records:
        emp = db.query(Employee).filter(Employee.id == r.employee_id).first()
        dept = db.query(Department).filter(Department.id == r.department_id).first()
        ws.append([
            emp.employee_no if emp else "",
            emp.name if emp else "",
            dept.name if dept else "",
            str(r.total_score) if r.total_score else "",
            r.grade or "",
            r.original_grade or "",
            str(r.weighted_performance) if r.weighted_performance else "",
            str(r.weighted_ability) if r.weighted_ability else "",
            str(r.weighted_attitude) if r.weighted_attitude else "",
            r.status or "",
            "是" if r.is_distribution_override else "否",
        ])

    # Apply borders and alignment to all cells
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=len(headers)):
        for cell in row:
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center", vertical="center")

    # Auto-adjust column widths
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except Exception:
                pass
        adjusted_width = min(max_length + 2, 30)
        ws.column_dimensions[column].width = adjusted_width

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    from urllib.parse import quote
    filename = f"{cycle.name}_考核结果.xlsx"
    filename_encoded = quote(filename)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename_encoded}"
        },
    )


@router.get("/cycle/{cycle_id}/distribution-adjustments")
def get_distribution_adjustments(
    cycle_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_role("admin", "hr", "executive")),
):
    """获取强制分布调整明细"""
    cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核周期不存在")

    records = db.query(AssessmentRecord).filter(
        AssessmentRecord.cycle_id == cycle_id,
        AssessmentRecord.original_grade != None,
        AssessmentRecord.grade != AssessmentRecord.original_grade,
    ).all()

    result = []
    for r in records:
        emp = db.query(Employee).filter(Employee.id == r.employee_id).first()
        result.append({
            "record_id": r.id,
            "employee_id": r.employee_id,
            "employee_name": emp.name if emp else None,
            "employee_no": emp.employee_no if emp else None,
            "total_score": str(r.total_score) if r.total_score else None,
            "original_grade": r.original_grade,
            "adjusted_grade": r.grade,
            "is_override": r.is_distribution_override,
            "override_reason": r.override_reason,
        })

    return {
        "cycle_id": cycle_id,
        "adjustments": result,
        "total_adjusted": len(result),
    }


@router.get("/employee/{employee_id}/trend")
def get_employee_trend(
    employee_id: int,
    limit: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取员工历史绩效趋势（P6-03）"""
    # P0-8: Data isolation
    if user.role == "peer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问")
    elif user.role == "employee":
        if user.employee_id != employee_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能查看本人的绩效趋势")
    elif user.role == "manager":
        current_employee = db.query(Employee).filter(Employee.id == user.employee_id).first()
        if not current_employee:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问")
        target_employee = db.query(Employee).filter(Employee.id == employee_id).first()
        dept_ids = get_all_dept_ids(db, current_employee.department_id)
        allowed = (
            current_employee.id == employee_id
            or _is_in_subordinate_chain(db, current_employee.id, employee_id)
            or (target_employee and target_employee.department_id in dept_ids)
        )
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问")
    # admin, hr, executive: allow all

    records = db.query(AssessmentRecord).filter(
        AssessmentRecord.employee_id == employee_id
    )
    # P1-18: 员工只能查看已发布/已归档的考核结果
    if user.role == "employee":
        records = records.filter(AssessmentRecord.status.in_(["published", "archived"]))
    records = records.order_by(AssessmentRecord.created_at.asc()).limit(limit).all()

    result = []
    for r in records:
        cycle = db.query(AssessmentCycle).filter(AssessmentCycle.id == r.cycle_id).first()
        self_scores = load_json(r.self_scores, {})
        manager_scores = load_json(r.manager_scores, {})
        peer_scores = load_json(r.peer_scores, {})

        result.append({
            "record_id": r.id,
            "cycle_id": r.cycle_id,
            "cycle_name": cycle.name if cycle else None,
            "cycle_type": cycle.type if cycle else None,
            "self_scores": self_scores,
            "manager_scores": manager_scores,
            "peer_scores": peer_scores,
            "weighted_performance": str(r.weighted_performance) if r.weighted_performance else None,
            "weighted_ability": str(r.weighted_ability) if r.weighted_ability else None,
            "weighted_attitude": str(r.weighted_attitude) if r.weighted_attitude else None,
            "total_score": str(r.total_score) if r.total_score else None,
            "grade": r.grade,
            "original_grade": r.original_grade,
            "status": r.status,
            "manager_comment": r.manager_comment,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return {"items": result, "total": len(result)}


@router.get("/record/{record_id}/pdf")
def export_record_pdf(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "hr", "executive", "employee")),
):
    """导出绩效档案PDF"""
    from app.utils.pdf_generator import generate_performance_pdf
    from fastapi.responses import StreamingResponse

    record = db.query(AssessmentRecord).filter(AssessmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考核记录不存在")

    # 权限隔离：员工只能下载自己的
    if user.role == "employee" and user.employee_id != record.employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看此记录")

    pdf_bytes = generate_performance_pdf(record_id, db)
    if not pdf_bytes:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="PDF生成失败")

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=performance_{record_id}.pdf"},
    )
