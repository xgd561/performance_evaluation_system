from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from typing import Any


class BizError(Exception):
    """
    业务异常基类
    统一结构: {code, message, data}
    支持 HTTP 状态码与业务码分离
    """
    def __init__(
        self,
        message: str = "业务错误",
        code: int = 1000,
        data: Any = None,
        status_code: int = 400,
    ):
        self.message = message
        self.code = code
        self.data = data
        self.status_code = status_code
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "data": self.data,
        }


class AuthError(BizError):
    """认证/授权异常（HTTP 401/403）"""
    def __init__(
        self,
        message: str = "认证失败",
        code: int = 2000,
        data: Any = None,
        status_code: int = 401,
    ):
        super().__init__(
            message=message,
            code=code,
            data=data,
            status_code=status_code,
        )


class NotFoundError(BizError):
    """资源不存在异常（HTTP 404）"""
    def __init__(
        self,
        message: str = "资源不存在",
        code: int = 3000,
        data: Any = None,
        status_code: int = 404,
    ):
        super().__init__(
            message=message,
            code=code,
            data=data,
            status_code=status_code,
        )


class ValidationError(BizError):
    """参数校验异常（HTTP 422）"""
    def __init__(
        self,
        message: str = "参数校验失败",
        code: int = 4000,
        data: Any = None,
        status_code: int = 422,
    ):
        super().__init__(
            message=message,
            code=code,
            data=data,
            status_code=status_code,
        )


def register_exception_handlers(app: FastAPI) -> None:
    """
    注册全局异常处理器到 FastAPI 应用
    所有业务异常返回统一 JSON 结构: {code, message, data}
    """

    @app.exception_handler(BizError)
    async def biz_error_handler(request: Request, exc: BizError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "code": 5000,
                "message": "服务器内部错误",
                "data": None,
            },
        )
