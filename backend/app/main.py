from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.database import init_db
from app.routers import auth, employees, departments, cycles, kpi_templates, config, dashboard, appeals, scores, reports, approvals, interviews, peers, logs, health, notifications, score_drafts
import app.models

app = FastAPI(
    title="绩效考核评分系统",
    description="Performance Evaluation System API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.utils.audit_logger import AuditLogMiddleware
from app.core.exceptions import register_exception_handlers
from app.core.response import UnifiedResponseMiddleware

app.add_middleware(AuditLogMiddleware)
# 成功响应统一包装为 {code, message, data}；错误响应保持原 HTTP 状态码
app.add_middleware(UnifiedResponseMiddleware)

register_exception_handlers(app)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.detail, "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    message = "; ".join([f"{e['loc']}: {e['msg']}" for e in errors])
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": message, "data": None},
    )


api_v1 = APIRouter(prefix="/api/v1")

api_v1.include_router(auth.router, prefix="/auth", tags=["认证"])
api_v1.include_router(employees.router, prefix="/employees", tags=["员工管理"])
api_v1.include_router(departments.router, prefix="/departments", tags=["部门管理"])
api_v1.include_router(departments.router_positions, prefix="/positions", tags=["岗位管理"])
api_v1.include_router(cycles.router, prefix="/assessment-cycles", tags=["考核周期"])
api_v1.include_router(kpi_templates.router, prefix="/kpi-templates", tags=["KPI模板"])
api_v1.include_router(config.router, prefix="/config", tags=["系统配置"])
api_v1.include_router(dashboard.router, prefix="/dashboard", tags=["仪表盘"])
api_v1.include_router(appeals.router, prefix="/appeals", tags=["申诉管理"])
api_v1.include_router(scores.router, prefix="/scores", tags=["评分管理"])
api_v1.include_router(score_drafts.score_drafts_router, prefix="/score-drafts", tags=["评分草稿"])
api_v1.include_router(approvals.router, prefix="/approvals", tags=["审批管理"])
api_v1.include_router(interviews.router, prefix="/interviews", tags=["绩效面谈"])
api_v1.include_router(interviews.record_router, prefix="/assessment-records", tags=["考核记录"])
api_v1.include_router(reports.router, prefix="/reports", tags=["报表分析"])
api_v1.include_router(peers.router, prefix="/peer-reviewers", tags=["协作评分"])
api_v1.include_router(logs.router, prefix="/logs", tags=["操作日志"])
api_v1.include_router(notifications.router, prefix="/notifications", tags=["通知消息"])
api_v1.include_router(health.router, tags=["健康检查"])

app.include_router(api_v1)

# Also mount routes without /api/v1 prefix for backward compatibility with tests
direct_api = APIRouter()
direct_api.include_router(auth.router, prefix="/auth", tags=["认证"])
direct_api.include_router(employees.router, prefix="/employees", tags=["员工管理"])
direct_api.include_router(departments.router, prefix="/departments", tags=["部门管理"])
direct_api.include_router(departments.router_positions, prefix="/positions", tags=["岗位管理"])
direct_api.include_router(cycles.router, prefix="/assessment-cycles", tags=["考核周期"])
direct_api.include_router(kpi_templates.router, prefix="/kpi-templates", tags=["KPI模板"])
direct_api.include_router(config.router, prefix="/config", tags=["系统配置"])
direct_api.include_router(dashboard.router, prefix="/dashboard", tags=["仪表盘"])
direct_api.include_router(appeals.router, prefix="/appeals", tags=["申诉管理"])
direct_api.include_router(scores.router, prefix="/scores", tags=["评分管理"])
direct_api.include_router(score_drafts.score_drafts_router, prefix="/score-drafts", tags=["评分草稿"])
direct_api.include_router(approvals.router, prefix="/approvals", tags=["审批管理"])
direct_api.include_router(interviews.router, prefix="/interviews", tags=["绩效面谈"])
direct_api.include_router(interviews.record_router, prefix="/assessment-records", tags=["考核记录"])
direct_api.include_router(reports.router, prefix="/reports", tags=["报表分析"])
direct_api.include_router(peers.router, prefix="/peer-reviewers", tags=["协作评分"])
direct_api.include_router(logs.router, prefix="/logs", tags=["操作日志"])
direct_api.include_router(notifications.router, prefix="/notifications", tags=["通知消息"])
# 无前缀同样暴露 /health，便于运维探活在任意挂载方式下可用
direct_api.include_router(health.router, tags=["健康检查"])

app.include_router(direct_api)


