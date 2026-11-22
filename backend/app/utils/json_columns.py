"""JSON 列读写工具。

SQLAlchemy 的 JSON 列会自动序列化/反序列化，但历史上多处路由仍对 JSON 列手动
``json.dumps``（写入变成「JSON 字符串再套一层 JSON」）与 ``json.loads``（读到大
字典时抛 TypeError）。这里统一提供容错读写，兼容两种历史数据形态。

约定：JSON 列写入直接存 dict/list，读取一律走 ``load_json``。
"""
import json


def load_json(value, default=None):
    """读取 JSON 列的值。

    兼容三种形态：已是 dict/list（SQLAlchemy 已反序列化）、遗留的 JSON 字符串、
    以及空值。解析失败时返回 ``default``，避免脏数据打挂接口。
    """
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return default
        try:
            return json.loads(text)
        except ValueError:
            return default
    return value