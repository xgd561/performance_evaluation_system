import pytest
from fastapi.testclient import TestClient
from datetime import date
from io import BytesIO
from app.models import AssessmentCycle, AssessmentRecord, Employee, Department, Position


@pytest.fixture
def excel_test_data(db_session):
    """创建 Excel 导出测试所需的基础数据"""
    dept_a = db_session.query(Department).filter(Department.code == "TECH").first()
    if not dept_a:
        dept_a = Department(name="技术部", code="TECH")
        db_session.add(dept_a)
        db_session.flush()

    dept_b = db_session.query(Department).filter(Department.code == "SALE").first()
    if not dept_b:
        dept_b = Department(name="销售部", code="SALE")
        db_session.add(dept_b)
        db_session.flush()

    pos_a = db_session.query(Position).filter(Position.name == "Java工程师", Position.department_id == dept_a.id).first()
    if not pos_a:
        pos_a = Position(name="Java工程师", department_id=dept_a.id)
        db_session.add(pos_a)
        db_session.flush()

    pos_b = db_session.query(Position).filter(Position.name == "销售经理", Position.department_id == dept_b.id).first()
    if not pos_b:
        pos_b = Position(name="销售经理", department_id=dept_b.id)
        db_session.add(pos_b)
        db_session.flush()

    emp_a = db_session.query(Employee).filter(Employee.employee_no == "EX001").first()
    if not emp_a:
        emp_a = Employee(employee_no="EX001", name="张三", department_id=dept_a.id, position_id=pos_a.id)
        db_session.add(emp_a)
        db_session.flush()

    emp_b = db_session.query(Employee).filter(Employee.employee_no == "EX002").first()
    if not emp_b:
        emp_b = Employee(employee_no="EX002", name="李四", department_id=dept_b.id, position_id=pos_b.id)
        db_session.add(emp_b)
        db_session.flush()

    cycle = AssessmentCycle(
        name="Excel导出测试周期",
        type="annual",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status="published",
        is_locked=False,
    )
    db_session.add(cycle)
    db_session.flush()

    record_a = AssessmentRecord(
        cycle_id=cycle.id,
        employee_id=emp_a.id,
        position_id=pos_a.id,
        department_id=dept_a.id,
        total_score=90.0,
        grade="A",
        original_grade="A",
        weighted_performance=92.0,
        weighted_ability=88.0,
        weighted_attitude=90.0,
        is_distribution_override=False,
        status="published",
    )
    db_session.add(record_a)

    record_b = AssessmentRecord(
        cycle_id=cycle.id,
        employee_id=emp_b.id,
        position_id=pos_b.id,
        department_id=dept_b.id,
        total_score=75.0,
        grade="C",
        original_grade="C",
        weighted_performance=70.0,
        weighted_ability=78.0,
        weighted_attitude=77.0,
        is_distribution_override=True,
        override_reason="部门比例调整",
        status="published",
    )
    db_session.add(record_b)
    db_session.commit()

    return {"cycle": cycle, "dept_a": dept_a, "dept_b": dept_b, "emp_a": emp_a, "emp_b": emp_b}


class TestExcelExport:
    """P6-12: Excel 导出端点测试"""

    def _read_excel_from_response(self, resp):
        from openpyxl import load_workbook
        wb = load_workbook(BytesIO(resp.content))
        return wb

    def test_export_excel_by_admin(self, client: TestClient, admin_token, excel_test_data):
        """Admin 应能成功导出 Excel"""
        cycle = excel_test_data["cycle"]
        resp = client.get(
            f"/api/v1/assessment-cycles/{cycle.id}/export-excel",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        wb = self._read_excel_from_response(resp)
        ws = wb.active
        assert ws.title == "考核汇总"
        assert ws.cell(row=1, column=1).value == "工号"
        assert ws.cell(row=2, column=1).value == excel_test_data["emp_a"].employee_no

    def test_export_excel_by_hr(self, client: TestClient, hr_token, excel_test_data):
        """HR 应能成功导出 Excel"""
        cycle = excel_test_data["cycle"]
        resp = client.get(
            f"/api/v1/assessment-cycles/{cycle.id}/export-excel",
            headers={"Authorization": f"Bearer {hr_token}"},
        )
        assert resp.status_code == 200
        wb = self._read_excel_from_response(resp)
        ws = wb.active
        assert ws.title == "考核汇总"

    def test_export_excel_by_executive(self, client: TestClient, executive_token, excel_test_data):
        """Executive 应能成功导出 Excel"""
        cycle = excel_test_data["cycle"]
        resp = client.get(
            f"/api/v1/assessment-cycles/{cycle.id}/export-excel",
            headers={"Authorization": f"Bearer {executive_token}"},
        )
        assert resp.status_code == 200
        wb = self._read_excel_from_response(resp)
        ws = wb.active
        assert ws.title == "考核汇总"

    def test_export_excel_nonexistent_cycle_returns_404(self, client: TestClient, admin_token):
        """不存在的周期导出应返回 404"""
        resp = client.get(
            "/api/v1/assessment-cycles/99999/export-excel",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404
        assert "考核周期不存在" in resp.json()["message"]

    def test_export_excel_by_manager_returns_403(self, client: TestClient, manager_token, excel_test_data):
        """Manager 无权导出 Excel"""
        cycle = excel_test_data["cycle"]
        resp = client.get(
            f"/api/v1/assessment-cycles/{cycle.id}/export-excel",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert resp.status_code == 403

    def test_export_excel_by_employee_returns_403(self, client: TestClient, employee_token, excel_test_data):
        """Employee 无权导出 Excel"""
        cycle = excel_test_data["cycle"]
        resp = client.get(
            f"/api/v1/assessment-cycles/{cycle.id}/export-excel",
            headers={"Authorization": f"Bearer {employee_token}"},
        )
        assert resp.status_code == 403

    def test_export_excel_filter_by_department(self, client: TestClient, admin_token, excel_test_data):
        """按部门筛选应只导出该部门记录"""
        cycle = excel_test_data["cycle"]
        dept_a = excel_test_data["dept_a"]
        resp = client.get(
            f"/api/v1/assessment-cycles/{cycle.id}/export-excel?department_id={dept_a.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        wb = self._read_excel_from_response(resp)
        ws = wb.active
        # 表头 + 1 行数据 = 2 行
        assert ws.max_row == 2
        assert ws.cell(row=2, column=1).value == excel_test_data["emp_a"].employee_no