def _migrate_db():
    """模型驱动的 SQLite 增量迁移。

    对比 SQLAlchemy 元数据与实际库表结构，为已存在的表自动补齐缺失列，
    避免每新增一个字段都要在本函数里手写一条 ALTER TABLE。
    SQLite 限制：ADD COLUMN 不能是 NOT NULL 且无默认值，这类列会跳过并打印告警。
    """
    from sqlalchemy import inspect, text
    from sqlalchemy.schema import ColumnDefault
    from app.database import engine
    from app.models import Base

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    def _type_sql(column):
        try:
            return column.type.compile(dialect=engine.dialect)
        except Exception:
            return "TEXT"

    def _default_sql(column):
        """只有标量默认值可以内联到 ADD COLUMN 中。"""
        default = column.default
        if default is None or not isinstance(default, ColumnDefault):
            return ""
        if getattr(default, "is_scalar", False) is False:
            return ""
        value = default.arg
        if isinstance(value, bool):
            return f" DEFAULT {1 if value else 0}"
        if isinstance(value, (int, float)):
            return f" DEFAULT {value}"
        if isinstance(value, str):
            return " DEFAULT '" + value.replace("'", "''") + "'"
        return ""

    added = 0
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue  # 新建表由 create_all 负责
            existing_columns = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                default_sql = _default_sql(column)
                if not column.nullable and not default_sql:
                    print(f"[migrate] skip {table.name}.{column.name}: NOT NULL 且无标量默认值，需人工处理")
                    continue
                ddl = f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {_type_sql(column)}{default_sql}'
                conn.execute(text(ddl))
                added += 1
                print(f"[migrate] Added column {table.name}.{column.name}")

    if added == 0:
        print("[migrate] schema up to date")


# 演示账号口径与 backend/tests/conftest.py 的 TEST_USERS 保持一致。
# 历史版本把除 testuser 以外的账号密码都写成了 admin123，导致按文档用
# Hr001@123 等密码登录时报 401，而前端 401 拦截器又会提示「登录已过期」，
# 很容易被误判成账号过期。
DEFAULT_ACCOUNTS = [
    # username, password, role, employee_no, name, position, is_first_login
    ("admin", "admin123", "admin", "ADMIN001", "系统管理员", "系统管理员", False),
    ("hr001", "Hr001@123", "hr", "HR001", "张HR", "HR专员", False),
    ("mgr001", "Mgr001@123", "manager", "MGR001", "李经理", "技术经理", False),
    ("emp001", "Emp001@123", "employee", "EMP001", "王员工", "Java工程师", True),
    ("peer001", "Peer001@123", "peer", "PEER001", "协作员工", "协作人", False),
    ("exec001", "Exec001@123", "executive", "EXEC001", "赵高管", "高管", False),
    ("testuser", "Correct123", "employee", "TEST001", "测试用户", "系统管理员", False),
]

# 旧种子统一使用的密码，仅用于识别「从未改过密码」的账号
_LEGACY_SEED_PASSWORD = "admin123"


def _seed_user_accounts():
    """幂等创建演示账号，并纠正旧种子遗留的错误密码。"""
    from app.database import SessionLocal
    from app.auth import get_password_hash, verify_password
    from app.models import User, Employee, Department, Position

    db = SessionLocal()
    try:
        dept = db.query(Department).filter(Department.code == "ADMIN").first()
        if not dept:
            dept = Department(name="管理部", code="ADMIN")
            db.add(dept)
            db.flush()

        for username, password, role, employee_no, name, position_name, first_login in DEFAULT_ACCOUNTS:
            position = db.query(Position).filter(Position.name == position_name).first()
            if not position:
                position = Position(name=position_name, department_id=dept.id)
                db.add(position)
                db.flush()

            employee = db.query(Employee).filter(Employee.employee_no == employee_no).first()
            if not employee:
                employee = Employee(
                    employee_no=employee_no,
                    name=name,
                    department_id=dept.id,
                    position_id=position.id,
                )
                db.add(employee)
                db.flush()

            user = db.query(User).filter(User.username == username).first()
            if not user:
                db.add(User(
                    username=username,
                    password_hash=get_password_hash(password),
                    role=role,
                    employee_id=employee.id,
                    is_first_login=first_login,
                ))
            elif password != _LEGACY_SEED_PASSWORD and verify_password(
                _LEGACY_SEED_PASSWORD, user.password_hash
            ):
                # 密码仍是旧种子值说明用户没改过，按目标密码纠正；改过则不动
                user.password_hash = get_password_hash(password)
            db.commit()
    finally:
        db.close()


@app.on_event("startup")
async def startup_event():
    init_db()
    _migrate_db()
    _seed_user_accounts()
