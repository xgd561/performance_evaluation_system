import os
import sys
import pytest
import json
import unittest.mock as mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, OperationLog
from app.utils.audit_logger import (
    log_operation,
    AuditLogMiddleware,
    _extract_token_user_id,
    _extract_target_info,
)

# 创建测试用内存数据库
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
Base.metadata.create_all(bind=test_engine)


class TestLogOperation:
    """测试 log_operation 显式记录"""

    def test_log_with_old_and_new_value(self):
        db = TestSessionLocal()
        log = log_operation(
            db=db,
            user_id=1,
            action="update",
            target_type="employee",
            target_id=2,
            old_value={"name": "old"},
            new_value={"name": "new"},
            ip_address="127.0.0.1",
        )
        assert log.user_id == 1
        assert log.action == "update"
        assert log.target_type == "employee"
        assert log.target_id == 2
        assert json.loads(log.old_value) == {"name": "old"}
        assert json.loads(log.new_value) == {"name": "new"}
        assert log.ip_address == "127.0.0.1"

    def test_log_with_none_values(self):
        db = TestSessionLocal()
        log = log_operation(
            db=db,
            user_id=1,
            action="delete",
            target_type="employee",
            target_id=2,
        )
        assert log.old_value is None
        assert log.new_value is None

    def test_log_complex_json(self):
        db = TestSessionLocal()
        log = log_operation(
            db=db,
            user_id=1,
            action="create",
            old_value={"grades": {"A": {"min": 90}}},
            new_value={"grades": {"A": {"min": 95}}},
        )
        assert json.loads(log.old_value)["grades"]["A"]["min"] == 90
        assert json.loads(log.new_value)["grades"]["A"]["min"] == 95


class TestExtractTargetInfo:
    """测试 URL 解析"""

    def test_create_resource(self):
        req = mock.Mock()
        req.method = "POST"
        req.url.path = "/api/v1/employees"
        req.headers = {}
        action, target_type, target_id = _extract_target_info(req)
        assert action == "create"
        assert target_type == "employees"
        assert target_id is None

    def test_update_resource_with_id(self):
        req = mock.Mock()
        req.method = "PUT"
        req.url.path = "/api/v1/employees/123"
        req.headers = {}
        action, target_type, target_id = _extract_target_info(req)
        assert action == "update"
        assert target_type == "employees"
        assert target_id == 123

    def test_delete_resource(self):
        req = mock.Mock()
        req.method = "DELETE"
        req.url.path = "/api/v1/employees/456"
        req.headers = {}
        action, target_type, target_id = _extract_target_info(req)
        assert action == "delete"
        assert target_type == "employees"
        assert target_id == 456

    def test_non_api_path(self):
        req = mock.Mock()
        req.method = "POST"
        req.url.path = "/auth/login"
        req.headers = {}
        action, target_type, target_id = _extract_target_info(req)
        assert action == "create"
        assert target_type == "auth"
        assert target_id is None

    def test_nested_path(self):
        req = mock.Mock()
        req.method = "POST"
        req.url.path = "/api/v1/employees/123/positions"
        req.headers = {}
        action, target_type, target_id = _extract_target_info(req)
        assert action == "create"
        assert target_type == "employees"
        assert target_id == 123


class TestExtractTokenUserId:
    """测试 Token 解析"""

    def test_no_auth_header(self):
        req = mock.Mock()
        req.headers = {}
        assert _extract_token_user_id(req) is None

    def test_invalid_token(self):
        req = mock.Mock()
        req.headers = {"Authorization": "Bearer invalid_token"}
        assert _extract_token_user_id(req) is None

    def test_valid_token(self):
        from app.core.security import create_access_token
        token = create_access_token(user_id=42, role="admin")
        req = mock.Mock()
        req.headers = {"Authorization": f"Bearer {token}"}
        assert _extract_token_user_id(req) == 42


