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

| 账号 | 密码 | 角色 |
|------|------|------|
| admin | admin123 | 管理员 |
| hr001 | Hr001@123 | HR |
| mgr001 | Mgr001@123 | 经理 |
| emp001 | Emp001@123 | 员工 |
| peer001 | Peer001@123 | 协作人 |
| exec001 | Exec001@123 | 高层 |

## 快速启动

```bash
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
cd frontend && npm run dev
```

## 剩余未实现（P2 及后续）

1. **时间窗口逾期检测与自动锁定/提醒机制**（如自评截止后自动锁定并发送提醒）
2. **更完整的自动化测试覆盖**（当前 `test_approvals.py` 部分测试因 `approve_record` 的 `status == "pending_approval"` 强校验与测试用例状态不一致而存在预存失败）

## 关键注意点

- 启动服务前先用 `restart-services.bat` 检查端口占用，避免旧进程缓存旧代码
- `app/auth.py` 的 `require_role` 已增加 `is_active` 纵深防御（P1-22）
- `app/routers/approvals.py` 的 `get_pending_approvals` 已改为 SQL 预过滤（P1-23），避免全表遍历
- `app/routers/dashboard.py` 的统计已按角色隔离（P1-21），管理员/HR 看全局，经理看团队，员工只看自己

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
