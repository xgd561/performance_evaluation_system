import sys

# 验证所有必需的依赖包可导入
REQUIRED_PACKAGES = [
    ("fastapi", "0.111.0"),
    ("uvicorn", "0.30.0"),
    ("sqlalchemy", "2.0.31"),
    ("alembic", "1.13.1"),
    ("pydantic", "2.7.4"),
    ("jose", None),  # python-jose
    ("passlib", None),
    ("multipart", None),  # python-multipart
    ("openpyxl", "3.1.5"),
    ("pytest", "8.2.2"),
    ("httpx", "0.27.0"),
    ("playwright", "1.44.0"),
    ("apscheduler", "3.10.4"),
]


def test_all_packages_importable():
    """断言所有依赖包均可成功导入"""
    failures = []
    for module_name, expected_version in REQUIRED_PACKAGES:
        try:
            mod = __import__(module_name)
            if expected_version and hasattr(mod, "__version__"):
                actual = mod.__version__
                if expected_version not in actual:
                    failures.append(
                        f"{module_name}: expected {expected_version}, got {actual}"
                    )
        except ImportError as e:
            failures.append(f"{module_name}: ImportError - {e}")

    assert not failures, "包导入失败:\n" + "\n".join(failures)


def test_fastapi_basic_app():
    """使用 FastAPI TestClient 做基本接口测试，断言状态码和响应结构"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok", "env": "test"}

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200, f"状态码应为 200，实际 {response.status_code}"
    data = response.json()
    assert data["status"] == "ok", f"响应结构错误: {data}"
    assert "env" in data, f"响应缺少 env 字段: {data}"


def test_sqlalchemy_sqlite_connection():
    """断言 SQLAlchemy 可连接 SQLite 内存数据库"""
    from sqlalchemy import create_engine, text

    engine = create_engine("sqlite:///:memory:", echo=False)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1, "SQLite 内存连接失败"


def test_pydantic_model_validation():
    """断言 Pydantic 模型校验正常工作"""
    from pydantic import BaseModel, ValidationError

    class Demo(BaseModel):
        name: str
        age: int

    obj = Demo(name="test", age=30)
    assert obj.name == "test"
    assert obj.age == 30

    try:
        Demo(name="test", age="not_an_int")
    except ValidationError:
        pass
    else:
        assert False, "Pydantic 应抛出 ValidationError"


def test_pytest_version():
    """断言 pytest 版本正确"""
    import pytest

    assert pytest.__version__.startswith("8.2"), f"pytest 版本异常: {pytest.__version__}"


if __name__ == "__main__":
    test_all_packages_importable()
    test_fastapi_basic_app()
    test_sqlalchemy_sqlite_connection()
    test_pydantic_model_validation()
    test_pytest_version()
    print("\n[PASS] P0-02 所有验证通过！")
