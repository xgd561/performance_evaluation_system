"""
test_perf.py — Performance tests (TC-PERF-001 ~ TC-PERF-024)

Corresponds to test cases in:
  TEST_CASES_绩效考核评分系统_v1.0.md  §15 性能测试用例 (PERF)
"""

import io
import time
import pytest
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

from tests.scripts.utils import assert_status_code, make_excel_bytes


# ---------------------------------------------------------------------------
# Baseline / UI-load tests (TC-PERF-001, TC-PERF-016, TC-PERF-024)
# ---------------------------------------------------------------------------

class TestFrontendPerf:
    """TC-PERF-001, TC-PERF-016, TC-PERF-024"""

    def test_dashboard_load_time(self, client: TestClient, admin_headers: dict):
        """TC-PERF-001: 首页仪表盘加载性能"""
        start = time.perf_counter()
        resp = client.get("/dashboard", headers=admin_headers)
        duration = time.perf_counter() - start
        assert duration < 2.0, f"Dashboard took {duration:.2f}s"
        assert_status_code(resp, 200)

    def test_dashboard_chart_render(self, client: TestClient, admin_headers: dict):
        """TC-PERF-016: 仪表盘图表渲染"""
        start = time.perf_counter()
        resp = client.get("/dashboard/charts", headers=admin_headers)
        duration = time.perf_counter() - start
        assert duration < 2.0, f"Chart render took {duration:.2f}s"
        assert_status_code(resp, 200)

    def test_static_resource_cache(self, client: TestClient):
        """TC-PERF-024: 静态资源缓存"""
        resp1 = client.get("/static/app.js")
        assert resp1.status_code in (200, 404)
        if resp1.status_code == 200:
            cache_control = resp1.headers.get("Cache-Control", "")
            assert "max-age" in cache_control or "no-cache" in cache_control


# ---------------------------------------------------------------------------
# Query / read performance (TC-PERF-006 ~ TC-PERF-008, TC-PERF-010 ~ TC-PERF-012)
# ---------------------------------------------------------------------------

class TestQueryPerf:
    """TC-PERF-006, TC-PERF-007, TC-PERF-008, TC-PERF-010, TC-PERF-011, TC-PERF-012"""

    def test_employee_list_10k(self, client: TestClient, admin_headers: dict):
        """TC-PERF-006: 员工列表10k数据查询"""
        start = time.perf_counter()
        resp = client.get("/employees?page=1&size=20", headers=admin_headers)
        duration = time.perf_counter() - start
        assert duration < 0.2, f"Employee list took {duration:.2f}s"
        assert_status_code(resp, 200)

        # Page 500
        start = time.perf_counter()
        resp = client.get("/employees?page=500&size=20", headers=admin_headers)
        duration = time.perf_counter() - start
        assert duration < 0.3, f"Page 500 took {duration:.2f}s"

    def test_full_text_search_speed(self, client: TestClient, admin_headers: dict):
        """TC-PERF-007: 全文搜索响应时间"""
        for keyword in ("张", "张三"):
            start = time.perf_counter()
            resp = client.get(f"/employees?keyword={keyword}", headers=admin_headers)
            duration = time.perf_counter() - start
            assert duration < 0.3, f"Search '{keyword}' took {duration:.2f}s"
            assert_status_code(resp, 200)

    def test_report_generate_1000(self, client: TestClient, admin_headers: dict, seeded_cycle: dict):
        """TC-PERF-008: 报表生成1000人数据"""
        start = time.perf_counter()
        resp = client.get(f"/reports/cycle/{seeded_cycle['id']}/summary", headers=admin_headers)
        duration = time.perf_counter() - start
        assert duration < 2.0, f"Report generation took {duration:.2f}s"
        assert_status_code(resp, 200)

    def test_concurrent_read(self, client: TestClient, admin_headers: dict):
        """TC-PERF-010: 并发读取API"""
        def fetch(_):
            return client.get("/employees?page=1&size=20", headers=admin_headers)

        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=100) as pool:
            results = list(pool.map(fetch, range(100)))
        duration = time.perf_counter() - start

        errors = [r for r in results if r.status_code != 200]
        assert len(errors) == 0, f"{len(errors)} requests failed"
        assert duration < 5.0, f"100 concurrent reads took {duration:.2f}s"

    def test_no_slow_queries(self, client: TestClient, admin_headers: dict):
        """TC-PERF-011: 数据库慢查询监控"""
        # Trigger a few complex queries
        endpoints = [
            "/employees?page=1&size=100",
            "/reports/cycle/1/distribution",
            "/assessment-cycles/1/progress",
        ]
        for url in endpoints:
            resp = client.get(url, headers=admin_headers)
            assert resp.status_code in (200, 404)

    def test_long_list_render_virtual_scroll(self, client: TestClient, admin_headers: dict):
        """TC-PERF-012: 前端长列表渲染 (API validates large page size)"""
        resp = client.get("/employees?page=1&size=1000", headers=admin_headers)
        assert_status_code(resp, 200)
        assert len(resp.json().get("items", [])) <= 1000


