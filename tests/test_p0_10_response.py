import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.response import (
    success_response,
    error_response,
    paginate_response,
    BaseResponse,
    PaginationData,
)


class TestSuccessResponse:
    """验证 success_response 构造正确"""

    def test_default_success(self):
        resp = success_response()
        assert resp == {"code": 0, "message": "操作成功", "data": None}

    def test_with_data(self):
        resp = success_response(data={"id": 1, "name": "test"})
        assert resp["code"] == 0
        assert resp["message"] == "操作成功"
        assert resp["data"] == {"id": 1, "name": "test"}

    def test_with_custom_message(self):
        resp = success_response(data=[1, 2, 3], message="查询成功")
        assert resp["code"] == 0
        assert resp["message"] == "查询成功"
        assert resp["data"] == [1, 2, 3]

    def test_with_none_data(self):
        resp = success_response(data=None)
        assert resp["data"] is None


class TestErrorResponse:
    """验证 error_response 构造正确"""

    def test_default_error(self):
        resp = error_response()
        assert resp == {"code": 1000, "message": "业务错误", "data": None}

    def test_with_custom_code_and_message(self):
        resp = error_response(code=2001, message="Token 已过期")
        assert resp["code"] == 2001
        assert resp["message"] == "Token 已过期"
        assert resp["data"] is None

    def test_with_data(self):
        resp = error_response(code=4001, message="参数非法", data={"field": "email"})
        assert resp["code"] == 4001
        assert resp["message"] == "参数非法"
        assert resp["data"] == {"field": "email"}


class TestPaginateResponse:
    """验证 paginate_response 构造正确"""

    def test_default_paginate(self):
        resp = paginate_response(
            data_list=[{"id": 1}, {"id": 2}],
            total=100,
            page=1,
            page_size=20,
        )
        assert resp["code"] == 0
        assert resp["message"] == "查询成功"
        assert resp["data"]["list"] == [{"id": 1}, {"id": 2}]
        assert resp["data"]["total"] == 100
        assert resp["data"]["page"] == 1
        assert resp["data"]["page_size"] == 20

    def test_custom_message(self):
        resp = paginate_response(
            data_list=[],
            total=0,
            page=2,
            page_size=10,
            message="暂无数据",
        )
        assert resp["message"] == "暂无数据"
        assert resp["data"]["list"] == []


class TestBaseResponseModel:
    """验证 BaseResponse Pydantic 模型"""

    def test_success_model(self):
        resp = BaseResponse(code=0, message="ok", data={"id": 1})
        assert resp.code == 0
        assert resp.message == "ok"
        assert resp.data == {"id": 1}
        assert resp.timestamp is not None

    def test_error_model(self):
        resp = BaseResponse(code=1000, message="error", data=None)
        assert resp.code == 1000
        assert resp.message == "error"

    def test_json_serialization(self):
        resp = BaseResponse(code=0, message="ok", data={"id": 1})
        json_str = resp.model_dump_json()
        assert '"code":0' in json_str
        assert '"message":"ok"' in json_str


class TestPaginationDataModel:
    """验证 PaginationData Pydantic 模型"""

    def test_pagination_data(self):
        pag = PaginationData(items=[1, 2, 3], total=10, page=1, page_size=5)
        assert pag.items == [1, 2, 3]
        assert pag.total == 10
        assert pag.page == 1
        assert pag.page_size == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
