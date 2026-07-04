import re
import os

file_path = r"D:\cc_project\performance_evaluation_system\TECH_绩效考核评分系统_v1.0.md"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

old_block = """## 9. 开发规范

- **命名**: Python 函数/变量使用 `snake_case`，Vue 组件使用 `PascalCase`。
- **类型注解**: 后端所有函数使用 Python 类型注解，Pydantic 模型定义请求/响应结构。
- **API 版本**: 所有接口以 `/api/v1` 开头，便于后续扩展 v2。
- **错误码**: 统一返回结构 `{code, message, data}`，HTTP 状态码与业务码分离。
- **测试**: 采用 pytest，每个 service 和 router 必须写单元测试，测试数据使用独立 SQLite 内存数据库。

---

## 10. 技术风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| SQLite 并发写入性能瓶颈 | 50人同时提交可能锁等待 | MVP 场景下并发量低，可控；后续迁移 MySQL 只需改数据库连接串 |
| 前后端联调问题 | 接口不一致 | 使用 FastAPI 自动生成的 Swagger 文档 (`/docs`) 作为接口契约 |
| 复杂报表导出性能 | 大数据量导出慢 | MVP 数据量有限，导出采用流式生成；后续可引入异步任务队列 |
| 考核状态机 bug | 状态流转错误导致流程卡住 | 状态流转封装为统一函数，写状态变更日志，支持管理员手动干预 |
| 强制分布降级引发争议 | 高分员工被系统强制降级（如 95 分从 A 降至 B），员工对结果不满 | 保留 `original_grade` 完整审计链；面谈时由上级解释降级原因；支持申诉复核 |

---"""

