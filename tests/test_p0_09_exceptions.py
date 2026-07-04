import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import BizError, AuthError, NotFoundError, ValidationError, register_exception_handlers


class TestExceptionClasses:
    """验证异常类可实例化、可抛出、属性正确"""

    def test_biz_error_default(self):
        exc = BizError()
        assert exc.message == "业务错误"
        assert exc.code == 1000
        assert exc.data is None
        assert exc.status_code == 400
        assert str(exc) == "业务错误"

    def test_biz_error_custom(self):
        exc = BizError(message="自定义错误", code=9999, data={"field": "name"}, status_code=403)
        assert exc.message == "自定义错误"
        assert exc.code == 9999
        assert exc.data == {"field": "name"}
        assert exc.status_code == 403

    def test_biz_error_to_dict(self):
        exc = BizError(message="测试", code=1234, data={"key": "value"})
        assert exc.to_dict() == {
            "code": 1234,
            "message": "测试",
            "data": {"key": "value"},
        }

    def test_auth_error_default(self):
        exc = AuthError()
        assert exc.message == "认证失败"
        assert exc.code == 2000
        assert exc.status_code == 401

    def test_not_found_error_default(self):
        exc = NotFoundError()
        assert exc.message == "资源不存在"
        assert exc.code == 3000
        assert exc.status_code == 404

    def test_validation_error_default(self):
        exc = ValidationError()
        assert exc.message == "参数校验失败"
        assert exc.code == 4000
        assert exc.status_code == 422

    def test_raise_and_catch_biz_error(self):
        with pytest.raises(BizError) as exc_info:
            raise BizError("操作失败", code=1001)
        assert exc_info.value.message == "操作失败"
        assert exc_info.value.code == 1001

    def test_raise_and_catch_auth_error(self):
        with pytest.raises(AuthError) as exc_info:
            raise AuthError("Token 已过期")
        assert exc_info.value.message == "Token 已过期"

    def test_raise_and_catch_not_found_error(self):
        with pytest.raises(NotFoundError) as exc_info:
            raise NotFoundError("员工不存在")
        assert exc_info.value.message == "员工不存在"

    def test_raise_and_catch_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("姓名不能为空")
        assert exc_info.value.message == "姓名不能为空"

    def test_auth_error_is_biz_error_subclass(self):
        assert issubclass(AuthError, BizError)
        exc = AuthError()
        assert isinstance(exc, BizError)

    def test_not_found_error_is_biz_error_subclass(self):
        assert issubclass(NotFoundError, BizError)

    def test_validation_error_is_biz_error_subclass(self):
        assert issubclass(ValidationError, BizError)


class TestExceptionHandlers:
    """验证 FastAPI 全局 exception handler 返回统一 JSON 结构"""

    @pytest.fixture
    def client(self):
        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/biz-error")
        def raise_biz_error():
            raise BizError(message="业务错误测试", code=1111, status_code=400)

        @app.get("/auth-error")
        def raise_auth_error():
            raise AuthError(message="未登录", code=2001, status_code=401)

        @app.get("/not-found")
        def raise_not_found():
            raise NotFoundError(message="记录不存在", code=3001, status_code=404)

        @app.get("/validation")
        def raise_validation():
            raise ValidationError(message="参数非法", code=4001, status_code=422)

        @app.get("/general")
        def raise_general():
            raise ValueError("未知错误")

        return TestClient(app, raise_server_exceptions=False)

    def test_biz_error_handler(self, client):
        resp = client.get("/biz-error")
        assert resp.status_code == 400
        assert resp.json() == {
            "code": 1111,
            "message": "业务错误测试",
            "data": None,
        }

    def test_auth_error_handler(self, client):
        resp = client.get("/auth-error")
        assert resp.status_code == 401
        assert resp.json() == {
            "code": 2001,
            "message": "未登录",
            "data": None,
        }

    def test_not_found_error_handler(self, client):
        resp = client.get("/not-found")
        assert resp.status_code == 404
        assert resp.json() == {
            "code": 3001,
            "message": "记录不存在",
            "data": None,
        }

    def test_validation_error_handler(self, client):
        resp = client.get("/validation")
        assert resp.status_code == 422
        assert resp.json() == {
            "code": 4001,
            "message": "参数非法",
            "data": None,
        }

    def test_general_exception_handler(self, client):
        resp = client.get("/general")
        assert resp.status_code == 500
        assert resp.json() == {
            "code": 5000,
            "message": "服务器内部错误",
            "data": None,
        }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
