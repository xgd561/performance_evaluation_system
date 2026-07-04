# 绩效考核评分系统 — 知识库

基于 FastAPI + Vue 3 + SQLite 的绩效考核评分系统。后端 14 张表完整，核心评分/审批/强制分布算法已就绪；前端基础页面完整，关键 Stub 已补齐，业务流程基本打通。

## 技术架构

- **后端**：FastAPI + SQLAlchemy + SQLite + JWT + OpenPyXL + ReportLab
- **前端**：Vue 3 + Element Plus + ECharts + Axios + XLSX
- **测试**：pytest + TestClient + factory_boy

## 项目结构

```
backend/
├── app/
│   ├── auth.py              # JWT 认证、密码哈希、require_role
│   ├── database.py          # SQLAlchemy engine / session
│   ├── main.py              # FastAPI 应用入口、异常处理
│   ├── models.py            # 14 张 ORM 表定义
│   ├── schemas.py           # Pydantic schemas
│   ├── services/            # 业务逻辑服务
│   │   ├── distribution_enforcer.py  # 强制分布降级算法
│   │   └── operation_logger.py        # 操作日志统一写入
│   ├── utils/               # 工具函数
│   │   └── pdf_generator.py # PDF 档案生成
│   └── routers/             # API 路由（按模块拆分）
│       ├── appeals.py       # 申诉
│       ├── approvals.py     # 审批（多级审批链）
│       ├── auth.py          # 登录/注册/Token
│       ├── config.py        # 系统配置（维度权重、审批链）
│       ├── cycles.py        # 考核周期
│       ├── dashboard.py     # 仪表盘（按角色隔离数据）
│       ├── employees.py     # 员工/部门/岗位
│       ├── interviews.py    # 绩效面谈
│       ├── kpi_templates.py # KPI 模板
│       ├── logs.py          # 操作日志查询
│       ├── peers.py         # 协作评分
│       ├── reports.py       # 报表导出（真实 Excel）
│       └── scores.py        # 评分提交/草稿/详情/发布
├── tests/                   # 23+ 测试文件，覆盖 P06-P23
└── requirements.txt

frontend/
├── src/
│   ├── api/                 # 接口封装（按模块）
│   ├── components/          # 公共组件（Layout、Charts）
│   ├── router/              # 路由配置（角色守卫）
│   └── views/               # 页面
│       ├── audit/           # 操作日志审计页
│       ├── config/          # 系统配置
│       ├── cycles/          # 考核周期
│       ├── distribution-review/  # 强制分布处理（HR）
│       ├── kpi-adjustment/    # KPI 动态调整申请/审批
│       ├── my-performance/  # 我的绩效（趋势图 + 详情抽屉）
│       ├── reports/         # 报表导出
│       ├── score-sheet/     # 上级评分（真实数据）
│       └── self-assessment/ # 自评
```

## 已完成功能（P0 + P1）

### P0 级（核心流程）

| 编号 | 功能 | 状态 |
|------|------|------|
| P0-1 | 上级评分页接入真实数据与提交 | ✅ 完成 |
| P0-2 | 考核结果发布接口 | ✅ 完成 |
| P0-3 | 评分草稿保存/恢复前后端完整链路 | ✅ 完成 |
| P0-4 | KPI 评分持久化与加权计算 | ✅ 完成 |
| P0-5 | 报表真实 Excel 导出 | ✅ 完成 |
| P0-6 | 移除 executive 写权限 | ✅ 完成 |
| P0-9 | GET 面试数据隔离 | ✅ 完成 |
| P0-10 | 经理链面试历史隔离 | ✅ 完成 |

### P1 级（业务增强 + 安全加固）

| 编号 | 功能 | 状态 |
|------|------|------|
| P1-11 | HR 强制分布处理页 | ✅ 完成 |
| P1-12 | KPI 动态调整申请前端 | ✅ 完成 |
| P1-13 | KPI 调整审批权限修复 | ✅ 完成 |
| P1-14 | 考核详情抽屉接口 | ✅ 完成 |
| P1-15 | ConfigView 维度权重 Tab 修复 | ✅ 完成 |
| P1-16 | 周期参与人员列表接口 | ✅ 完成 |
| P1-17 | 操作日志查询与审计页 | ✅ 完成 |
| P1-18 | 未发布记录分数掩码 | ✅ 完成 |
| P1-19 | P1-18 后端测试 | ✅ 完成 |
| P1-20 | 递归子部门可见性 | ✅ 完成 |
| P1-21 | 仪表盘角色隔离统计 | ✅ 完成 |
| P1-22 | require_role 检查 is_active | ✅ 完成 |
| P1-23 | 审批列表避免全表扫描 | ✅ 完成 |

