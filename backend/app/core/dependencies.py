from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.security import get_current_user, security
from app.database import get_db
from app.models import User


def get_current_user_or_403(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    通用依赖：获取当前用户，未认证或用户无效时返回 403。
    与 get_current_user 的区别：使用 403 状态码（适用于不允许匿名访问的接口）。
    """
    try:
        return get_current_user(credentials, db)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足",
        )


def require_role(*roles: str):
    """
    创建 FastAPI Dependency，要求当前用户角色在允许列表中。

    使用方式：
        @router.get("/admin-only", dependencies=[Depends(require_role("admin"))])
        def admin_endpoint(): ...

    Args:
        *roles: 允许访问的角色列表

    Returns:
        Dependency: FastAPI 依赖函数
    """
    def _role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="当前角色无权访问该资源",
            )
        return current_user
    return _role_checker
