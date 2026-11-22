---
kind: logging_system
name: 基于 Python stdlib logging + ASGI Middleware 的操作审计日志系统
category: logging_system
scope:
    - '**'
source_files:
    - backend/app/utils/audit_logger.py
    - backend/app/services/operation_logger.py
    - backend/app/models.py
    - backend/app/schemas.py
    - backend/app/routers/logs.py
    - backend/app/main.py
---

## 1. 使用的系统与框架

后端采用 Python 标准库 `logging`（`logging.getLogger(__name__)`）作为进程内日志门面，但**没有引入第三方日志框架**（代码中未发现 loguru、structlog、python-json-logger 等）。Uvicorn 自身通过命令行参数启动（见根目录与 backend 下的 `uvicorn.log`、`backend_stdout.log`、`uvicorn_8014.log`、`uvicorn_run.log`），其输出由 Uvicorn 默认 handler 写入文件；应用层未调用 `logging.config.dictConfig`/`basicConfig` 自定义 handler。

业务层面的“日志”实质是**操作审计日志（Audit Log）**：将关键写操作的请求体、响应体、用户、IP 等信息持久化到 SQLite 的 `operation_logs` 表，并通过 `/api/v1/logs` 暴露查询 API。该能力由一个纯 ASGI Middleware 自动拦截 POST/PUT/DELETE 请求完成。

## 2. 关键文件

| 文件 | 作用 |
|---|---|
| `backend/app/utils/audit_logger.py` | 定义 `AuditLogMiddleware`、`log_operation`、`_extract_token_user_id`、`_extract_target_info` |
| `backend/app/services/operation_logger.py` | 另一份轻量 `log_operation`（使用 `db.flush()` 而非 commit），供业务服务直接调用 |
| `backend/app/models.py` (L186-L196) | `OperationLog` SQLAlchemy 模型，对应 `operation_logs` 表 |
| `backend/app/schemas.py` (L344, L359) | `OperationLogOut` / `OperationLogListResponse` Pydantic 响应模型 |
| `backend/app/routers/logs.py` | `/logs` 路由：分页查询、按 action/target_type/date 筛选、列出所有 action |
| `backend/app/main.py` | 注册 `AuditLogMiddleware`（第 26 行）、挂载 `/logs` 路由（第 67/91 行） |

## 3. 架构与设计约定

### 3.1 自动审计（ASGI Middleware）

`AuditLogMiddleware` 在 `main.py` 中以 `app.add_middleware(AuditLogMiddleware)` 注册，位于 CORS 之后、异常处理器之前。

拦截规则：
- 仅对 HTTP scope 生效（`scope["type"] != "http"` 直接透传）。
- 仅对 `POST`/`PUT`/`DELETE` 方法记录日志，其他方法直接 `await self.app(...)` 透传。
- 读取并解析 request body（JSON 优先，失败时回退为 UTF-8 字符串），然后通过重写 `receive` 让下游 endpoint 仍可再次消费 body。
- 通过 `send_with_capture` 捕获 response 的 status 和 body，仅当 `200 <= status < 300` 时才落库。
- 从 `Authorization: Bearer <token>` 头解析 `user_id`（调用 `decode_token`，取 payload 的 `sub` 字段转 int）。
- 从 URL path 推断 `action`（POST→create，PUT→update，DELETE→delete，其余用 method 小写）和 `target_type`（取 `/api/v1/<resource>/...` 中的 `<resource>`）。
- 从 URL 末尾提取纯数字段作为 `target_id`。
- 从 `request.client.host` 获取 `ip_address`。
- 每次落库使用独立的 `SessionLocal()`，并在 `finally` 中 `db.close()`，避免泄漏连接。

### 3.2 手动审计（Service 层）

`services/operation_logger.log_operation` 提供显式调用入口，参数包括 `user_id`、`action`、`target_type`、`target_id`、`old_value`、`new_value`、`ip_address`，内部 `db.add(log); db.flush()`（不 commit，交由外层事务管理）。

`utils/audit_logger.log_operation` 与之类似，但额外支持 `default=str` 的 JSON 序列化兜底，且 `db.commit()`。

### 3.3 数据模型

`OperationLog` 表字段：
- `id`：自增主键
- `user_id`：外键关联 `users.id`
- `action`：VARCHAR(100)，如 create/update/delete 或 approve/reject/score_submit/kpi_adjust 等
- `target_type`：VARCHAR(50)，如 employee/cycle/assessment_record 等
- `target_id`：INT
- `old_value`：TEXT（JSON 序列化后的旧快照）
- `new_value`：TEXT（JSON 序列化后的新快照）
- `ip_address`：VARCHAR(50)
- `created_at`：DATETIME，默认 `datetime.utcnow`

### 3.4 查询与展示

`routers/logs.py` 提供：
- `GET /logs`：分页（page/size，size ≤ 100），支持按 `action`、`target_type`、`start_date`、`end_date` 过滤，返回 `total` + `items`，并按 `created_at DESC` 排序；同时批量 JOIN `User` 填充 `username`。
- `GET /logs/actions`：返回所有已出现的 `action` 去重列表，用于前端下拉选择。
- 两个接口均要求 `require_role("admin", "hr")`。

## 4. 约定与约束

- **日志级别策略**：应用层未实现自定义日志级别体系；`AuditLogMiddleware` 内部仅在写入失败时通过 `logger.error(f"Failed to write audit log: {e}")` 记录错误，其余审计事件不经过 Python `logging` 流，而是直接落库。
- **结构化字段**：审计日志以数据库行结构组织，`old_value`/`new_value` 统一经 `json.dumps(..., ensure_ascii=False)` 序列化为 TEXT 存储。
- **只记成功写操作**：Middleware 仅对 2xx 响应落库，4xx/5xx 变更不会产生审计记录。
- **Body 可重复消费**：Middleware 通过重写 `receive` 返回原始 body，保证下游 FastAPI endpoint 仍能正常读取请求体。
- **无敏感信息脱敏**：当前实现直接序列化完整 request/response body，未见数据脱敏逻辑（`app/utils/data_masking.py` 存在但未在此处引用）。
- **Uvicorn 进程日志**：Uvicorn 自身的 access/error 日志由外部脚本/容器写入 `uvicorn.log`、`backend_stdout.log`、`uvicorn_8014.log`、`uvicorn_run.log` 等文件，应用代码未配置这些 handler。
- **测试覆盖**：`tests/test_p17_operation_logs.py`、`tests/test_operation_logs.py`、`tests/scripts/test_log.py` 以及 `test_p0_13_audit_logger.py` 对审计日志的写入与查询进行了断言。