## 默认测试账号

| 账号 | 密码 | 角色 | 员工编号 |
|------|------|------|----------|
| admin | `admin123` | 管理员 | ADMIN001 |
| hr001 | `Hr001@123` | HR | HR001 |
| mgr001 | `Mgr001@123` | 经理 | MGR001 |
| emp001 | `Emp001@123` | 员工 | EMP001 |
| peer001 | `Peer001@123` | 协作人 | PEER001 |
| exec001 | `Exec001@123` | 高层 | exec001 |

> **注意**：`emp001` 的密码以代码 `main.py` 中的 seed 逻辑和测试用例 `conftest.py` 为准，是 `Emp001@123`（首字母大写，带 `@123` 后缀）。

## 快速启动

```bash
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
cd frontend && npm run dev
```

## 剩余未实现（P2 及后续）

1. **时间窗口逾期检测与自动锁定/提醒机制**（如自评截止后自动锁定并发送提醒）
2. **更完整的自动化测试覆盖**（当前 `test_approvals.py` 部分测试因 `approve_record` 的 `status == "pending_approval"` 强校验与测试用例状态不一致而存在预存失败）
3. **前端 ConfigView 协作评分开关 UI**（后端已支持 `GET/PUT /config/peer-review-enabled`，前端需在系统配置页面增加开关）
4. **考核周期创建/编辑页面协作评分开关 UI**（后端已支持 `peer_review_enabled` 字段，前端需在周期配置中增加继承全局 + 手动覆盖的开关）

## 后端 API 路由详解

| 模块 | 文件 | 关键端点 | 说明 |
|------|------|----------|------|
| **认证** | `auth.py` | `POST /auth/login`, `/auth/refresh`, `/auth/me`, `/auth/change-password` | JWT 登录、限流（5 次失败锁 30 分钟）、密码复杂度校验 |
| **员工** | `employees.py` | `GET /employees`, `POST /employees/import`, `GET /employees/{id}/subordinates` | 递归子部门查询、Excel 批量导入、经理数据隔离 |
| **部门** | `departments.py` | `GET /departments`, `GET /positions`, `POST /positions` | 部门层级、岗位管理、删除保护（有员工/岗位时禁止删除） |
| **考核周期** | `cycles.py` | `GET /assessment-cycles`, `POST /assessment-cycles/launch`, `POST /assessment-cycles/{id}/publish` | 周期创建、启动（自动创建考核记录和 KPI 快照）、发布 |
| **KPI 模板** | `kpi_templates.py` | `GET /kpi-templates`, `POST /kpi-templates/{id}/adjust` | KPI 模板 CRUD、KPI 动态调整申请与审批 |
| **系统配置** | `config.py` | `GET /config/grade-rules`, `PUT /config/dimension-weights`, `GET /config/peer-review-enabled` | 等级规则、维度权重、评价人权重、小部门豁免配置、协作评分开关（全局默认值） |
| **仪表盘** | `dashboard.py` | `GET /dashboard`, `/dashboard/manager`, `/dashboard/peer`, `/dashboard/employee` | 按角色隔离统计（Admin/HR 看全局，经理看团队，员工只看自己） |
| **申诉** | `appeals.py` | `GET /appeals`, `POST /appeals`, `POST /appeals/{id}/review` | 申诉创建、审批（支持修改总分和等级） |
| **评分** | `scores.py` | `GET /scores/summary/{cycle_id}`, `POST /scores/calculate/{cycle_id}`, `POST /scores/manager/{record_id}` | 加权计算、强制分布、评分草稿、详情查询、分数掩码 |
| **审批** | `approvals.py` | `GET /approvals/pending`, `POST /approvals/{id}/approve`, `POST /approvals/{id}/rollback` | 多级审批链（默认：直线上级→部门负责人→HR 负责人）、全表扫描优化 |
| **绩效面谈** | `interviews.py` | `GET /interviews/pending`, `POST /interviews/{record_id}` | 面谈记录、C/D 等级必须填写改进计划 |
| **报表** | `reports.py` | `GET /reports/cycle/{id}/distribution`, `GET /reports/record/{id}/pdf` | 等级分布统计、Excel 导出、PDF 档案生成 |
| **协作评分** | `peers.py` | `GET /peer-reviewers/my-reviews`, `POST /peer-reviewers` | 协作人待评列表、分配协作人、防止自我评分 |
| **日志** | `logs.py` | `GET /logs`, `GET /logs/actions` | 操作日志分页查询、按 action/target_type/日期范围过滤 |

