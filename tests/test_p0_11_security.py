import os
import sys
import pytest
import unittest.mock as mock
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
    decode_token,
    get_current_user,
)


class TestPasswordHash:
    """验证 bcrypt 密码哈希与校验"""

    def test_hash_password_returns_bcrypt(self):
        hashed = get_password_hash("Password123")
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        hashed = get_password_hash("Password123")
        assert verify_password("Password123", hashed) is True

    def test_verify_password_incorrect(self):
        hashed = get_password_hash("Password123")
        assert verify_password("WrongPassword", hashed) is False

    def test_different_passwords_different_hashes(self):
        h1 = get_password_hash("Password123")
        h2 = get_password_hash("Password123")
        assert h1 != h2
        assert verify_password("Password123", h1)
        assert verify_password("Password123", h2)


class TestJWT:
    """验证 JWT 创建与解码"""

    def test_create_access_token(self):
        token = create_access_token(user_id=1, role="admin")
        assert isinstance(token, str)
        assert "." in token

    def test_decode_token(self):
        token = create_access_token(user_id=1, role="admin")
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "1"
        assert payload["role"] == "admin"

    def test_token_expiration(self):
        token = create_access_token(user_id=1, role="admin")
        payload = decode_token(token)
        assert "exp" in payload
        exp = datetime.utcfromtimestamp(payload["exp"])
        assert exp > datetime.utcnow()
        assert exp <= datetime.utcnow() + timedelta(hours=2, minutes=1)

    def test_decode_invalid_token(self):
        assert decode_token("invalid.token.here") is None

    def test_decode_empty_token(self):
        assert decode_token("") is None


class TestGetCurrentUser:
    """验证 get_current_user 依赖项"""

    def test_no_credentials(self):
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(None, mock.Mock())
        assert exc_info.value.status_code == 401

    def test_invalid_token(self):
        creds = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid_token"
        )
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(creds, mock.Mock())
        assert exc_info.value.status_code == 401

    def test_valid_token_user_exists(self):
        token = create_access_token(user_id=1, role="admin")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        mock_user = mock.Mock()
        mock_user.id = 1
        mock_user.is_active = True

        mock_db = mock.Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = get_current_user(creds, mock_db)
        assert result.id == 1

    def test_valid_token_user_not_found(self):
        token = create_access_token(user_id=999, role="admin")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        mock_db = mock.Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(creds, mock_db)
        assert exc_info.value.status_code == 401

    def test_valid_token_user_inactive(self):
        token = create_access_token(user_id=1, role="admin")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        mock_user = mock.Mock()
        mock_user.id = 1
        mock_user.is_active = False

        mock_db = mock.Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(creds, mock_db)
        assert exc_info.value.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
