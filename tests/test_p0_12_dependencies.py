import os
import sys
import pytest
import unittest.mock as mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.dependencies import (
    get_current_user_or_403,
    require_role,
)
from app.core.security import create_access_token


class MockUser:
    def __init__(self, id=1, role="admin", is_active=True):
        self.id = id
        self.role = role
        self.is_active = is_active


class TestGetCurrentUserOr403:
    """验证 get_current_user_or_403 通用依赖"""

    def test_valid_token_returns_user(self):
        token = create_access_token(user_id=1, role="admin")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        mock_user = MockUser(id=1, role="admin")
        mock_db = mock.Mock()

        with mock.patch(
            "app.core.dependencies.get_current_user", return_value=mock_user
        ):
            result = get_current_user_or_403(creds, mock_db)
            assert result.id == 1

    def test_no_credentials_raises_403(self):
        mock_db = mock.Mock()
        with mock.patch(
            "app.core.dependencies.get_current_user",
            side_effect=HTTPException(status_code=401),
        ):
            with pytest.raises(HTTPException) as exc_info:
                get_current_user_or_403(None, mock_db)
            assert exc_info.value.status_code == 403

    def test_invalid_token_raises_403(self):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad_token")
        mock_db = mock.Mock()
        with mock.patch(
            "app.core.dependencies.get_current_user",
            side_effect=HTTPException(status_code=401),
        ):
            with pytest.raises(HTTPException) as exc_info:
                get_current_user_or_403(creds, mock_db)
            assert exc_info.value.status_code == 403

    def test_inactive_user_raises_403(self):
        token = create_access_token(user_id=1, role="admin")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        mock_db = mock.Mock()
        with mock.patch(
            "app.core.dependencies.get_current_user",
            side_effect=HTTPException(status_code=401, detail="用户已被禁用"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                get_current_user_or_403(creds, mock_db)
            assert exc_info.value.status_code == 403


class TestRequireRole:
    """验证 require_role 角色权限守卫"""

    def test_matching_single_role(self):
        checker = require_role("admin")
        mock_user = MockUser(id=1, role="admin")
        result = checker(mock_user)
        assert result.id == 1
        assert result.role == "admin"

    def test_matching_one_of_multiple_roles(self):
        checker = require_role("admin", "hr")
        mock_user = MockUser(id=2, role="hr")
        result = checker(mock_user)
        assert result.role == "hr"

    def test_non_matching_role_raises_403(self):
        checker = require_role("admin")
        mock_user = MockUser(id=3, role="employee")
        with pytest.raises(HTTPException) as exc_info:
            checker(mock_user)
        assert exc_info.value.status_code == 403

    def test_non_matching_among_multiple_roles_raises_403(self):
        checker = require_role("admin", "hr")
        mock_user = MockUser(id=4, role="employee")
        with pytest.raises(HTTPException) as exc_info:
            checker(mock_user)
        assert exc_info.value.status_code == 403

    def test_manager_role_allowed(self):
        checker = require_role("manager", "admin")
        mock_user = MockUser(id=5, role="manager")
        result = checker(mock_user)
        assert result.role == "manager"

    def test_executive_role_allowed(self):
        checker = require_role("executive")
        mock_user = MockUser(id=6, role="executive")
        result = checker(mock_user)
        assert result.role == "executive"

    def test_hr_role_allowed(self):
        checker = require_role("admin", "hr", "manager")
        mock_user = MockUser(id=7, role="hr")
        result = checker(mock_user)
        assert result.role == "hr"

    def test_403_detail_message(self):
        checker = require_role("admin")
        mock_user = MockUser(id=8, role="employee")
        with pytest.raises(HTTPException) as exc_info:
            checker(mock_user)
        assert "无权" in exc_info.value.detail


class TestRequireRoleAsFastAPIDependency:
    """验证 require_role 在 FastAPI 依赖链中的行为"""

    def test_dependency_callable_signature(self):
        """require_role 返回可调用对象，可作为 Depends 参数"""
        checker = require_role("admin")
        assert callable(checker)
        import inspect

        sig = inspect.signature(checker)
        params = list(sig.parameters.keys())
        assert "current_user" in params

    def test_role_attribute_accessed(self):
        """确保 checker 读取了 user.role 属性"""
        checker = require_role("admin")
        mock_user = mock.Mock()
        mock_user.role = "admin"
        result = checker(mock_user)
        assert result.role == "admin"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
