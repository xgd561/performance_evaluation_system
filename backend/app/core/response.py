import json
from typing import Any, Generic, List, Optional, TypeVar
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """统一 API 响应模型"""
    code: int = Field(..., description="业务状态码")
    message: str = Field(..., description="提示信息")
    data: Optional[T] = Field(None, description="业务数据")
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"), description="响应时间戳")

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S"),
        }
    )


class PaginationData(BaseModel, Generic[T]):
    """分页数据结构"""
    items: List[T] = Field(..., description="当前页数据列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页条数")


ENVELOPE_KEYS = frozenset({"code", "message", "data"})

# 不参与统一包装的路径：
# - 健康检查是运维探针契约（脚本/监控直接读 {"status": "ok"}），不随业务响应变化
# - OpenAPI 文档接口若被包装会导致 Swagger UI 无法加载
EXCLUDED_PATHS = frozenset({
    "/health",
    "/api/v1/health",
    "/openapi.json",
    "/docs",
    "/redoc",
    "/docs/oauth2-redirect",
})


def is_envelope(payload: Any) -> bool:
    """判断 payload 是否已经是 {code, message, data} 信封形态（用于避免重复包装）。"""
    return (
        isinstance(payload, dict)
        and ENVELOPE_KEYS.issubset(payload.keys())
        and isinstance(payload.get("code"), int)
        and isinstance(payload.get("message"), str)
    )


def success_response(data: Any = None, message: str = "操作成功") -> dict:
    """
    构造成功响应字典，结构与 BaseResponse 对齐（含 timestamp）。

    Args:
        data: 业务数据，任意类型
        message: 提示信息

    Returns:
        dict: {code, message, data, timestamp}
    """
    return {
        "code": 0,
        "message": message,
        "data": data,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def error_response(code: int = 1000, message: str = "业务错误", data: Any = None) -> dict:
    """
    构造错误响应字典。

    Args:
        code: 业务错误码
        message: 错误提示
        data: 附加数据（如校验失败的字段详情）

    Returns:
        dict: {code, message, data, timestamp}
    """
    return {
        "code": code,
        "message": message,
        "data": data,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def paginate_response(
    data_list: list,
    total: int,
    page: int,
    page_size: int,
    message: str = "查询成功",
) -> dict:
    """
    构造分页成功响应字典。

    Args:
        data_list: 当前页数据列表
        total: 总记录数
        page: 当前页码
        page_size: 每页条数
        message: 提示信息

    Returns:
        dict: {code, message, data: {list, total, page, page_size}, timestamp}
    """
    return {
        "code": 0,
        "message": message,
        "data": {
            "list": data_list,
            "total": total,
            "page": page,
            "page_size": page_size,
        },
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


class UnifiedResponseMiddleware:
    """把成功的 JSON 响应统一包装为 {code, message, data, timestamp}。

    策略（与前端 request.js 的解包约定对应）：
    - 只处理 2xx 且 Content-Type 为 JSON 的响应；PDF/Excel 等二进制流原样透传
    - 已是信封形态的响应不重复包装，保证幂等
    - 错误响应保留原 HTTP 状态码与既有 {code, message} 结构，不做包装
    - EXCLUDED_PATHS 中的路径（健康检查、OpenAPI 文档）不参与包装
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or scope.get("path") in EXCLUDED_PATHS:
            await self.app(scope, receive, send)
            return

        start: dict = {}
        chunks: List[bytes] = []

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                start["message"] = message
                return
            if message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))
                if message.get("more_body"):
                    return
                await self._emit(start.get("message"), b"".join(chunks), send)
                return
            await send(message)

        await self.app(scope, receive, send_wrapper)

    @staticmethod
    async def _emit(start, body: bytes, send):
        if start is None:
            return

        status = start.get("status", 200)
        headers = list(start.get("headers", []))

        async def passthrough():
            await send(start)
            await send({"type": "http.response.body", "body": body})

        # 仅包装成功响应
        if not 200 <= status < 300 or not body:
            await passthrough()
            return

        content_type = ""
        for key, value in headers:
            if key.lower() == b"content-type":
                content_type = value.decode("latin-1")
                break
        if "json" not in content_type.lower():
            await passthrough()
            return

        try:
            payload = json.loads(body)
        except ValueError:
            await passthrough()
            return

        if is_envelope(payload):
            await passthrough()
            return

        wrapped = success_response(payload)
        new_body = json.dumps(wrapped, ensure_ascii=False, default=str).encode("utf-8")
        new_headers = [(k, v) for k, v in headers if k.lower() != b"content-length"]
        new_headers.append((b"content-length", str(len(new_body)).encode("latin-1")))

        await send({"type": "http.response.start", "status": status, "headers": new_headers})
        await send({"type": "http.response.body", "body": new_body})
