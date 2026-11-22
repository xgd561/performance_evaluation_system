"""统一响应契约：成功响应包成 {code, message, data}，错误响应与探针路径保持原样。

注意：conftest 里给 httpx.Response.json 加了自动解包，所以这里统一读 resp.content
再用 json.loads 还原原始响应体，确保断言针对的是真实传输内容。
"""
import json


def _raw(resp):
    return json.loads(resp.content.decode("utf-8"))


def test_success_response_wrapped(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.post("/api/v1/positions", json={"name": "统一响应岗", "level": "P5"}, headers=headers)
    assert resp.status_code == 201

    body = _raw(resp)
    assert body["code"] == 0
    assert body["message"] == "操作成功"
    assert body["data"]["name"] == "统一响应岗"


def test_list_response_wrapped_into_data(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.get("/api/v1/positions", headers=headers)
    assert resp.status_code == 200

    body = _raw(resp)
    assert body["code"] == 0
    # 岗位列表原本返回 {"items": [...]}，业务数据整体作为 data 的内容
    assert isinstance(body["data"]["items"], list)


def test_error_response_not_wrapped(client, admin_token):
    """错误响应保留真实 HTTP 状态码，body 不套信封的 data 层。"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.get("/api/v1/employees/999999", headers=headers)
    assert resp.status_code == 404

    body = _raw(resp)
    assert body["code"] == 404
    assert "message" in body
    assert body.get("data") is None


def test_legacy_envelope_not_double_wrapped(client, admin_token):
    """已是 {code, message, data} 的响应不重复包装（幂等）。"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = client.get("/api/v1/positions", headers=headers)
    body = _raw(resp)
    assert "data" in body
    # 若被二次包装，内层还会出现一次 code/message
    if isinstance(body["data"], dict):
        assert "data" not in body["data"]


def test_health_not_wrapped(client):
    """健康检查是运维探针契约，不参与包装（保持原有的 code/data 结构）。"""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = _raw(resp)
    assert body["code"] == 0
    assert body["data"]["db"] == "ok"
    assert "message" not in body


def test_openapi_not_wrapped(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    body = _raw(resp)
    assert "paths" in body
    assert "code" not in body
