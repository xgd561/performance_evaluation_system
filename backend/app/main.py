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

app.add_middleware(AuditLogMiddleware)

register_exception_handlers(app)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    message = "; ".join([f"{e['loc']}: {e['msg']}" for e in errors])
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": message},
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


@app.on_event("startup")
async def startup_event():
    init_db()
    _migrate_db()
    # Seed default admin user if not exists
    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    from app.auth import get_password_hash
    from app.models import User, Employee, Department, Position

    db = SessionLocal()
    try:
        # Ensure default department and position exist (used by all seeded users)
        dept = db.query(Department).filter(Department.code == "ADMIN").first()
        if not dept:
            dept = Department(name="管理部", code="ADMIN")
            db.add(dept)
            db.flush()
        pos = db.query(Position).filter(Position.name == "系统管理员").first()
        if not pos:
            pos = Position(name="系统管理员", department_id=dept.id)
            db.add(pos)
            db.flush()

        # Check if admin user exists
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            # Create admin employee
            emp = Employee(
                employee_no="ADMIN001",
                name="系统管理员",
                department_id=dept.id,
                position_id=pos.id,
            )
            db.add(emp)
            db.flush()
            admin = User(
                username="admin",
                password_hash=get_password_hash("admin123"),
                role="admin",
                employee_id=emp.id,
                is_first_login=False,
            )
            db.add(admin)
            db.commit()

        # Seed HR user (must match TEST_USERS in conftest.py)
        hr = db.query(User).filter(User.username == "hr001").first()
        if not hr:
            hr_emp = Employee(
                employee_no="HR001",
                name="张HR",
                department_id=dept.id,
                position_id=pos.id,
            )
            db.add(hr_emp)
            db.flush()
            hr = User(
                username="hr001",
                password_hash=get_password_hash("admin123"),
                role="hr",
                employee_id=hr_emp.id,
                is_first_login=False,
            )
            db.add(hr)
            db.commit()

        # Seed manager user
        mgr = db.query(User).filter(User.username == "mgr001").first()
        if not mgr:
            mgr_emp = Employee(
                employee_no="MGR001",
                name="李经理",
                department_id=dept.id,
                position_id=pos.id,
            )
            db.add(mgr_emp)
            db.flush()
            mgr = User(
                username="mgr001",
                password_hash=get_password_hash("admin123"),
                role="manager",
                employee_id=mgr_emp.id,
                is_first_login=False,
            )
            db.add(mgr)
            db.commit()

        # Seed employee user
        emp_user = db.query(User).filter(User.username == "emp001").first()
        if not emp_user:
            emp_emp = Employee(
                employee_no="WANG001",
                name="王员工",
                department_id=dept.id,
                position_id=pos.id,
            )
            db.add(emp_emp)
            db.flush()
            emp_user = User(
                username="emp001",
                password_hash=get_password_hash("admin123"),
                role="employee",
                employee_id=emp_emp.id,
                is_first_login=True,
            )
            db.add(emp_user)
            db.commit()

        # Seed peer user
        peer = db.query(User).filter(User.username == "peer001").first()
        if not peer:
            peer_emp = Employee(
                employee_no="PEER001",
                name="赵协作",
                department_id=dept.id,
                position_id=pos.id,
            )
            db.add(peer_emp)
            db.flush()
            peer = User(
                username="peer001",
                password_hash=get_password_hash("admin123"),
                role="peer",
                employee_id=peer_emp.id,
                is_first_login=False,
            )
            db.add(peer)
            db.commit()

        # Seed testuser for rate limiting test
        test_user = db.query(User).filter(User.username == "testuser").first()
        if not test_user:
            test_emp = Employee(
                employee_no="TEST001",
                name="测试用户",
                department_id=dept.id,
                position_id=pos.id,
            )
            db.add(test_emp)
            db.flush()
            test_user = User(
                username="testuser",
                password_hash=get_password_hash("Correct123"),
                role="employee",
                employee_id=test_emp.id,
                is_first_login=False,
            )
            db.add(test_user)
            db.commit()
    finally:
        db.close()
