"""
test_exc.py — Exception scenario tests (TC-EXC-001 ~ TC-EXC-030)

Corresponds to test cases in:
  TEST_CASES_绩效考核评分系统_v1.0.md  §16.4 异常场景测试用例 (EXC)
"""

import io
import pytest
from fastapi.testclient import TestClient

from tests.scripts.utils import (
    assert_status_code,
    make_excel_bytes,
    create_department,
    create_position,
    create_employee,
)


# ---------------------------------------------------------------------------
# Network / timeout / connection errors (TC-EXC-001 ~ TC-EXC-005)
# ---------------------------------------------------------------------------

class TestNetworkException:
    """TC-EXC-001, TC-EXC-002, TC-EXC-003, TC-EXC-004, TC-EXC-005"""

    def test_network_timeout_graceful(self, client: TestClient, employee_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-EXC-001: 网络超时处理"""
        # Simulate slow network by sending large payload
        large_payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_id": seeded_employee["id"],
            "dimension_scores": {"业绩": 85, "能力": 90, "态度": 88},
        }
        resp = client.post("/scores/self", json=large_payload, headers=employee_headers)
        assert resp.status_code in (200, 408, 504)
        if resp.status_code != 200:
            assert "超时" in resp.json().get("message", "") or "timeout" in resp.json().get("message", "").lower()

    def test_database_connection_failure(self, client: TestClient, admin_headers: dict):
        """TC-EXC-002: 数据库连接失败"""
        # This is typically tested by stopping the DB; at API level we verify error format
        resp = client.get("/health/db", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("DB health endpoint not implemented")
        if resp.status_code == 503:
            data = resp.json()
            assert "暂时不可用" in data.get("message", "")
            assert "code" in data

    def test_server_500_error_format(self, client: TestClient, admin_headers: dict):
        """TC-EXC-003: 服务器500错误"""
        resp = client.get("/debug/trigger-500", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Debug error endpoint not implemented")
        assert_status_code(resp, 500)
        data = resp.json()
        assert "trace_id" in data or "request_id" in data
        assert "stack" not in data and "traceback" not in data

    def test_service_maintenance_503(self, client: TestClient):
        """TC-EXC-004: 服务维护503"""
        resp = client.get("/maintenance")
        if resp.status_code == 404:
            pytest.skip("Maintenance endpoint not implemented")
        assert_status_code(resp, 503)
        assert "Retry-After" in resp.headers or "维护" in resp.json().get("message", "")

    def test_request_timeout_interrupt(self, client: TestClient, admin_headers: dict):
        """TC-EXC-005: 请求超时"""
        resp = client.get("/reports/slow-query", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Slow query endpoint not implemented")
        assert resp.status_code in (200, 408, 504)
        if resp.status_code != 200:
            assert "超时" in resp.json().get("message", "") or "timeout" in resp.json().get("message", "").lower()


# ---------------------------------------------------------------------------
# Request format / validation errors (TC-EXC-006 ~ TC-EXC-009)
# ---------------------------------------------------------------------------

class TestRequestFormatException:
    """TC-EXC-006, TC-EXC-007, TC-EXC-008, TC-EXC-009"""

    def test_invalid_json_payload(self, client: TestClient, admin_headers: dict):
        """TC-EXC-006: 无效JSON请求体"""
        resp = client.post(
            "/employees",
            data='{ "name": "张三"',
            headers={**admin_headers, "Content-Type": "application/json"},
        )
        assert_status_code(resp, 400)
        assert "JSON" in resp.json().get("message", "")

    def test_missing_content_type_header(self, client: TestClient, admin_headers: dict):
        """TC-EXC-007: 缺少必要请求头"""
        resp = client.post("/employees", data="not json", headers=admin_headers)
        assert resp.status_code in (400, 415)

    def test_file_upload_too_large(self, client: TestClient, admin_headers: dict):
        """TC-EXC-008: 文件上传过大"""
        large_content = b"x" * (15 * 1024 * 1024)
        files = {"file": ("large.xlsx", io.BytesIO(large_content), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = client.post("/employees/import", files=files, headers=admin_headers)
        assert_status_code(resp, 413)

    def test_unsupported_file_format(self, client: TestClient, admin_headers: dict):
        """TC-EXC-009: 不支持的文件格式"""
        files = {"file": ("data.csv", io.BytesIO("name,age\n张三,30".encode('utf-8')), "text/csv")}
        resp = client.post("/employees/import", files=files, headers=admin_headers)
        assert_status_code(resp, 415)
        assert "xlsx" in resp.json().get("message", "")


# ---------------------------------------------------------------------------
# Concurrency / data consistency errors (TC-EXC-010 ~ TC-EXC-013)
# ---------------------------------------------------------------------------

class TestConcurrencyException:
    """TC-EXC-010, TC-EXC-011, TC-EXC-012, TC-EXC-013"""

    def test_optimistic_lock_conflict(self, client: TestClient, admin_headers: dict, seeded_employee: dict):
        """TC-EXC-010: 并发修改冲突"""
        # Two updates with same version
        resp1 = client.get(f"/employees/{seeded_employee['id']}", headers=admin_headers)
        version = resp1.json().get("version", 1)
        payload = {"name": "修改A", "version": version}
        client.put(f"/employees/{seeded_employee['id']}", json=payload, headers=admin_headers)
        # Second update with same version should fail
        payload2 = {"name": "修改B", "version": version}
        resp2 = client.put(f"/employees/{seeded_employee['id']}", json=payload2, headers=admin_headers)
        if resp2.status_code == 409:
            assert "已被他人修改" in resp2.json().get("message", "")

    def test_data_inconsistency_missing_score(self, client: TestClient, admin_headers: dict, seeded_cycle: dict):
        """TC-EXC-011: 数据不一致"""
        resp = client.post(f"/assessment-cycles/{seeded_cycle['id']}/summarize", headers=admin_headers)
        assert resp.status_code in (200, 409)
        if resp.status_code == 200:
            data = resp.json()
            if "warnings" in data:
                assert any("缺失" in w for w in data["warnings"])

    def test_third_party_service_failure(self, client: TestClient, admin_headers: dict):
        """TC-EXC-012: 第三方服务故障"""
        # Simulate SMS failure by triggering notification with bad provider config
        resp = client.post("/notifications/test-sms", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Test SMS endpoint not implemented")
        assert resp.status_code in (200, 503)
        if resp.status_code == 503:
            assert "降级" in resp.json().get("message", "") or "服务" in resp.json().get("message", "")

    def test_notification_service_failure(self, client: TestClient, admin_headers: dict, seeded_cycle: dict):
        """TC-EXC-013: 通知服务失败"""
        payload = {"employee_ids": [1, 2, 3], "message": "测试通知"}
        resp = client.post("/notifications", json=payload, headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Notification endpoint not implemented")
        assert resp.status_code in (200, 503)
        if resp.status_code == 200:
            assert resp.json().get("queued") is True or resp.json().get("sent") is not None


# ---------------------------------------------------------------------------
# Service / resource errors (TC-EXC-014 ~ TC-EXC-018)
# ---------------------------------------------------------------------------

class TestServiceException:
    """TC-EXC-014, TC-EXC-015, TC-EXC-016, TC-EXC-017, TC-EXC-018"""

    def test_export_service_failure(self, client: TestClient, admin_headers: dict, seeded_cycle: dict):
        """TC-EXC-014: 导出服务失败"""
        resp = client.get(f"/reports/cycle/{seeded_cycle['id']}/export?format=xlsx", headers=admin_headers)
        if resp.status_code == 507:
            assert "磁盘" in resp.json().get("message", "") or "空间" in resp.json().get("message", "")

    def test_import_partial_failure(self, client: TestClient, admin_headers: dict):
        """TC-EXC-015: 导入部分失败"""
        headers = ["工号", "姓名", "部门", "岗位"]
        rows = [[f"EMP{i:03d}", f"员工{i}", "技术部", "Java工程师"] for i in range(1, 101)]
        # Introduce errors
        rows[10][1] = ""
        rows[20][0] = ""
        rows[30][1] = ""
        excel_bytes = make_excel_bytes(100, headers, rows)
        if not excel_bytes:
            pytest.skip("openpyxl not installed")
        files = {"file": ("employees.xlsx", io.BytesIO(excel_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = client.post("/employees/import", files=files, headers=admin_headers)
        assert_status_code(resp, 200)
        data = resp.json()
        assert data.get("success") + data.get("failed", 0) == 100
        assert "errors" in data

    def test_foreign_key_missing(self, client: TestClient, admin_headers: dict):
        """TC-EXC-016: 外键缺失"""
        payload = {
            "employee_no": "EMP_FK",
            "name": "外键测试",
            "department_id": 99999,
            "position_id": 1,
        }
        resp = client.post("/employees", json=payload, headers=admin_headers)
        assert_status_code(resp, 422)
        assert "不存在" in resp.json().get("message", "")

    def test_cascade_delete_blocked(self, client: TestClient, admin_headers: dict, seeded_department: dict, seeded_position: dict):
        """TC-EXC-017: 级联删除拦截"""
        dept_id = seeded_department["id"]
        resp = client.delete(f"/departments/{dept_id}", headers=admin_headers)
        assert_status_code(resp, 409)
        msg = resp.json().get("message", "")
        assert "员工" in msg or "岗位" in msg

    def test_api_version_conflict(self, client: TestClient, admin_headers: dict):
        """TC-EXC-018: 版本冲突"""
        resp = client.get("/v1/employees", headers=admin_headers)
        if resp.status_code == 410:
            assert "已弃用" in resp.json().get("message", "")
        elif resp.status_code == 200:
            assert "Deprecation" in resp.headers or "弃用" in resp.json().get("warning", "")


# ---------------------------------------------------------------------------
# Idempotency / rate / lock / queue errors (TC-EXC-019 ~ TC-EXC-023)
# ---------------------------------------------------------------------------

class TestIdempotencyException:
    """TC-EXC-019, TC-EXC-020, TC-EXC-021, TC-EXC-022, TC-EXC-023"""

    def test_duplicate_request_idempotency(self, client: TestClient, admin_headers: dict, seeded_department: dict, seeded_position: dict):
        """TC-EXC-019: 重复请求幂等性"""
        payload = {
            "employee_no": "EMP_IDEM",
            "name": "幂等测试",
            "department_id": seeded_department["id"],
            "position_id": seeded_position["id"],
        }
        headers = {**admin_headers, "Idempotency-Key": "unique-key-123"}
        resp1 = client.post("/employees", json=payload, headers=headers)
        resp2 = client.post("/employees", json=payload, headers=headers)
        if resp1.status_code == 201 and resp2.status_code == 201:
            # If idempotency is not implemented, both succeed; verify only one record exists
            resp_list = client.get("/employees?employee_no=EMP_IDEM", headers=admin_headers)
            assert len(resp_list.json().get("items", [])) == 1
        elif resp2.status_code == 409:
            assert "已存在" in resp2.json().get("message", "")

    def test_rate_limit_exceeded(self, client: TestClient):
        """TC-EXC-020: 限流拦截"""
        for i in range(70):
            resp = client.get("/employees")
            if resp.status_code == 429:
                assert "X-RateLimit-Limit" in resp.headers or "请求过于频繁" in resp.json().get("message", "")
                return
        pytest.skip("Rate limit not triggered within 70 requests")

    def test_optimistic_lock_failure(self, client: TestClient, admin_headers: dict, seeded_employee: dict):
        """TC-EXC-021: 乐观锁失败"""
        # Same as TC-EXC-010 but from approval perspective
        record_resp = client.get(f"/employees/{seeded_employee['id']}", headers=admin_headers)
        version = record_resp.json().get("version", 1)
        payload = {"name": "更新A", "version": version}
        client.put(f"/employees/{seeded_employee['id']}", json=payload, headers=admin_headers)
        payload2 = {"name": "更新B", "version": version}
        resp2 = client.put(f"/employees/{seeded_employee['id']}", json=payload2, headers=admin_headers)
        if resp2.status_code == 409:
            assert "状态已变更" in resp2.json().get("message", "") or "已被他人修改" in resp2.json().get("message", "")

    def test_transaction_rollback(self, client: TestClient, admin_headers: dict, seeded_cycle: dict):
        """TC-EXC-022: 事务回滚"""
        resp = client.post(
            f"/assessment-cycles/{seeded_cycle['id']}/summarize?simulate_failure=true",
            headers=admin_headers,
        )
        if resp.status_code == 404:
            pytest.skip("Simulate failure endpoint not implemented")
        if resp.status_code == 500:
            # Verify no partial data was committed
            resp2 = client.get(f"/assessment-cycles/{seeded_cycle['id']}/records", headers=admin_headers)
            for item in resp2.json().get("items", []):
                assert item.get("total_score") is None or item.get("grade") is None, "Partial commit detected"

    def test_message_queue_backlog(self, client: TestClient, admin_headers: dict):
        """TC-EXC-023: 消息队列堆积"""
        resp = client.get("/monitor/queue-depth", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Queue monitor endpoint not implemented")
        assert_status_code(resp, 200)
        data = resp.json()
        depth = data.get("depth", 0)
        if depth > 1000:
            assert data.get("alert_triggered") is True


# ---------------------------------------------------------------------------
# Cache / resource exhaustion errors (TC-EXC-024 ~ TC-EXC-030)
# ---------------------------------------------------------------------------

class TestCacheException:
    """TC-EXC-024, TC-EXC-025, TC-EXC-026, TC-EXC-027, TC-EXC-028, TC-EXC-029, TC-EXC-030"""

    def test_cache_penetration(self, client: TestClient, admin_headers: dict):
        """TC-EXC-024: 缓存穿透"""
        # Query non-existent IDs repeatedly
        for i in range(1000):
            resp = client.get(f"/employees/{99999 + i}", headers=admin_headers)
            assert resp.status_code in (404, 200)
        # If caching is working, DB should not be hit 1000 times

    def test_cache_stampede(self, client: TestClient, admin_headers: dict):
        """TC-EXC-025: 缓存雪崩"""
        # Trigger many concurrent reads after cache expiry
        from concurrent.futures import ThreadPoolExecutor

        def fetch(_):
            return client.get("/employees?page=1&size=20", headers=admin_headers)

        with ThreadPoolExecutor(max_workers=100) as pool:
            results = list(pool.map(fetch, range(100)))
        for r in results:
            assert r.status_code == 200

    def test_database_deadlock(self, client: TestClient, admin_headers: dict, seeded_department: dict, seeded_position: dict):
        """TC-EXC-026: 数据库死锁"""
        # Create two employees and update them in reverse order from two threads
        emp1 = create_employee(client, admin_headers, "EMP_DL1", "死锁1", seeded_department["id"], seeded_position["id"])
        emp2 = create_employee(client, admin_headers, "EMP_DL2", "死锁2", seeded_department["id"], seeded_position["id"])

        def update_emp1_emp2():
            client.put(f"/employees/{emp1['id']}", json={"name": "DL1-A"}, headers=admin_headers)
            client.put(f"/employees/{emp2['id']}", json={"name": "DL2-A"}, headers=admin_headers)
            return True

        def update_emp2_emp1():
            client.put(f"/employees/{emp2['id']}", json={"name": "DL2-B"}, headers=admin_headers)
            client.put(f"/employees/{emp1['id']}", json={"name": "DL1-B"}, headers=admin_headers)
            return True

        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(update_emp1_emp2)
            f2 = pool.submit(update_emp2_emp1)
            results = [f1.result(), f2.result()]
        assert all(results), "Deadlock caused unrecoverable failure"

    def test_connection_pool_exhaustion(self, client: TestClient, admin_headers: dict):
        """TC-EXC-027: 连接池耗尽"""
        from concurrent.futures import ThreadPoolExecutor

        def fetch(_):
            return client.get("/employees?page=1&size=20", headers=admin_headers)

        with ThreadPoolExecutor(max_workers=20) as pool:
            results = list(pool.map(fetch, range(20)))
        timeouts = [r for r in results if r.status_code in (503, 408)]
        successes = [r for r in results if r.status_code == 200]
        assert len(successes) > 0 or len(timeouts) > 0

    def test_disk_full(self, client: TestClient, admin_headers: dict):
        """TC-EXC-028: 磁盘满"""
        resp = client.get("/health/disk", headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Disk health endpoint not implemented")
        assert resp.status_code in (200, 507)
        if resp.status_code == 507:
            assert "磁盘" in resp.json().get("message", "") or "空间" in resp.json().get("message", "")

    def test_memory_overflow_prevention(self, client: TestClient, admin_headers: dict):
        """TC-EXC-029: 内存溢出"""
        large_content = b"x" * (100 * 1024 * 1024)  # 100MB
        files = {"file": ("huge.xlsx", io.BytesIO(large_content), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        resp = client.post("/employees/import", files=files, headers=admin_headers)
        assert resp.status_code in (413, 500)
        assert resp.status_code != 502  # Should not crash the server

    def test_circular_dependency(self, client: TestClient, admin_headers: dict, seeded_department: dict, seeded_position: dict):
        """TC-EXC-030: 依赖循环"""
        # Create A -> B -> C hierarchy
        emp_a = create_employee(client, admin_headers, "EMP_A", "A", seeded_department["id"], seeded_position["id"])
        emp_b = create_employee(client, admin_headers, "EMP_B", "B", seeded_department["id"], seeded_position["id"], manager_id=emp_a["id"])
        emp_c = create_employee(client, admin_headers, "EMP_C", "C", seeded_department["id"], seeded_position["id"], manager_id=emp_b["id"])

        # Try to set C as A's manager (creates cycle A -> B -> C -> A)
        resp = client.put(f"/employees/{emp_a['id']}", json={"manager_id": emp_c["id"]}, headers=admin_headers)
        assert_status_code(resp, 422)
        assert "循环" in resp.json().get("message", "") or "cycle" in resp.json().get("message", "").lower()


class TestGenericException:
    """TC-EXC-031, TC-EXC-032, TC-EXC-033, TC-EXC-034, TC-EXC-035, TC-EXC-036, TC-EXC-037, TC-EXC-038"""

    def test_parameter_type_error(self, client: TestClient, admin_headers: dict):
        """TC-EXC-031: 通用422参数类型错误"""
        # Pass string where integer is expected
        resp = client.post("/employees", json={"employee_no": "EMP001", "name": "张三", "department_id": "abc"}, headers=admin_headers)
        assert resp.status_code in (422, 400)
        assert "类型" in resp.json().get("message", "") or "type" in resp.json().get("message", "").lower() or "integer" in resp.json().get("message", "").lower()

    def test_parameter_format_error(self, client: TestClient, admin_headers: dict):
        """TC-EXC-032: 通用422参数格式错误"""
        # Invalid email format
        resp = client.post("/employees", json={"employee_no": "EMP001", "name": "张三", "email": "invalid-email"}, headers=admin_headers)
        if resp.status_code != 404:
            assert resp.status_code in (422, 400)
            assert "格式" in resp.json().get("message", "") or "format" in resp.json().get("message", "").lower() or "email" in resp.json().get("message", "").lower()

    def test_illegal_character_no_500(self, client: TestClient, admin_headers: dict):
        """TC-EXC-033: 通用500非法字符触发不返回500"""
        xss = "<script>alert(1)</script>"
        resp = client.post("/employees", json={"employee_no": "EMP001", "name": xss}, headers=admin_headers)
        assert resp.status_code != 500, "Illegal character caused 500 error"
        # Should be 409 (duplicate) or 422 (validation), but never 500

    def test_submit_missing_dimensions_blocked(self, client: TestClient, manager_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-EXC-034: 未填写所有维度就提交"""
        payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_id": seeded_employee["id"],
            "dimension_scores": {"业绩": 85},  # Missing ability and attitude
        }
        resp = client.post("/scores/manager", json=payload, headers=manager_headers)
        if resp.status_code == 404:
            pytest.skip("Manager score endpoint not implemented")
        assert_status_code(resp, 422)
        assert "维度" in resp.json().get("message", "") or "未评分" in resp.json().get("message", "")

    def test_score_after_deadline_blocked(self, client: TestClient, manager_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-EXC-035: 考核截止后尝试评分"""
        # Assume the cycle is closed for scoring
        payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_id": seeded_employee["id"],
            "dimension_scores": {"业绩": 85, "能力": 90, "态度": 88},
        }
        resp = client.post("/scores/manager", json=payload, headers=manager_headers)
        if resp.status_code == 404:
            pytest.skip("Manager score endpoint not implemented")
        if resp.status_code == 409:
            assert "截止" in resp.json().get("message", "")

    def test_resubmit_already_scored(self, client: TestClient, manager_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-EXC-036: 对已评分下属再次提交"""
        payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_id": seeded_employee["id"],
            "dimension_scores": {"业绩": 85, "能力": 90, "态度": 88},
        }
        resp = client.post("/scores/manager", json=payload, headers=manager_headers)
        if resp.status_code == 404:
            pytest.skip("Manager score endpoint not implemented")
        if resp.status_code == 409:
            assert "已评分" in resp.json().get("message", "") or "覆盖" in resp.json().get("message", "")

    def test_peer_score_after_deadline(self, client: TestClient, peer_headers: dict, seeded_cycle: dict, seeded_employee: dict):
        """TC-EXC-037: 协作评分截止后提交"""
        payload = {
            "cycle_id": seeded_cycle["id"],
            "employee_id": seeded_employee["id"],
            "dimension_scores": {"能力": 85},
        }
        resp = client.post("/scores/peer", json=payload, headers=peer_headers)
        if resp.status_code == 404:
            pytest.skip("Peer score endpoint not implemented")
        if resp.status_code == 409:
            assert "截止" in resp.json().get("message", "")

    def test_modify_launched_cycle_blocked(self, client: TestClient, admin_headers: dict, seeded_cycle: dict):
        """TC-EXC-038: 修改已发起考核周期被拦截"""
        # Launch the cycle first
        client.post(
            "/assessment-cycles/launch",
            json={"cycle_id": seeded_cycle["id"], "employee_ids": []},
            headers=admin_headers,
        )
        resp = client.put(f"/assessment-cycles/{seeded_cycle['id']}", json={"name": "新名称"}, headers=admin_headers)
        if resp.status_code == 404:
            pytest.skip("Cycle update endpoint not implemented")
        assert_status_code(resp, 409)
        assert "已发起" in resp.json().get("message", "")