class TestAuditLogMiddleware:
    """测试 middleware 拦截"""

    @pytest.fixture
    def test_app(self):
        app = FastAPI()

        @app.post("/api/v1/employees")
        def create_employee(request: Request):
            return {"id": 1, "name": "test"}

        @app.put("/api/v1/employees/{id}")
        def update_employee(id: int, request: Request):
            return {"id": id, "name": "updated"}

        @app.delete("/api/v1/employees/{id}")
        def delete_employee(id: int, request: Request):
            return {"message": "deleted"}

        @app.get("/api/v1/employees")
        def list_employees(request: Request):
            return [{"id": 1}]

        app.add_middleware(AuditLogMiddleware)

        return TestClient(app)

    def test_post_request_logged(self, test_app):
        with mock.patch("app.utils.audit_logger.log_operation") as mock_log:
            response = test_app.post("/api/v1/employees", json={"name": "test"})
            assert response.status_code == 200
            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args.kwargs
            assert call_kwargs["action"] == "create"
            assert call_kwargs["target_type"] == "employees"

    def test_put_request_logged(self, test_app):
        with mock.patch("app.utils.audit_logger.log_operation") as mock_log:
            response = test_app.put("/api/v1/employees/123", json={"name": "updated"})
            assert response.status_code == 200
            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args.kwargs
            assert call_kwargs["action"] == "update"
            assert call_kwargs["target_id"] == 123

    def test_delete_request_logged(self, test_app):
        with mock.patch("app.utils.audit_logger.log_operation") as mock_log:
            response = test_app.delete("/api/v1/employees/456")
            assert response.status_code == 200
            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args.kwargs
            assert call_kwargs["action"] == "delete"
            assert call_kwargs["target_id"] == 456

    def test_get_request_not_logged(self, test_app):
        with mock.patch("app.utils.audit_logger.log_operation") as mock_log:
            response = test_app.get("/api/v1/employees")
            assert response.status_code == 200
            mock_log.assert_not_called()

    def test_post_with_token(self, test_app):
        from app.core.security import create_access_token
        token = create_access_token(user_id=99, role="admin")
        with mock.patch("app.utils.audit_logger.log_operation") as mock_log:
            response = test_app.post(
                "/api/v1/employees",
                json={"name": "test"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args.kwargs
            assert call_kwargs["user_id"] == 99

    def test_error_response_not_logged(self, test_app):
        with mock.patch("app.utils.audit_logger.log_operation") as mock_log:
            # 触发一个 404
            response = test_app.post("/api/v1/not-found", json={"name": "test"})
            assert response.status_code == 404
            mock_log.assert_not_called()

    def test_middleware_body_readable_by_endpoint(self, test_app):
        """验证 middleware 读取 body 后，endpoint 仍可正常读取"""
        @test_app.app.post("/api/v1/body-test")
        async def body_test(request: Request):
            import json

            body = await request.body()
            data = json.loads(body)
            return {"received": data}

        # 重新创建 TestClient 因为添加了新 route
        client = TestClient(test_app.app)
        with mock.patch("app.utils.audit_logger.log_operation"):
            response = client.post("/api/v1/body-test", json={"key": "value"})
            assert response.status_code == 200
            assert response.json() == {"received": {"key": "value"}}


class TestAuditLogMiddlewareIntegration:
    """测试 middleware 与数据库集成"""

    @pytest.fixture
    def test_app_db(self):
        app = FastAPI()

        @app.post("/api/v1/employees")
        def create_employee(request: Request):
            return {"id": 1, "name": "test"}

        app.add_middleware(AuditLogMiddleware)

        return TestClient(app)

    def test_post_writes_to_db(self, test_app_db):
        # 清空测试数据库中的日志
        db = TestSessionLocal()
        db.query(OperationLog).delete()
        db.commit()

        with mock.patch("app.utils.audit_logger.SessionLocal", TestSessionLocal):
            response = test_app_db.post("/api/v1/employees", json={"name": "test"})
            assert response.status_code == 200

        # 验证数据库写入
        db = TestSessionLocal()
        logs = db.query(OperationLog).all()
        assert len(logs) == 1
        assert logs[0].action == "create"
        assert logs[0].target_type == "employees"
        assert logs[0].new_value is not None
        assert json.loads(logs[0].new_value)["name"] == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
