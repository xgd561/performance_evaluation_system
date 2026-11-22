"""鉴权兼容层。

生产代码统一使用 app.auth 的鉴权实现；本模块保留历史函数签名，
密钥/算法/密码哈希/token 解码均委托 app.auth，避免两套实现分叉。
"""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.auth import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token as _auth_create_access_token,
    decode_token as _auth_decode_token,
    get_password_hash as _auth_get_password_hash,
    verify_password as _auth_verify_password,
)
from app.database import get_db
from app.models import User

security = HTTPBearer(auto_error=False)


def create_access_token(user_id: int, role: str) -> str:
    """
    创建 JWT access token（历史签名：按 user_id + role 编码）

    Args:
        user_id: 用户 ID
        role: 用户角色

    Returns:
        str: 编码后的 JWT 字符串
    """
    return _auth_create_access_token({"sub": str(user_id), "role": role})


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    校验明文密码与哈希密码是否匹配

    Args:
        plain_password: 明文密码
        hashed_password: bcrypt 哈希后的密码

    Returns:
        bool: 是否匹配
    """
    return _auth_verify_password(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    使用 bcrypt 对密码进行哈希

    Args:
        password: 明文密码

    Returns:
        str: 哈希后的密码字符串
    """
    return _auth_get_password_hash(password)


def decode_token(token: str) -> Optional[dict]:
    """
    解码并验证 JWT token

    Args:
        token: JWT 字符串

    Returns:
        Optional[dict]: 解码后的 payload，验证失败返回 None
    """
    return _auth_decode_token(token)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI 依赖：从 Authorization Header 提取并验证 Token

    Args:
        credentials: HTTP Bearer 凭据
        db: 数据库 Session

    Returns:
        User: 当前登录用户对象

    Raises:
        HTTPException: 401 未认证或 403 无权限
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户已被禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
