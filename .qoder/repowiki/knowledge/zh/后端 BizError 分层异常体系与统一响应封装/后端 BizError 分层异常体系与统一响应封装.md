---
kind: error_handling
name: 后端 BizError 分层异常体系与统一响应封装
category: error_handling
scope:
    - '**'
source_files:
    - backend/app/core/exceptions.py
    - backend/app/core/response.py
    - backend/app/main.py
    - backend/app/utils/workflow_state_machine.py
    - backend/app/utils/audit_logger.py
    - backend/app/auth.py
    - backend/app/core/security.py
    - backend/app/core/dependencies.py
    - frontend/src/api/request.js
---

## 1. 整体方案

后端基于 FastAPI，采用「自定义业务异常类 + 全局异常处理器 + 统一响应模型」三层结构；前端通过 Axios 拦截器统一消费后端返回的 `{code, message, data}` 格式。

- 业务异常：`app/core/exceptions.py` 定义 `BizError` 基类及 `AuthError`、`NotFoundError`、`ValidationError` 三个子类，每个异常携带 `message / code / data / status_code` 四个字段。
- 全局处理：`register_exception_handlers(app)` 在 `main.py` 启动时注册两个处理器——`BizError` → 原样返回 `status_code` + `to_dict()`；未捕获的 `Exception` → 固定返回 `{code:5000, message:"服务器内部错误", data:null}`（HTTP 500）。
- HTTP 层异常：`main.py` 还单独覆盖了 `FastAPI.HTTPException` 和 `RequestValidationError`，将 FastAPI 原生异常也归一化为 `{code, message}` 字典。
- 统一响应：`app/core/response.py` 提供 `success_response()` / `error_response()` / `paginate_response()` 工厂函数，以及带 `timestamp` 字段的 `BaseResponse` Pydantic 模型，作为 API 成功响应的约定结构。

## 2. 关键文件

| 文件 | 职责 |
|---|---|
| `backend/app/core/exceptions.py` | 业务异常类定义 + `register_exception_handlers` 全局注册 |
| `backend/app/core/response.py` | 统一成功/失败/分页响应构造器 |
| `backend/app/main.py` | FastAPI 应用装配，挂载 CORS、审计中间件、异常处理器、路由 |
| `backend/app/utils/workflow_state_machine.py` | 状态机中抛出 `BizError` 的典型业务校验点 |
| `backend/app/auth.py` | 认证逻辑中大量使用 `fastapi.HTTPException`（401/403） |
| `backend/app/core/security.py` | RBAC 权限检查抛 `HTTPException(403)` |
| `backend/app/core/dependencies.py` | 依赖注入中捕获并重新包装 `HTTPException` |
| `frontend/src/api/request.js` | Axios 拦截器按 `data.code !== 0 && data.code !== 200` 判定业务失败 |

## 3. 架构与约定

### 3.1 业务异常层次
```
BizError (base)
├── AuthError      # 默认 code=2000, status=401
├── NotFoundError   # 默认 code=3000, status=404
└── ValidationError # 默认 code=4000, status=422
```
所有业务分支应优先 raise 这些类型，而不是裸 `raise Exception`。当前仓库中唯一已使用的业务异常是 `WorkflowStateMachine.transition` 抛出的 `BizError(code=1100/1101)`，用于“未知状态”和“不允许的动作”。

### 3.2 全局异常处理链
`main.py` 中注册的顺序为：
1. `BizError` → 透传 `exc.status_code` + `exc.to_dict()`
2. `HTTPException` → 映射为 `{code: exc.status_code, message: exc.detail}`
3. `RequestValidationError` → 拼接 Pydantic 校验信息为 `loc: msg; ...`，返回 `{code:422, message}`
4. 兜底 `Exception` → `{code:5000, message:"服务器内部错误", data:null}`

注意：`HTTPException` 的全局处理器在 `register_exception_handlers` 之后由 `main.py` 再次覆盖，因此 FastAPI 内置的 `HTTPException` 不会走 `BizError` 的处理器。

### 3.3 审计日志与异常隔离
`AuditLogMiddleware`（`app/utils/audit_logger.py`）仅记录 **2xx** 响应（`200 <= response_status < 300`），即错误请求不会被写入操作日志；同时日志写入本身被 `try/except Exception` 包裹，失败仅 `logger.error` 而不阻断主流程。

### 3.4 前端错误处理
Axios 响应拦截器判断 `data.code !== 0 && data.code !== 200` 视为业务失败，弹出 `ElMessage.error(data.message)` 并 reject Promise；网络错误或 `HTTP 401` 会清除本地 token 并跳转 `/login`。

## 4. 观察到的约定与约束

- 业务异常统一继承 `BizError`，并通过 `to_dict()` 输出 `{code, message, data}` 三字段结构（见 `exceptions.py` 注释“统一结构: {code, message, data}”）。
- 业务码与 HTTP 状态码分离：`BizError` 同时维护 `code`（业务码）和 `status_code`（HTTP 码），例如 `AuthError` 默认 `code=2000, status=401`。
- 全局异常处理器通过 `register_exception_handlers(app)` 集中注册，而非在各模块分散添加 `@app.exception_handler`。
- 状态机中的非法转换必须抛 `BizError`，且附带 `current_state` / `action` / `allowed_actions` 等上下文数据（`workflow_state_machine.py` 第 138、147 行）。
- 审计日志只落库 2xx 响应，非 2xx 的请求不产生操作日志（`audit_logger.py` 第 162 行条件）。
- 前端对 `code=0` 或 `code=200` 视作成功，其余一律视为业务错误（`request.js` 第 57 行）。
- 代码中也存在直接使用 `fastapi.HTTPException` 的路径（`auth.py`、`security.py`、`dependencies.py`），它们不走 `BizError` 体系，而是由 `main.py` 的 `http_exception_handler` 统一转成 `{code, message}` 格式——这是现有实现的一部分，不是缺失。

## 5. 待改进点（描述性，非强制规则）

- `AuthError` / `NotFoundError` / `ValidationError` 子类目前未被任何业务代码 raise，实际认证/授权错误仍通过 `HTTPException` 抛出，导致业务码空间（2000/3000/4000）尚未被使用。
- `success_response` / `error_response` 返回裸 `dict`，而 `BaseResponse` 是 Pydantic 模型但未被使用，两者并存增加了响应格式的歧义面。
- `HTTPException` 与 `BizError` 两套异常体系并存，部分路径（如 `auth.py`、`security.py`）未迁移到 `BizError`，使前端需兼容 `code=0` 与 `code=200` 两种成功码。