> **注意**：后端同时挂载了两套路由前缀：
> - `/api/v1/*` — 主 API 前缀
> - `/*` — 向后兼容的无前缀路由（直接 `/auth/login` 等）

## 前端架构详解

### 技术栈
- **框架**：Vue 3 + Vite 5 + Vue Router 4
- **UI 库**：Element Plus（全量注册图标）
- **状态管理**：Pinia（`stores/auth.js` 持久化到 `localStorage`，`stores/app.js` 管理 UI 状态）
- **图表**：ECharts（趋势图）
- **HTTP**：Axios（统一拦截器，业务错误码自动 `ElMessage.error`）
- **Excel**：xlsx.js（导入/导出）

### 路由守卫
- 未登录自动跳转 `/login`
- `meta.roles` 控制页面访问权限（`admin`, `hr`, `manager`, `employee`, `peer`）
- 所有视图组件懒加载

### API 封装结构
`src/api/` 下按模块拆分：
- `request.js` — Axios 实例，`baseURL: '/api'`，请求拦截器注入 `Bearer token`，响应拦截器处理业务错误码
- `auth.js`, `employees.js`, `departments.js`, `cycles.js`, `scores.js`, `approvals.js`, `appeals.js`, `interviews.js`, `reports.js`, `peers.js`, `logs.js`, `config.js`, `kpiAdjustment.js`, `distribution.js`, `kpi-templates.js`

### 公共组件
- `Layout.vue` — 侧边栏 + 头部 + 主内容区，菜单权限按角色控制
- `PageContainer.vue` — 页面标题容器
- `BreadcrumbNav.vue` — 面包屑导航

## 前端页面清单

| 目录 | 页面 | 角色 | 核心功能 |
|------|------|------|----------|
| `login/` | `LoginView.vue` | 公共 | 登录页，支持回车提交 |
| `dashboard/` | `DashboardView.vue` | 全部 | 角色化仪表盘（统计卡片 + 快捷入口） |
| `employees/` | `EmployeeList.vue` | Admin/HR | 员工 CRUD、Excel 导入、部门/岗位级联选择 |
| `departments/` | `DepartmentList.vue` | Admin/HR | 部门层级管理、岗位管理（内联编辑） |
| `cycles/` | `CycleList.vue` | Admin/HR | 考核周期创建/启动/发布、进度查看、协作人分配 |
| `kpi-templates/` | `KpiTemplateList.vue` | Admin/HR | 按岗位配置 KPI 模板及权重 |
| `config/` | `ConfigView.vue` | Admin | 等级规则、维度权重、评价人权重、小部门豁免（Tab 切换） |
| `summary/` | `SummaryDashboard.vue` | Admin/HR | 周期汇总、触发计算、等级分布统计 |
| `distribution-review/` | `DistributionReview.vue` | Admin/HR | 强制分布调整预览、特批候选人批量审批 |
| `audit/` | `OperationLog.vue` | Admin/HR | 操作日志审计（按 action/目标类型/日期过滤） |
| `score-sheet/` | `ScoreSheetView.vue` | Manager | 上级评分（员工选择、三维度评分、KPI 明细、经理评语、草稿保存） |
| `approval-workbench/` | `ApprovalWorkbench.vue` | Manager/HR | 审批工作台（待审批列表、通过/驳回/回退、异常标记） |
| `interview/` | `InterviewList.vue` | Manager | 绩效面谈记录（C/D 等级必须填写改进计划） |
| `kpi-adjustment/` | `KpiAdjustmentRequest.vue` | Manager | KPI 调整申请（选择 KPI、填写新目标和理由） |
| `kpi-adjustment/` | `KpiAdjustmentApproval.vue` | Manager/HR | KPI 调整审批（批量通过/驳回） |
| `peer-review/` | `PeerReviewList.vue` | Peer | 协作评分列表（待办/已办分区，按截止时间排序） |
| `peer-review/` | `PeerReviewScore.vue` | Peer | 协作评分页面（能力维度 0-100，锚点提示） |
| `self-assessment/` | `SelfAssessment.vue` | Employee | 自评页面（三维度评分、草稿保存、提交后不可修改） |
| `my-performance/` | `MyPerformance.vue` | Employee | 我的绩效（趋势图、历史记录、详情抽屉、PDF 下载、申诉） |
| `appeal/` | `AppealView.vue` | Employee | 员工申诉（选择已发布记录、填写理由、查看申诉历史） |
| `appeal/` | `AppealList.vue` | Admin/HR | 申诉管理列表（审批通过/驳回） |
| `reports/` | `ReportExport.vue` | Admin/HR | 报表导出（选择周期、下载 Excel） |

## 核心服务逻辑

