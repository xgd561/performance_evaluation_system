import json
import logging
from typing import Any, Optional

from starlette.requests import Request
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import OperationLog
from app.core.security import decode_token

logger = logging.getLogger(__name__)


def log_operation(
    db: Session,
    user_id: int,
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    old_value: Optional[Any] = None,
    new_value: Optional[Any] = None,
    ip_address: Optional[str] = None,
) -> OperationLog:
    """
    手动记录操作日志。

    Args:
        db: 数据库 Session
        user_id: 操作人 ID
        action: 操作动作（如 create, update, delete）
        target_type: 操作对象类型（如 employee, cycle）
        target_id: 操作对象 ID
        old_value: 变更前的值（JSON 可序列化）
        new_value: 变更后的值（JSON 可序列化）
        ip_address: 客户端 IP

    Returns:
        OperationLog: 创建的记录
    """
    log = OperationLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        old_value=json.dumps(old_value, ensure_ascii=False, default=str) if old_value is not None else None,
        new_value=json.dumps(new_value, ensure_ascii=False, default=str) if new_value is not None else None,
        ip_address=ip_address,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def _extract_token_user_id(request: Request) -> Optional[int]:
    """从请求头中提取 token 并解析 user_id"""
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    token = auth.replace("Bearer ", "")
    payload = decode_token(token)
    if payload is None:
        return None
    try:
        return int(payload.get("sub"))
    except (ValueError, TypeError):
        return None


def _extract_target_info(request: Request) -> tuple:
    """从 URL 推断 action 和 target_type"""
    path = request.url.path
    parts = [p for p in path.split("/") if p]

    # 找资源段（优先取 /api/v1/ 后的第一段）
    resource = None
    if len(parts) >= 2 and parts[0] == "api":
        resource = parts[2] if len(parts) > 2 else None
    else:
        resource = parts[0] if parts else None

    # 判断 action
    method = request.method
    if method == "POST":
        action = "create"
    elif method == "PUT":
        action = "update"
    elif method == "DELETE":
        action = "delete"
    else:
        action = method.lower()

    # 尝试提取 target_id（URL 最后一个纯数字段）
    target_id = None
    for part in reversed(parts):
        if part.isdigit():
            target_id = int(part)
            break

    return action, resource, target_id


class AuditLogMiddleware:
    """纯 ASGI Middleware：自动拦截 POST/PUT/DELETE 请求并记录操作日志。"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        method = request.method

        if method not in ("POST", "PUT", "DELETE"):
            await self.app(scope, receive, send)
            return

        # 读取 request body
        body = await request.body()

        # 解析 request body
        request_body = None
        if body:
            try:
                request_body = json.loads(body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                request_body = body.decode("utf-8", errors="ignore")

        # 重新包装 receive，使下游 endpoint 可再次读取 body
        async def receive_with_body():
            return {"type": "http.request", "body": body}

        # 获取操作信息
        user_id = _extract_token_user_id(request)
        action, target_type, target_id = _extract_target_info(request)
        ip_address = request.client.host if request.client else None

        # 捕获 response
        response_started = False
        response_status = None
        response_body = b""

        async def send_with_capture(message):
            nonlocal response_started, response_status, response_body
            if message["type"] == "http.response.start":
                response_started = True
                response_status = message.get("status", 200)
                await send(message)
            elif message["type"] == "http.response.body":
                response_body += message.get("body", b"")
                await send(message)
            else:
                await send(message)

        await self.app(scope, receive_with_body, send_with_capture)

        # 只记录成功的请求（2xx）
        if response_started and response_status is not None and 200 <= response_status < 300:
            # 解析 response body
            resp_body = None
            if response_body:
                try:
                    resp_body = json.loads(response_body)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    resp_body = response_body.decode("utf-8", errors="ignore")

            try:
                db = SessionLocal()
                try:
                    log_operation(
                        db=db,
                        user_id=user_id or 0,
                        action=action,
                        target_type=target_type,
                        target_id=target_id,
                        old_value=request_body,
                        new_value=resp_body,
                        ip_address=ip_address,
                    )
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Failed to write audit log: {e}")