new_block = """## 9. 开发规范

### 9.1 代码风格与命名

| 层级 | 类型 | 规范 | 示例 |
|------|------|------|------|
| **后端** | 函数/变量 | `snake_case` | `calculate_weighted_score` |
| | 类 | `PascalCase` | `DistributionEnforcer` |
| | 常量 | `UPPER_SNAKE_CASE` | `MAX_LOGIN_ATTEMPTS = 5` |
| | 模块 | `snake_case` | `score_calculator.py` |
| **前端** | Vue 组件 | `PascalCase` | `DistributionReview.vue` |
| | 组合式函数 | `camelCase`，以 `use` 开头 | `usePermission.js` |
| | Pinia Store | `camelCase` | `auth.js` / `app.js` |
| | API 模块 | `camelCase` | `employees.js` |
| **数据库** | 表名 | `snake_case`，复数形式 | `assessment_records` |
| | 列名 | `snake_case` | `employee_no` |
| | 迁移文件 | `YYYY_MM_DD_HHMM_revise_xxx.py` | `2024_07_04_1200_add_max_ratio.py` |

### 9.2 后端开发规范

**1. 类型注解**：所有函数必须标注参数和返回值类型
```python
def calculate_score(
    self_scores: list[float],
    manager_scores: list[float],
    weights: dict[str, float]
) -> float:
    ...
```

**2. Pydantic 模型**：请求/响应模型统一放在 `schemas.py`，按模块分块
```python
class EmployeeCreate(BaseModel):
    employee_no: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
```

**3. 分层调用守则**：
- Router 层：只做参数校验、权限校验、调用 Service、返回响应
- Service 层：只做业务编排，禁止直接 `db.query(Model)`
- Repository 层：封装所有 ORM 操作，返回模型或 DTO
- Infrastructure 层：封装技术细节（文件、PDF、邮件、定时任务）
- **严禁跨层逆向调用**

**4. 异常处理**：使用自定义异常，禁止裸 `try/except Exception`
```python
from app.core.exceptions import BizError, AuthError

if not user:
    raise AuthError(message="用户不存在")
if score < 0:
    raise BizError(code=4001, message="评分不能为负数")
```

**5. 审计日志**：所有写操作（增删改）必须记录审计日志
```python
from app.utils.audit_logger import log_operation

log_operation(
    user_id=current_user.id,
    action="UPDATE_EMPLOYEE",
    target_type="employee",
    target_id=employee.id,
    old_value={"department_id": old_dept_id},
    new_value={"department_id": new_dept_id}
)
```

**6. 数据库迁移**：
- 任何模型变更必须通过 Alembic 生成迁移脚本
- 迁移脚本命名：`revise_表名_操作_日期`，如 `revise_employees_add_leave_date`
- 生产环境部署前必须在测试环境执行迁移验证

### 9.3 前端开发规范

**1. Vue 3 组合式 API**：
- 优先使用 `<script setup>` 语法
- 响应式数据区分 `ref`（简单值）和 `reactive`（对象）
- 复杂逻辑抽离到 `composables/`，禁止在 Vue 文件中写超过 200 行的逻辑

**2. Pinia 状态管理**：
- Store 按业务域拆分：`auth.js`（认证）、`app.js`（全局 UI）
- 禁止直接修改 Store 中的数组/对象，使用 `store.$patch()` 或 Action
- API 调用在 Store 的 Action 中完成，Vue 组件只负责调用 Action

**3. API 封装**：
- 统一错误处理在 `api/request.js` 拦截器中完成
- 组件中禁止裸写 `axios.get()`，必须调用 `api/` 下的封装方法
- 请求参数校验在调用前完成，避免将无效请求发送到后端

**4. 组件设计**：
- 公共组件必须写 `Props` 类型定义和默认值
- 表单组件必须暴露 `validate()` 和 `reset()` 方法
- 列表组件必须支持 `loading` 状态和空数据提示

### 9.4 测试规范

| 测试类型 | 工具 | 覆盖率要求 | 说明 |
|---------|------|-----------|------|
| **后端单元测试** | pytest | Service 层 ≥ 80% | 使用 SQLite `:memory:` 数据库，每个测试独立 Session |
| **后端集成测试** | pytest + TestClient | Router 层 ≥ 60% | 测试完整请求链路，验证状态码和响应结构 |
| **前端组件测试** | Vitest | 核心组件 ≥ 50% | 测试 Props 渲染、事件触发、状态变更 |
| **E2E 测试** | Playwright | 核心流程 100% | 登录 → 自评 → 审批 → 发布全流程 |

**测试数据管理**：
- 使用 `pytest.fixture` 管理测试数据，禁止测试间共享数据
- 每个测试文件配套 `conftest.py`，提供 `client`、`db_session`、`auth_token` 等 Fixture
- 敏感数据（密码）使用统一测试常量，禁止硬写在测试用例中

### 9.5 安全编码规范

- **禁止硬编码密钥**：JWT 密钥、数据库密码必须通过环境变量或 `.env` 文件注入
- **输入校验**：前端校验为体验，后端校验为安全，所有接口必须做后端参数校验（Pydantic）
- **SQL 注入防护**：禁止字符串拼接 SQL，必须使用 SQLAlchemy ORM 参数化查询
- **XSS 防护**：前端对用户输入做 HTML 转义，后端返回的富文本必须经过 bleach 清洗
- **敏感数据**：日志中禁止输出密码、Token、身份证，使用 `data_masking.py` 脱敏后再记录

### 9.6 Git 工作流

**分支策略**（Git Flow 简化版）：

```
main          ──→ 生产分支，只接受合并请求，禁止直接推送
  └── develop ──→ 开发分支，日常开发基于此
        ├── feature/xxx  ──→ 功能分支，从 develop 切出，完成后合并回 develop
        ├── hotfix/xxx   ──→ 热修复分支，从 main 切出，修复后合并回 main 和 develop
```

**提交规范**（Angular 风格）：

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 添加员工批量导入功能` |
| `fix` | 修复 Bug | `fix: 修复自评提交后状态未更新问题` |
| `docs` | 文档更新 | `docs: 更新 API 接口文档` |
| `refactor` | 重构 | `refactor: 优化评分计算算法` |
| `test` | 测试相关 | `test: 添加审批流程单元测试` |
| `chore` | 构建/工具 | `chore: 更新依赖版本` |

**提交信息格式**：
```
<type>(<scope>): <subject>

<body>（可选：说明修改原因、影响范围）

<footer>（可选：关联 Issue 编号，如 Closes #123）
```

---

## 10. 技术风险与应对

### 10.1 架构层风险

| 风险 | 影响 | 应对措施 | 责任方 |
|------|------|---------|--------|
| **SQLite 并发写入瓶颈** | 50 人同时提交评分时可能出现锁等待，导致响应变慢 | ① MVP 阶段并发量低，可控；② 写入操作使用短事务，尽快释放锁；③ 后续迁移 MySQL 只需改数据库连接串（SQLAlchemy 兼容） | 架构 |
| **SQLite 单文件损坏** | 服务器宕机或磁盘故障可能导致数据库文件损坏，数据丢失 | ① 每日自动备份（`backup.bat`）；② 备份保留 30 天；③ 重要操作前生成归档 PDF | 运维 |
| **APScheduler 在 Windows 下稳定性** | Windows 服务重启或休眠可能导致定时任务 missed | ① 使用 `BackgroundScheduler` 持久化到 SQLite；② 启动时调用 `scheduler.start()` 恢复未执行任务；③ 设置 `misfire_grace_time=3600` 允许 1 小时内补执行 | 后端 |
| **PDF 生成依赖外部工具** | Playwright/WeasyPrint 安装失败或版本不兼容导致归档失败 | ① 封装 `pdf_engine.py`，统一调用接口；② 归档失败时记录错误日志，允许手动重试；③ 降级方案：先导出 HTML，由浏览器打印为 PDF | 后端 |

### 10.2 数据层风险

| 风险 | 影响 | 应对措施 | 责任方 |
|------|------|---------|--------|
| **员工数据泄露** | 手机号、身份证号、绩效分数被未授权人员查看 | ① 数据脱敏（6.6 节）：列表页手机号 `153****3992`；② 权限控制：HR 只能查看本部门员工；③ 审计日志追踪所有敏感数据查询 | 安全 |
| **强制分布降级争议** | 高分员工被系统强制降级（如 95 分从 A 降至 B），引发不满 | ① 保留 `original_grade` 完整审计链；② 面谈时由上级解释降级原因；③ 支持申诉复核（Appeal 流程）；④ 小部门豁免（≤5 人）不参与强制分布 | 产品 |
| **考核状态机卡住** | 状态流转错误导致考核流程停滞（如员工已提交但上级未收到） | ① 状态流转封装为 `workflow_state_machine.py` 统一函数；② 每次状态变更写入 `operation_logs`；③ 管理员可在后台手动矫正状态（危险操作需二次确认） | 后端 |
| **导入数据污染** | HR 导入错误 Excel 导致员工数据混乱 | ① 预览模式：先校验后执行，错误报告 Excel 返给 HR；② 事务保护：单条失败整批回滚；③ 工号唯一性校验（模板内 + 数据库内） | 后端 |

### 10.3 应用层风险

| 风险 | 影响 | 应对措施 | 责任方 |
|------|------|---------|--------|
| **前后端联调不一致** | 接口字段、类型、返回值与前端预期不符 | ① 使用 FastAPI 自动生成 Swagger `/docs` 作为接口契约；② 前端使用 `types/api.ts` 定义接口类型，与 Swagger 保持一致；③ 接口变更必须通过 PR Review，通知前端同步修改 | 开发 |
| **复杂报表导出超时** | 跨周期大数据量导出（如 5000 条记录）导致浏览器超时 | ① 导出采用流式生成（Streaming），边查边写；② 前端显示进度条，后端返回 Task ID 轮询；③ 超大数据量导出改为异步任务，完成后通知下载 | 后端 |
| **前端构建兼容性** | 不同 Node 版本或浏览器导致构建失败或运行时错误 | ① `package.json` 指定 `engines` 字段；② 使用 Vite 构建，自动处理浏览器兼容性；③ 核心功能（如评分提交）在 Chrome/Edge/Firefox 下测试 | 前端 |
| **JWT Token 泄露** | Access Token 被截获导致未授权访问 | ① 短有效期（2 小时）；② Refresh Token（7 天）存储在 HttpOnly Cookie；③ 敏感操作（如修改密码）要求重新验证密码 | 安全 |

### 10.4 运维层风险

| 风险 | 影响 | 应对措施 | 责任方 |
|------|------|---------|--------|
| **备份失败导致无法恢复** | 备份脚本未执行或磁盘满导致备份文件缺失 | ① 备份脚本执行后写入 `backup.log`，记录成功/失败；② 每周人工抽查备份文件完整性；③ 备份目录与数据目录分离（不同磁盘） | 运维 |
| **单点维护风险** | 系统仅 1 人熟悉，离职或休假导致问题无法处理 | ① 代码注释率 ≥ 30%；② 技术文档（TECH）与代码同步维护；③ 核心算法（如强制分布）写独立文档说明原理；④ 关键操作（如数据库修复）保留操作手册 | 团队 |
| **版本升级回滚困难** | 升级后发现问题，无法快速回退到上一版本 | ① 升级前执行 `backup.bat`；② 使用 Git 标签标记每个生产版本；③ 数据库变更使用 Alembic，回滚执行 `alembic downgrade`；④ 保留上一版本构建产物（`frontend/dist`） | 运维 |

### 10.5 风险监控与预警

| 预警项 | 监控方式 | 阈值 | 响应动作 |
|--------|---------|------|---------|
| 数据库文件增长 | 定时脚本统计 `data/db/*.db` 大小 | > 500MB | 清理历史归档或迁移到 MySQL |
| 日志磁盘占用 | 定时统计 `logs/` 目录大小 | > 2GB | 压缩旧日志或调整保留策略 |
| 备份失败 | 检查 `backup.log` 最后一条记录 | 连续 2 天无成功记录 | 人工介入检查磁盘空间和脚本 |
| 接口响应时间 | 健康检查接口返回 | P95 > 3s | 检查 SQLite 锁竞争或慢查询 |
| 失败登录次数 | 审计日志统计 | 同一账号 5 分钟内失败 ≥ 5 次 | 自动锁定账号 15 分钟 |

---"""

if old_block not in content:
    print("ERROR: Old block not found")
    # Try to find the section
    idx = content.find("## 9. 开发规范")
    if idx != -1:
        print(f"Found at index {idx}")
        print(repr(content[idx:idx+200]))
    else:
        print("Section not found at all")
    exit(1)

content = content.replace(old_block, new_block, 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("SUCCESS")