### 强制分布降级算法（`services/distribution_enforcer.py`）
- 按部门统计各等级（A/B/C/D）人数，检查是否超出比例上限
- 小部门豁免（≤5 人时放宽限制）
- 超标时从低到高排序，依次降级（A→B→C→D），最多迭代 10 次
- 返回调整后记录、调整日志、特批候选人名单

### 操作日志（`services/operation_logger.py`）
- 统一写入 `operation_logs` 表，支持 `old_value`/`new_value` JSON 序列化
- 只 `flush` 不 `commit`，由调用方控制事务边界

### PDF 生成（`utils/pdf_generator.py`）
- ReportLab 生成 A4 绩效考核档案 PDF
- 包含：基本信息、三维度得分、总分、等级、经理评语
- 边缘情况：记录不存在时返回空字节

## 关键注意点（补充）

- **启动服务前先用 `restart-services.bat` 检查端口占用**，避免旧进程缓存旧代码
- **后端严禁使用 `--reload`**，Windows 环境 Uvicorn reload 不可靠，使用 `restart.bat` 或 `taskkill + uvicorn` 手动重启
- `app/auth.py` 的 `require_role` 已增加 `is_active` 纵深防御（P1-22）
- `app/routers/approvals.py` 的 `get_pending_approvals` 已改为 SQL 预过滤（P1-23），避免全表遍历
- `app/routers/dashboard.py` 的统计已按角色隔离（P1-21），管理员/HR 看全局，经理看团队，员工只看自己
- `app/routers/scores.py` 的加权计算逻辑：当存在 KPI 快照时，业绩维度得分由 KPI 得分替代；经理与自评差异超过 20 分时会标记异常
- `frontend/vite.config.js` 的代理目标端口是 `8014`（与 `restart-services.bat` 一致），不是 `8000`
- 前端 `request.js` 的响应拦截器**只将数字类型的 `code` 视为业务状态码**，避免字符串编码（如部门 `code`）被误判

## 端到端（E2E）测试

项目已集成 **Playwright**，支持从真实浏览器触发页面点击的端到端测试。

### 关键文件

| 文件 | 说明 |
|------|------|
| `frontend/playwright.config.ts` | Playwright 主配置：测试目录 `tests/e2e`、Chromium 桌面浏览器、自动截图/录屏/追踪、自动启动前端 dev server。 |
| `frontend/tests/e2e/auth-login.spec.ts` | 首个 E2E 测试套件：覆盖登录成功、登录失败、未登录重定向 3 个场景。 |
| `frontend/package.json` | 已添加 `test:e2e`（无头模式）和 `test:e2e:ui`（UI 调试模式）脚本。 |

### 环境前提

运行 E2E 测试前，需确保以下服务已启动：

1. **后端 API**（端口 8014）：

   ```bash
   cd backend
   .venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8014
   ```

2. **前端 Dev Server**（端口 3000）：由 Playwright 的 `webServer` 配置自动启动，无需手动执行。

### 常用命令速查

```bash
cd frontend

# 无头模式运行（CI/快速验证）
npm run test:e2e
# 等价于：npx playwright test --project=chromium

# 有头模式（弹出 Chromium 窗口，可观察过程）
npx playwright test --project=chromium --headed

# UI 调试模式（交互式时间轴、DOM 快照、逐帧回放）
npm run test:e2e:ui
# 等价于：npx playwright test --ui

# 慢动作观察（每个操作延迟 1 秒）
# 修改 playwright.config.ts -> use.launchOptions: { slowMo: 1000 } 后运行 --headed

# 查看 HTML 报告
npx playwright show-report
```

### 选择器策略建议

Element Plus 组件渲染后 DOM 结构复杂，推荐以下定位方式：

- **表单输入**：`page.getByPlaceholder('用户名')`（依赖 placeholder 文本）
- **按钮**：`page.getByRole('button', { name: '登录' })`（依赖按钮文本）
- **页面标题**：`page.getByRole('heading', { name: '仪表盘' })`（避免 `getByText` 匹配到导航菜单）
- **统计卡片**：`page.locator('.stat-label').filter({ hasText: '员工总数' })`（精确到 stat-label 容器）

⚠️ 避免直接用 `page.getByText('考核周期')` 等宽泛文本，容易匹配到导航菜单、表格标题等多个元素导致 `strict mode violation`。

### 测试产物

- 失败时自动截图：`test-results/<test-name>/test-failed-1.png`
- 失败时自动录屏：`test-results/<test-name>/video.webm`
- 追踪文件（trace）：`test-results/<test-name>/trace.zip`，可用 `npx playwright show-trace trace.zip` 查看
- HTML 报告：`frontend/playwright-report/index.html`
