from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    require_role,
)
from app.schemas import (
    LoginRequest,
    LoginResponse,
    StandardResponse,
    ChangePasswordRequest,
    RefreshTokenRequest,
)
from app.models import User

router = APIRouter()
security = HTTPBearer()

# In-memory rate limit store for failed login attempts
_failed_attempts = {}


def _check_rate_limit(username: str):
    now = datetime.utcnow()
    attempts = _failed_attempts.get(username, {"count": 0, "last_attempt": now})
    if attempts["count"] >= 5:
        lockout_end = attempts["last_attempt"] + timedelta(minutes=30)
        if now < lockout_end:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="密码错误次数过多，请30分钟后再试",
            )
        else:
            attempts["count"] = 0
    return attempts


def _record_failed_attempt(username: str):
    now = datetime.utcnow()
    attempts = _failed_attempts.get(username, {"count": 0, "last_attempt": now})
    attempts["count"] += 1
    attempts["last_attempt"] = now
    _failed_attempts[username] = attempts


def _clear_failed_attempts(username: str):
    if username in _failed_attempts:
        del _failed_attempts[username]


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    _check_rate_limit(req.username)

    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        _record_failed_attempt(req.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    _clear_failed_attempts(req.username)

    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})

    result = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "name": user.employee.name if user.employee else user.username,
        },
    }
    return result


@router.post("/refresh")
def refresh_token(req: RefreshTokenRequest):
    payload = decode_token(req.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token已过期或无效",
        )
    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token无效",
        )
    access_token = create_access_token(data={"sub": username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "name": user.employee.name if user.employee else user.username,
        "role": user.role,
        "employee_id": user.employee_id,
    }


@router.put("/password")
def change_password(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误",
        )
    if req.old_password == req.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码不能与旧密码相同",
        )
    if len(req.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="密码长度过短，请使用更复杂的密码",
        )
    # Weak password check: pure digits or pure letters
    if req.new_password.isdigit() or req.new_password.isalpha():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="密码复杂度不足，请使用字母+数字组合",
        )
    user.password_hash = get_password_hash(req.new_password)
    user.is_first_login = False
    db.commit()
    return {"code": 200, "message": "密码修改成功"}


@router.post("/change-password")
def change_password_post(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return change_password(req, user, db)


@router.post("/logout")
def logout(user: User = Depends(get_current_user)):
    return {"code": 200, "message": "退出成功"}
