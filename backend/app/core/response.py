from typing import Any, Generic, List, Optional, TypeVar
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """统一 API 响应模型"""
    code: int = Field(..., description="业务状态码")
    message: str = Field(..., description="提示信息")
    data: Optional[T] = Field(None, description="业务数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")

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


def success_response(data: Any = None, message: str = "操作成功") -> dict:
    """
    构造成功响应字典

    Args:
        data: 业务数据，任意类型
        message: 提示信息

    Returns:
        dict: {code, message, data}
    """
    return {
        "code": 0,
        "message": message,
        "data": data,
    }


def error_response(code: int = 1000, message: str = "业务错误", data: Any = None) -> dict:
    """
    构造错误响应字典

    Args:
        code: 业务错误码
        message: 错误提示
        data: 附加数据（如校验失败的字段详情）

    Returns:
        dict: {code, message, data}
    """
    return {
        "code": code,
        "message": message,
        "data": data,
    }


def paginate_response(
    data_list: list,
    total: int,
    page: int,
    page_size: int,
    message: str = "查询成功",
) -> dict:
    """
    构造分页成功响应字典

    Args:
        data_list: 当前页数据列表
        total: 总记录数
        page: 当前页码
        page_size: 每页条数
        message: 提示信息

    Returns:
        dict: {code, message, data: {list, total, page, page_size}}
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
    }