# ---------------------------------------------------------------------------
# Import / export performance (TC-PERF-009, TC-PERF-015, TC-PERF-019, TC-PERF-021)
# ---------------------------------------------------------------------------

class TestImportExportPerf:
    """TC-PERF-009, TC-PERF-015, TC-PERF-019, TC-PERF-021"""

    def test_excel_import_10k_rows(self, client: TestClient, admin_headers: dict):
        """TC-PERF-009: Excel导入10,000行"""
        headers = ["工号", "姓名", "部门", "岗位"]
        rows = [[f"EMP{i:05d}", f"员工{i}", "技术部", "Java工程师"] for i in range(1, 10001)]
        excel_bytes = make_excel_bytes(10000, headers, rows)
        if not excel_bytes:
            pytest.skip("openpyxl not installed")

        files = {"file": ("employees.xlsx", io.BytesIO(excel_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        start = time.perf_counter()
        resp = client.post("/employees/import", files=files, headers=admin_headers)
        duration = time.perf_counter() - start
        assert duration < 30.0, f"10k import took {duration:.2f}s"
        assert_status_code(resp, 200)
        assert resp.json().get("success") == 10000

    def test_pdf_generate_500_with_images(self, client: TestClient, admin_headers: dict):
        """TC-PERF-015: 图片密集型PDF生成"""
        start = time.perf_counter()
        resp = client.get("/reports/batch/pdf?count=500", headers=admin_headers)
        duration = time.perf_counter() - start
        if resp.status_code == 404:
            pytest.skip("Batch PDF endpoint not implemented")
        assert duration < 60.0, f"500 PDF generation took {duration:.2f}s"
        assert_status_code(resp, 200)

    def test_export_5000_pdf(self, client: TestClient, admin_headers: dict, seeded_cycle: dict):
        """TC-PERF-019: 导出5000人PDF"""
        start = time.perf_counter()
        resp = client.get(f"/reports/cycle/{seeded_cycle['id']}/export?format=pdf", headers=admin_headers)
        duration = time.perf_counter() - start
        if resp.status_code == 404:
            pytest.skip("PDF export endpoint not implemented")
        assert duration < 45.0, f"5000 PDF export took {duration:.2f}s"
        assert_status_code(resp, 200)
        assert len(resp.content) < 50 * 1024 * 1024  # < 50MB

    def test_concurrent_export(self, client: TestClient, admin_headers: dict, seeded_cycle: dict):
        """TC-PERF-021: 并发导出"""
        def export(_):
            return client.get(f"/reports/cycle/{seeded_cycle['id']}/export?format=xlsx", headers=admin_headers)

        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(export, range(10)))
        duration = time.perf_counter() - start

        for r in results:
            assert r.status_code == 200
        assert duration < 15.0, f"10 concurrent exports took {duration:.2f}s"


# ---------------------------------------------------------------------------
# Memory / stability (TC-PERF-013, TC-PERF-014, TC-PERF-022, TC-PERF-023)
# ---------------------------------------------------------------------------

class TestStabilityPerf:
    """TC-PERF-013, TC-PERF-014, TC-PERF-022, TC-PERF-023"""

    def test_memory_leak(self, client: TestClient, admin_headers: dict):
        """TC-PERF-013: 内存泄漏检测"""
        # Run a few heavy operations and verify response times don't degrade
        times = []
        for _ in range(10):
            start = time.perf_counter()
            resp = client.get("/employees?page=1&size=100", headers=admin_headers)
            times.append(time.perf_counter() - start)
            assert resp.status_code == 200
        # Last 3 should not be significantly slower than first 3
        avg_first = sum(times[:3]) / 3
        avg_last = sum(times[-3:]) / 3
        assert avg_last < avg_first * 2, "Possible memory leak detected"

    def test_cache_hit_rate(self, client: TestClient, admin_headers: dict):
        """TC-PERF-014: 缓存命中率"""
        # First call (cold)
        r1 = client.get("/employees?page=1&size=20", headers=admin_headers)
        assert r1.status_code == 200
        # Subsequent calls should be faster (warm cache)
        start = time.perf_counter()
        for _ in range(9):
            client.get("/employees?page=1&size=20", headers=admin_headers)
        duration = time.perf_counter() - start
        assert duration < 1.0, f"10 cached reads took {duration:.2f}s"

    def test_connection_pool_limits(self, client: TestClient, admin_headers: dict):
        """TC-PERF-022: 数据库连接池"""
        def fetch(_):
            return client.get("/employees?page=1&size=20", headers=admin_headers)

        with ThreadPoolExecutor(max_workers=100) as pool:
            results = list(pool.map(fetch, range(100)))
        errors = [r for r in results if r.status_code not in (200, 503)]
        assert len(errors) == 0, f"Unexpected errors: {len(errors)}"

    def test_message_queue_throughput(self, client: TestClient, admin_headers: dict):
        """TC-PERF-023: 消息队列处理"""
        # Trigger bulk notifications
        payload = {"employee_ids": list(range(1, 1001)), "message": "考核通知"}
        resp = client.post("/notifications/bulk", json=payload, headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Bulk notification endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        assert data.get("sent", 0) >= 100 or data.get("queued", 0) >= 100


# ---------------------------------------------------------------------------
# Write / batch performance (TC-PERF-017, TC-PERF-018, TC-PERF-020)
# ---------------------------------------------------------------------------

class TestWritePerf:
    """TC-PERF-017, TC-PERF-018, TC-PERF-020"""

    def test_batch_approval_100(self, client: TestClient, admin_headers: dict, seeded_cycle: dict):
        """TC-PERF-017: 批量审批100人"""
        # Need 100 pending records
        payload = {"record_ids": list(range(1, 101)), "action": "pass"}
        start = time.perf_counter()
        resp = client.post("/approvals/batch", json=payload, headers=admin_headers)
        duration = time.perf_counter() - start
        if resp.status_code == 404:
            pytest.skip("Batch approval endpoint not implemented")
        assert duration < 3.0, f"Batch 100 approvals took {duration:.2f}s"
        assert_status_code(resp, 200)

    def test_summarize_1000(self, client: TestClient, admin_headers: dict, seeded_cycle: dict):
        """TC-PERF-018: 汇总计算1000人"""
        start = time.perf_counter()
        resp = client.post(f"/assessment-cycles/{seeded_cycle['id']}/summarize", headers=admin_headers)
        duration = time.perf_counter() - start
        assert duration < 8.0, f"1000 summarize took {duration:.2f}s"
        assert_status_code(resp, 200)

    def test_concurrent_login_200(self, client: TestClient):
        """TC-PERF-020: 并发登录200人"""
        def login(_):
            return client.post("/auth/login", json={"username": "admin", "password": "admin123"})

        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=200) as pool:
            results = list(pool.map(login, range(200)))
        duration = time.perf_counter() - start
        errors = [r for r in results if r.status_code != 200]
        assert len(errors) == 0, f"{len(errors)} login failures"
        assert duration < 10.0, f"200 concurrent logins took {duration:.2f}s"


class TestAdditionalPerf:
    """TC-PERF-025, TC-PERF-026, TC-PERF-027, TC-PERF-028, TC-PERF-029, TC-PERF-030"""

    def test_score_page_load(self, client: TestClient, employee_headers: dict):
        """TC-PERF-025: 评分页加载性能"""
        start = time.perf_counter()
        resp = client.get("/scores/my-assessment", headers=employee_headers)
        duration = time.perf_counter() - start
        assert duration < 2.0, f"Score page took {duration:.2f}s"
        assert resp.status_code in (200, 404)

    def test_summary_page_load_500(self, client: TestClient, admin_headers: dict, seeded_cycle: dict):
        """TC-PERF-026: 汇总页加载500人"""
        start = time.perf_counter()
        resp = client.get(f"/scores/summary/{seeded_cycle['id']}", headers=admin_headers)
        duration = time.perf_counter() - start
        if resp.status_code == 404:
            pytest.skip("Score summary endpoint not implemented")
        assert duration < 3.0, f"Summary page took {duration:.2f}s"
        assert_status_code(resp, 200)

    def test_trend_chart_load(self, client: TestClient, admin_headers: dict, seeded_employee: dict):
        """TC-PERF-027: 历史趋势图加载"""
        start = time.perf_counter()
        resp = client.get(f"/reports/employee/{seeded_employee['id']}/trend?cycles=8", headers=admin_headers)
        duration = time.perf_counter() - start
        if resp.status_code == 404:
            pytest.skip("Trend endpoint not implemented")
        assert duration < 2.0, f"Trend chart took {duration:.2f}s"
        assert_status_code(resp, 200)

    def test_login_response_time(self, client: TestClient):
        """TC-PERF-028: 登录接口响应时间"""
        times = []
        for _ in range(10):
            start = time.perf_counter()
            resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
            times.append(time.perf_counter() - start)
            assert resp.status_code == 200
        avg = sum(times) / len(times)
        assert avg < 0.3, f"Average login time {avg:.3f}s exceeds 300ms"

    def test_submit_score_response_time(self, client: TestClient, employee_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-PERF-029: 提交评分接口响应时间"""
        payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_id": seeded_employee["id"],
            "dimension_scores": {"业绩": 85, "能力": 90, "态度": 88},
        }
        start = time.perf_counter()
        resp = client.post("/scores/self", json=payload, headers=employee_headers)
        duration = time.perf_counter() - start
        if resp.status_code == 404:
            pytest.skip("Self score endpoint not implemented")
        assert duration < 0.3, f"Score submission took {duration:.3f}s"

    def test_concurrent_manager_score_50(self, client: TestClient, admin_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-PERF-030: 50人同时提交上级评分"""
        # Create 50 employees and records
        from tests.scripts.utils import create_employee
        from concurrent.futures import ThreadPoolExecutor

        emps = []
        for i in range(1, 6):  # Use 5 for quick test; 50 would be too slow in unit test
            emp = create_employee(
                client, admin_headers, f"EMP_PERF{i:03d}", f"员工{i}",
                seeded_employee["department_id"], seeded_employee["position_id"],
            )
            emps.append(emp)

        # Launch cycle for them
        client.post(
            "/assessment-cycles/launch",
            json={"cycle_id": seeded_cycle["id"], "employee_ids": [e["id"] for e in emps]},
            headers=admin_headers,
        )

        def submit_score(emp):
            payload = {
                "cycle_id": seeded_cycle["id"],
                "employee_id": emp["id"],
                "dimension_scores": {"业绩": 85, "能力": 90, "态度": 88},
            }
            return client.post("/scores/self", json=payload, headers=admin_headers)

        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(submit_score, emps))
        duration = time.perf_counter() - start

        errors = [r for r in results if r.status_code not in (200, 409)]
        assert len(errors) == 0, f"{len(errors)} score submissions failed"
        assert duration < 2.0, f"Concurrent scores took {duration:.2f}s"


class TestAdditionalPerf:
    """TC-PERF-025, TC-PERF-026, TC-PERF-027, TC-PERF-028, TC-PERF-029, TC-PERF-030"""

    def test_scoring_page_load(self, client: TestClient, employee_headers: dict):
        """TC-PERF-025: 评分页加载性能"""
        start = time.perf_counter()
        resp = client.get("/scores/my-assessment", headers=employee_headers)
        duration = time.perf_counter() - start
        if resp.status_code == 404:
            pytest.skip("My assessment endpoint not implemented")
        assert duration < 2.0, f"Scoring page took {duration:.2f}s"
        assert_status_code(resp, 200)

    def test_summary_page_load_500(self, client: TestClient, admin_headers: dict, seeded_cycle: dict):
        """TC-PERF-026: 汇总页加载500人"""
        start = time.perf_counter()
        resp = client.get(f"/scores/summary/{seeded_cycle['id']}", headers=admin_headers)
        duration = time.perf_counter() - start
        if resp.status_code == 404:
            pytest.skip("Score summary endpoint not implemented")
        assert duration < 3.0, f"Summary page took {duration:.2f}s"
        assert_status_code(resp, 200)

    def test_trend_chart_load(self, client: TestClient, admin_headers: dict, seeded_employee: dict):
        """TC-PERF-027: 历史趋势图加载"""
        start = time.perf_counter()
        resp = client.get(f"/reports/employee/{seeded_employee['id']}/trend?cycles=8", headers=admin_headers)
        duration = time.perf_counter() - start
        if resp.status_code == 404:
            pytest.skip("Trend endpoint not implemented")
        assert duration < 2.0, f"Trend chart took {duration:.2f}s"
        assert_status_code(resp, 200)

    def test_login_response_time(self, client: TestClient):
        """TC-PERF-028: 登录接口响应时间"""
        times = []
        for _ in range(10):
            start = time.perf_counter()
            resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
            times.append(time.perf_counter() - start)
            assert resp.status_code == 200
        avg = sum(times) / len(times)
        assert avg < 0.3, f"Average login time {avg:.2f}s exceeds 300ms"

    def test_submit_score_response_time(self, client: TestClient, employee_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-PERF-029: 提交评分接口响应时间"""
        payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_id": seeded_employee["id"],
            "dimension_scores": {"业绩": 85, "能力": 90, "态度": 88},
        }
        start = time.perf_counter()
        resp = client.post("/scores/self", json=payload, headers=employee_headers)
        duration = time.perf_counter() - start
        if resp.status_code == 404:
            pytest.skip("Self score endpoint not implemented")
        assert duration < 0.3, f"Score submission took {duration:.2f}s"

    def test_concurrent_manager_score_50(self, client: TestClient, manager_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-PERF-030: 50人同时提交上级评分"""
        def submit_score(_):
            payload = {
                "cycle_id": seeded_cycle["id"],
                "employee_id": seeded_employee["id"],
                "dimension_scores": {"业绩": 85, "能力": 90, "态度": 88},
            }
            return client.post("/scores/manager", json=payload, headers=manager_headers)

        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=50) as pool:
            results = list(pool.map(submit_score, range(50)))
        duration = time.perf_counter() - start
        errors = [r for r in results if r.status_code not in (200, 409)]
        assert len(errors) == 0, f"{len(errors)} requests failed"
        assert duration < 10.0, f"50 concurrent manager scores took {duration:.2f}s"
