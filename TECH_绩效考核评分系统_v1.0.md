# 绩效考核评分系统 - 技术方案文档 (Technical Design)

> **文档版本**: v1.0  
> **编写日期**: 2026-06-28  
> **状态**: 待评审  
> **关联 PRD**: `PRD_绩效考核评分系统_v1.0.md`  
> **输出目录**: `D:\cc_project\performance_evaluation_system\`

---

## 1. 技术选型

### 1.1 选型原则
基于 PRD 确认结论（无外部集成、纯 Web、内网使用、MVP 优先），选型遵循：**开发效率高、测试友好、部署简单、Windows 开发环境友好**。

### 1.2 技术栈

| 层级 | 技术 | 版本 | 选型理由 |
|------|------|------|---------|
| **前端** | Vue 3 | ^3.4 | 渐进式框架，中文生态丰富，Element Plus 组件库成熟 |
| **前端构建** | Vite | ^5.0 | 启动快、热更新快、配置简单 |
| **前端 UI** | Element Plus | ^2.7 | 企业级后台管理组件库，表格/表单/图表完善 |
| **前端状态** | Pinia | ^2.1 | Vue 官方推荐，TypeScript 支持好，比 Vuex 简洁 |
| **前端路由** | Vue Router | ^4.3 | 官方路由，支持导航守卫（权限控制） |
| **前端图表** | ECharts | ^5.5 | 趋势图、分布图、饼图能力成熟，中文文档完善 |
| **后端** | Python FastAPI | ^0.111 | 现代异步框架，自动 API 文档，数据校验/依赖注入内置，测试极友好 |
| **后端 ORM** | SQLAlchemy | ^2.0 | Python 事实标准 ORM，支持 SQLite→MySQL 无缝迁移 |
| **数据库** | SQLite (MVP) | 3.x | 零配置、单文件、内网桌面/服务器均可运行，后续可迁移至 MySQL |
| **数据迁移** | Alembic | ^1.13 | SQLAlchemy 官方迁移工具，版本化数据库结构 |
| **测试** | pytest | ^8.0 | Python 标准测试框架，FastAPI 内置 TestClient |
| **部署** | Uvicorn | ^0.30 | ASGI 服务器，单命令启动，支持 Windows |

### 1.3 不选 Java/Django 的理由
- **不选 Spring Boot**: 需要 Maven/Gradle 配置，启动慢，开发反馈周期长，对于 MVP 过重。
- **不选 Django**: 模板引擎耦合度高，前后端分离不如 FastAPI 纯粹；MVP 不需要 Django Admin 的复杂度。

---

## 2. 系统架构

### 2.1 整体架构

采用经典 **前后端分离 B/S 架构**：

```
┌─────────────────────────────────────────────────────────────┐
│                        客户端浏览器                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Vue 3 SPA (Vite + Element Plus + ECharts + Pinia)   │   │
│  │  • 登录页 / 评分页 / 汇总页 / 报表页 / 配置页          │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP REST API (JSON)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI 后端服务                            │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────┐ │
│  │ 认证模块    │  │ 考核管理    │  │ 评分管理    │  │ 报表模块 │ │
│  │ (JWT)      │  │ (CRUD)     │  │ (计算)      │  │ (统计)  │ │
│  └────────────┘  └────────────┘  └────────────┘  └────────┘ │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐             │
│  │ 审批流程    │  │ KPI 模板   │  │ 员工管理    │             │
│  │ (状态机)   │  │ (配置)     │  │ (CRUD)     │             │
│  └────────────┘  └────────────┘  └────────────┘             │
└──────────────────────────┬──────────────────────────────────┘
                           │ SQLAlchemy ORM
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  SQLite 数据库 (单文件, 零配置)                                │
│  • 考核周期 / 员工 / KPI / 评分记录 / 审批记录 / 历史归档       │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 模块职责划分

| 模块 | 职责 | 核心能力 |
|------|------|---------|
| **认证模块** | 用户登录、权限校验、JWT 签发 | 基于角色的访问控制 (RBAC) |
| **员工管理** | 员工信息 CRUD、部门/岗位/考核关系维护 | Excel 导入、考核关系树 |
| **KPI 模板** | 按岗位配置 KPI 指标库、权重、目标值 | 模板版本快照 |
| **考核管理** | 考核周期 CRUD、发起考核、进度监控、状态流转 | 状态机驱动、时间窗口控制 |
| **评分管理** | 生成评分表、接收评分、自动汇总计算 | 加权算法、差异校验、锁定机制 |
| **审批流程** | 多级审批、异常标红、通过/驳回/打回 | 审批链配置、审批记录留痕 |
| **报表分析** | 等级分布、历史趋势、绩效档案 | ECharts 渲染、PDF/Excel 导出 |
| **申诉管理** | 申诉发起、复核、结果变更 | 申诉绑定考核记录、审批联动 |

---

## 2.3 前端交互与页面流设计（按角色）

系统采用 **角色驱动** 的页面导航设计，每个角色登录后看到不同的首页仪表盘和可操作菜单，降低学习成本。

#### 2.3.1 角色首页仪表盘

| 角色 | 首页核心内容 | 快捷操作入口 |
|------|------------|------------|
| **系统管理员 (admin)** | 考核周期统计卡片、系统配置待办 | 创建考核周期、配置 KPI 模板、权限管理 |
| **HR 专员 (hr)** | 当前进行中的考核周期、待处理强制分布、待审批申诉 | 发起考核、查看汇总进度、处理申诉、导出报表 |
| **部门经理 (manager)** | 我的待评列表（下属人数/进度）、待审批绩效、待面谈提醒 | 批量评分、审批下属绩效、记录面谈 |
| **协作人 (peer)** | 我的协作评分待办（按被评人分组） | 快速进入评分页 |
| **员工 (employee)** | 我的当前考核状态（进度条）、历史绩效趋势图（近4周期） | 进入自评、查看历史绩效、发起申诉 |
| **高管 (executive)** | 全公司绩效分布、部门对比、趋势分析 | 查看仪表盘（只读） |

#### 2.3.2 核心页面交互设计

**（1）评分页（Score Sheet）—— 员工自评 / 上级评分 / 协作评分**
- **左侧导航**：固定显示被评人信息（姓名、岗位、部门）、当前考核周期、倒计时提醒。
- **评分锚点展示**：每个维度（业绩/能力/态度）下方直接嵌入评分参考标准（如「90-100 = 优秀，超出预期...」），采用 Element Plus 的  组合组件，鼠标悬停显示锚点说明。
- **实时校验**：
  - 输入分数超出 0-100 范围时，输入框边框变红，提示「分数需在 0-100 之间」。
  - 上级评分与自评分差异超过 20 分时，弹出确认对话框：「您给 XX 维度打的 65 分与员工自评 90 分差异较大，请确认是否继续？」
  - 所有维度未填完时，「提交」按钮置灰不可用。
- **KPI 逐项评分**：业绩维度下展开 KPI 列表，每项含「指标名称 | 目标值 | 权重 | 自评分 | 上级评分」五列，上级评分时可对比员工自评分（并排显示）。
- **评语区**：上级评分时必填综合评语，下方显示字数统计（不少于 20 字），未达标时标红提示。

**（2）汇总页（Summary Dashboard）—— HR / 审批人视角**
- **顶部筛选栏**：按部门 / 岗位 / 等级筛选，支持关键字搜索员工姓名。
- **数据表格**：列含「员工 | 总分 | 原始等级 | 调整后等级 | 强制调整标记 | 自评/上级评/协作评 | 审批状态」。
  - 强制调整标记：被系统降级的行，等级列旁显示 🔴 红色图标，鼠标悬停显示「因 A 等级超限，由 A 强制降至 B」。
  - 异常分数标红：总分 <60 或 >98 的行，总分单元格背景淡红色。
- **分布图联动**：表格上方显示部门等级分布饼图（原始 vs 调整后双环图），点击饼图区块自动筛选表格。
- **批量操作**：HR 可选中多行，批量「导出 Excel」、「触发重新计算」。

**（3）审批工作台（Approval Workbench）—— 管理者视角**
- **待审批卡片列表**：每张卡片显示员工姓名、总分、等级、异常标记（🔴）、强制调整标记（🔴）。
- **详情抽屉**：点击卡片从右侧滑出详情抽屉，内含：
  - 员工评分表摘要（各维度得分）
  - 历史绩效趋势图（该员工近 4 周期总分折线）
  - 强制调整说明（如有）
  - 审批按钮：通过 / 驳回（填写理由） / 打回重评（二次确认）
- **批量审批**：部门负责人可批量通过无异常标记的记录（需勾选「我已确认以上人员评分无误」）。

**（4）我的绩效（My Performance）—— 员工视角**
- **当前考核卡片**：大字体显示当前周期总分与等级，进度条显示考核阶段（自评 → 上级评 → 汇总中...）。
- **历史趋势图**：ECharts 折线图，X 轴为周期，Y 轴为总分，支持点击切换「总分 / 业绩 / 能力 / 态度」四条线。
- **绩效档案列表**：按时间倒序展示历次考核，点击展开查看详情（评分表、评语、申诉记录）。
- **申诉入口**：当前考核结果下方常驻「对结果有异议？」按钮，点击展开申诉表单（申诉理由下拉框 + 详细描述文本框）。

**（5）强制分布处理页（Distribution Review）—— HR 视角**
- **超标部门列表**：左侧显示所有超标部门，红色高亮，含「部门名称 | 人数 | A 超标 X 人 | 操作」。
- **智能调整预览**：点击部门后，右侧展示「调整前 vs 调整后」对比表格，可逐行勾选「确认降级」。
- **重新计算按钮**：HR 确认调整后，点击「重新计算并校验」，系统刷新分布状态，合规后自动解锁进入审批。


**（6）员工批量导入页（Employee Import）—— HR 视角**
- **三步引导式界面**：
  - Step 1「下载模板」：展示模板字段说明，提供「下载空模板」和「下载带示例模板」两个按钮。
  - Step 2「上传文件」：拖拽上传区域（支持 `.xlsx`），上传后显示文件解析进度条。
  - Step 3「预览与确认」：表格展示解析结果，错误行标红并显示具体错误（如「第5行：工号 EMP003 已存在」），HR 可在线编辑修正或下载错误报告。确认无误后点击「确认导入」。
- **导入结果弹窗**：显示成功/失败数量，提供「下载错误报告」和「查看导入员工」按钮。

**（7）绩效面谈页（Interview）—— 上级视角**
- **待面谈列表**：显示已通过审批的下属，按面谈预约时间排序。
- **面谈记录表单**：员工信息（只读）、面谈时间（日期选择器）、面谈地点、沟通内容（富文本）、改进计划（C/D 等级必填，字数 ≥50）。
- **历史面谈关联**：下方折叠面板显示该员工历次面谈记录，供上级参考。

#### 2.3.3 交互一致性规范
- **全局导航栏**：顶部固定，左侧 Logo + 系统名称，右侧显示当前用户角色 + 姓名 + 消息铃铛（红点提示待办数量）。
- **面包屑导航**：每个页面顶部显示当前位置，如「考核管理 > 2026Q2 考核 > 分数汇总」。
- **按钮状态规范**：主操作（提交/保存/确认）用 Element Plus ，危险操作（删除/打回）用 ，禁用态统一置灰并显示 Tooltip 原因。
- **加载与反馈**：所有提交操作显示 Element  全屏遮罩，成功后顶部  绿色提示，失败后红色提示并保留表单数据。
- **空状态处理**：无数据时显示友好插画 + 引导文字（如「暂无待评下属，请联系 HR 确认考核关系」）。

## 3. 数据库设计 (ER 图与表结构)

### 3.1 实体关系图

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   Department    │ 1:M   │    Employee     │ 1:M   │AssessmentRecord │
│  (部门)         │───────│   (员工)        │───────│  (考核记录)      │
└─────────────────┘       └─────────────────┘       └────────┬────────┘
       │                           │                         │
       │                           │ 1:M                     │ 1:M
       │                           ▼                         ▼
       │                    ┌─────────────────┐       ┌─────────────────┐
       │                    │  Position       │       │   ScoreDetail   │
       │                    │  (岗位)          │       │  (评分明细)      │
       │                    └─────────────────┘       └─────────────────┘
       │                           │                         │
       │                           │ 1:M                     │
       │                           ▼                         │
       │                    ┌─────────────────┐               │
       │                    │   KpiTemplate   │◄──────────────┘
       │                    │  (KPI模板)      │
       │                    └─────────────────┘
       │                           │
       │                           │ M:N
       ▼                           ▼
┌─────────────────┐       ┌─────────────────┐
│   AssessmentCycle│ 1:M  │  PeerReviewer   │
│  (考核周期)      │───────│  (协作评分关系)   │
└─────────────────┘       └─────────────────┘
       │                           │
       │ 1:M                       │ 1:M
       ▼                           ▼
┌─────────────────┐       ┌─────────────────┐
│  ApprovalRecord │       │  AppealRecord   │
│  (审批记录)      │       │  (申诉记录)      │
└─────────────────┘       └─────────────────┘
```

### 3.2 表结构设计

#### 3.2.1 `departments` — 部门表
```sql
CREATE TABLE departments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR(100) NOT NULL,        -- 部门名称
    code        VARCHAR(50) UNIQUE,             -- 部门编码
    parent_id   INTEGER,                       -- 上级部门ID
    head_id     INTEGER,                     -- 部门负责人（员工ID）
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.2.2 `positions` — 岗位表
```sql
CREATE TABLE positions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR(100) NOT NULL,        -- 岗位名称
    department_id INTEGER,                     -- 所属部门
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.2.3 `employees` — 员工表
```sql
CREATE TABLE employees (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_no     VARCHAR(50) UNIQUE NOT NULL,  -- 工号
    name            VARCHAR(100) NOT NULL,        -- 姓名
    department_id   INTEGER,                       -- 部门ID
    position_id     INTEGER,                       -- 岗位ID
    manager_id      INTEGER,                       -- 直属上级ID
    is_department_head BOOLEAN DEFAULT FALSE,      -- 是否部门负责人（用于审批链）
    is_active       BOOLEAN DEFAULT TRUE,          -- 是否在职
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.2.4 `assessment_cycles` — 考核周期表
```sql
CREATE TABLE assessment_cycles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            VARCHAR(200) NOT NULL,        -- 周期名称
    type            VARCHAR(20) NOT NULL,          -- 季度/年度
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    self_due_date   DATE,                          -- 自评截止日
    manager_due_date DATE,                         -- 上级评截止日
    peer_due_date   DATE,                          -- 协作评截止日
    status          VARCHAR(50) DEFAULT 'not_started', -- 状态
    dimension_weights TEXT NOT NULL,               -- JSON: {"performance":0.6,"ability":0.2,"attitude":0.2}
    reviewer_weights TEXT NOT NULL,                -- JSON: 评分人权重
    grade_rules     TEXT NOT NULL,                 -- JSON: 等级规则
    is_distribution_enabled BOOLEAN DEFAULT TRUE,  -- 是否启用强制分布（MVP默认开启）
    small_dept_exemption BOOLEAN DEFAULT TRUE,     -- 小部门豁免（≤5人时放宽）
    approval_chain_config TEXT,                    -- JSON: 审批链配置
    is_locked       BOOLEAN DEFAULT FALSE,         -- 已归档锁定
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.2.5 `kpi_templates` — KPI 模板表
```sql
CREATE TABLE kpi_templates (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id     INTEGER NOT NULL,              -- 关联岗位
    name            VARCHAR(200) NOT NULL,          -- 指标名称
    weight          DECIMAL(5,2) NOT NULL,          -- 权重(在业绩维度内)
    target_value    VARCHAR(255),                  -- 目标值
    scoring_method  VARCHAR(50) DEFAULT 'percentage', -- 计分方式
    description     TEXT,                          -- 评分标准说明
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.2.6 `assessment_records` — 员工考核记录表（核心）
```sql
CREATE TABLE assessment_records (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id            INTEGER NOT NULL,            -- 考核周期
    employee_id         INTEGER NOT NULL,            -- 被考核员工
    position_id         INTEGER,                     -- 考核时岗位快照
    department_id       INTEGER,                     -- 考核时部门快照（用于强制分布按部门统计）
    kpi_snapshot        TEXT,                        -- JSON: KPI模板快照
    
    -- 各评分人原始分 (JSON)
    self_scores         TEXT,                        -- {"performance":85,"ability":90,"attitude":88}
    self_facts          TEXT,                        -- JSON: {"performance":"主导完成XX项目","ability":"自学Vue 3","attitude":"主动承担周末值班"}
    manager_scores      TEXT,                        -- 上级评分
    peer_scores         TEXT,                        -- 协作评分
    peer_comments       TEXT,                        -- JSON: [{"reviewer_name":"赵晓峰","ability_score":86,"comment":"需求评审响应及时..."}]
    
    -- 加权后维度得分
    weighted_performance DECIMAL(5,2),               -- 业绩加权分
    weighted_ability     DECIMAL(5,2),               -- 能力加权分
    weighted_attitude    DECIMAL(5,2),               -- 态度加权分
    total_score          DECIMAL(5,2),                -- 总分
    grade                VARCHAR(10),                -- A/B/C/D（强制调整后的最终等级）
    original_grade       VARCHAR(10),                -- 强制调整前的原始等级（用于追溯）
    
    manager_comment     TEXT,                        -- 上级综合评语
    interview_record    TEXT,                        -- JSON: 面谈记录
    appeal_record       TEXT,                        -- JSON: 申诉记录
    
    status              VARCHAR(50) DEFAULT 'pending_self', -- 考核状态
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.2.7 `score_details` — 评分明细表（KPI 逐项评分）
```sql
CREATE TABLE score_details (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id       INTEGER NOT NULL,              -- 考核记录ID
    kpi_template_id INTEGER,                       -- KPI指标ID
    kpi_name        VARCHAR(200),                   -- KPI名称快照
    weight          DECIMAL(5,2),                   -- KPI权重快照
    self_score      DECIMAL(5,2),                    -- 自评分
    manager_score   DECIMAL(5,2),                    -- 上级评分
    target_value    VARCHAR(255),                   -- 目标值快照
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.2.8 `approval_records` — 审批记录表
```sql
CREATE TABLE approval_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id       INTEGER NOT NULL,              -- 考核记录ID
    approver_id     INTEGER NOT NULL,              -- 审批人ID
    approver_role   VARCHAR(50),                    -- 审批角色：direct_manager/hr_head
    step_index      INTEGER DEFAULT 1,              -- 审批链中的第几步（1=直属上级, 2=HR负责人）
    action          VARCHAR(50),                    -- 通过/驳回/打回
    comment         TEXT,                          -- 审批意见
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```


#### 3.2.9 `users` — 系统用户表（登录账号）
```sql
CREATE TABLE users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    VARCHAR(100) UNIQUE NOT NULL,       -- 登录名：拼音 + 6位工号（如 zhangxiguan010001）
    password_hash VARCHAR(255) NOT NULL,           -- 哈希密码(bcrypt)，默认密码 = 工号 + @123
    role        VARCHAR(50) NOT NULL,              -- admin/hr/manager/employee/peer/executive
    role_code   VARCHAR(10),                       -- 角色编码：01=admin, 02=hr, 03=manager, 04=employee, 05=peer, 06=executive
    employee_id INTEGER,                           -- 关联员工ID
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.2.10 `cycle_employees` — 考核周期参与人员表

用于明确记录哪些员工被纳入本次考核，支持中途增删和状态跟踪。

```sql
CREATE TABLE cycle_employees (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id    INTEGER NOT NULL,              -- 考核周期ID
    employee_id INTEGER NOT NULL,              -- 员工ID
    status      VARCHAR(50) DEFAULT 'pending', -- pending/in_progress/completed/excluded
    added_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cycle_id, employee_id)
);
```

#### 3.2.11 `peer_reviewers` — 协作评分关系表

定义跨部门协作评分关系，支持一个员工被多人协作评分。

```sql
CREATE TABLE peer_reviewers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id        INTEGER NOT NULL,          -- 考核周期ID
    employee_id     INTEGER NOT NULL,          -- 被考核员工ID
    reviewer_id     INTEGER NOT NULL,          -- 协作评分人ID
    reviewer_department_id INTEGER,            -- 评分人所属部门（快照）
    status          VARCHAR(50) DEFAULT 'pending', -- pending/completed/skipped
    UNIQUE(cycle_id, employee_id, reviewer_id)
);
```

#### 3.2.12 `operation_logs` — 操作日志表

记录所有敏感操作，满足审计追溯要求。

```sql
CREATE TABLE operation_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,              -- 操作用户ID
    action      VARCHAR(100) NOT NULL,         -- 操作类型：approve, reject, score_submit, grade_override, distribution_review...
    target_type VARCHAR(50),                   -- 操作对象类型：assessment_record, approval, appeal_record...
    target_id   INTEGER,                       -- 操作对象ID
    old_value   TEXT,                          -- 变更前快照（JSON）
    new_value   TEXT,                          -- 变更后快照（JSON）
    ip_address  VARCHAR(50),                   -- 操作IP
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.2.13 `appeal_records` — 申诉记录表（独立表）

从 `assessment_records` 中剥离，支持独立查询和状态跟踪。

```sql
CREATE TABLE appeal_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id       INTEGER NOT NULL,          -- 关联考核记录ID
    employee_id     INTEGER NOT NULL,          -- 申诉人ID
    reason          TEXT NOT NULL,             -- 申诉理由
    detail          TEXT,                      -- 详细说明
    status          VARCHAR(50) DEFAULT 'pending', -- pending/under_review/resolved/rejected
    reviewer_id     INTEGER,                   -- 复核人ID
    review_result   TEXT,                      -- 复核结论
    resolved_at     TIMESTAMP,                 -- 处理完成时间
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.2.14 `interview_records` — 面谈记录表（独立表）

从 `assessment_records` 中剥离，支持面谈历史独立查询。

```sql
CREATE TABLE interview_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id       INTEGER NOT NULL,          -- 关联考核记录ID
    interviewer_id  INTEGER NOT NULL,          -- 面谈人（上级）ID
    interview_time  TIMESTAMP,               -- 面谈时间
    location        VARCHAR(200),              -- 面谈地点
    content         TEXT,                      -- 沟通内容
    improvement_plan TEXT,                     -- 改进计划（C/D等级必填）
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. 接口设计 (REST API)

### 4.1 接口规范
- **Base URL**: `http://localhost:8000/api/v1`
- **认证方式**: JWT Bearer Token (`Authorization: Bearer <token>`)
- **响应格式**: 
  ```json
  {
    "code": 200,
    "message": "success",
    "data": { ... }
  }
  ```

### 4.2 核心接口列表

#### 认证模块
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/auth/login` | 用户登录 | 公开 |
| POST | `/auth/refresh` | 刷新 Token | 已登录 |
| GET | `/auth/me` | 获取当前用户 | 已登录 |

#### 员工管理
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/employees` | 员工列表 | admin/hr |
| POST | `/employees` | 新增员工 | admin/hr |
| PUT | `/employees/{id}` | 修改员工 | admin/hr |
| DELETE | `/employees/{id}` | 删除员工 | admin/hr |
| GET | `/employees/import-template` | 下载批量导入模板 | admin/hr |
| POST | `/employees/import` | Excel 导入 | admin/hr |
| POST | `/employees/import-preview` | 导入预览（校验不保存） | admin/hr |
| GET | `/employees/{id}/subordinates` | 获取下属 | manager |

#### 考核周期管理
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/cycles` | 周期列表 | 登录用户 |
| POST | `/cycles` | 创建周期 | admin |
| PUT | `/cycles/{id}` | 修改周期 | admin |
| POST | `/cycles/{id}/launch` | 发起考核 | admin/hr |
| GET | `/cycles/{id}/progress` | 进度监控 | admin/hr |

#### 评分管理
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/scores/my-assessment` | 获取我的评分表 | employee |
| POST | `/scores/self` | 提交自评 | employee |
| GET | `/scores/to-review` | 待评列表 | manager |
| POST | `/scores/manager/{record_id}` | 提交上级评分 | manager |
| POST | `/scores/peer/{record_id}` | 提交协作评分 | peer |
| GET | `/scores/summary/{cycle_id}` | 分数汇总表 | admin/hr/manager |
| POST | `/scores/calculate/{cycle_id}` | 触发汇总计算 | admin/hr |

#### 审批流程
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/approvals/pending` | 我的待审批 | manager/hr |
| POST | `/approvals/{record_id}/approve` | 通过 | 审批人 |
| POST | `/approvals/{record_id}/reject` | 驳回 | 审批人 |
| POST | `/approvals/{record_id}/rollback` | 打回重评 | 审批人 |

#### 报表分析
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/reports/cycle/{cycle_id}/distribution` | 等级分布（原始 vs 调整后） | admin/hr/manager |
| GET | `/reports/cycle/{cycle_id}/distribution-adjustments` | 强制调整人员清单 | admin/hr |
| GET | `/reports/employee/{employee_id}/trend` | 历史趋势 | 本人/上级/hr |
| GET | `/reports/cycle/{cycle_id}/export` | 导出 Excel | admin/hr |
| GET | `/reports/record/{record_id}/pdf` | 生成 PDF 档案 | 本人/上级/hr |

#### 考核记录管理
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/records/{record_id}` | 获取考核记录详情 | 本人/上级/hr |
| PUT | `/records/{record_id}/status` | 修改考核记录状态（HR强制流转） | admin/hr |
| POST | `/records/{record_id}/draft` | 保存评分草稿 | employee/manager/peer |
| GET | `/records/{record_id}/draft` | 获取评分草稿 | employee/manager/peer |

#### 申诉管理
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/appeals` | 提交申诉 | employee |
| GET | `/appeals/my-appeals` | 我的申诉历史 | employee |
| GET | `/appeals/pending` | 待处理申诉列表 | hr |
| GET | `/appeals/{id}` | 申诉详情 | employee/hr |
| POST | `/appeals/{id}/review` | 复核并处理申诉 | hr |
| GET | `/appeals/cycle/{cycle_id}` | 获取某周期所有申诉 | admin/hr |

#### 绩效面谈管理
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/interviews/pending` | 待面谈列表 | manager |
| POST | `/interviews/{record_id}` | 创建面谈记录 | manager |
| GET | `/interviews/{record_id}` | 获取面谈详情 | manager/employee |
| PUT | `/interviews/{record_id}` | 更新面谈记录 | manager |
| GET | `/interviews/employee/{employee_id}` | 员工面谈历史 | manager/hr/employee |

#### 部门与岗位管理
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/departments` | 部门列表 | 登录用户 |
| POST | `/departments` | 新增部门 | admin/hr |
| PUT | `/departments/{id}` | 修改部门 | admin/hr |
| DELETE | `/departments/{id}` | 删除部门 | admin/hr |
| GET | `/positions` | 岗位列表 | 登录用户 |
| POST | `/positions` | 新增岗位 | admin/hr |
| PUT | `/positions/{id}` | 修改岗位 | admin/hr |
| DELETE | `/positions/{id}` | 删除岗位 | admin/hr |

#### 考核周期人员管理
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/cycles/{cycle_id}/employees` | 周期参与人员列表 | admin/hr |
| POST | `/cycles/{cycle_id}/employees` | 批量添加人员到周期 | admin/hr |
| DELETE | `/cycles/{cycle_id}/employees/{employee_id}` | 从周期移除人员 | admin/hr |

#### 协作评分人管理
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/peer-reviewers/cycle/{cycle_id}` | 协作评分关系列表 | admin/hr |
| POST | `/peer-reviewers` | 分配协作评分人 | admin/hr |
| DELETE | `/peer-reviewers/{id}` | 移除协作评分人 | admin/hr |
| GET | `/peer-reviewers/my-reviews` | 我的待协作评分列表 | peer |

#### 审批辅助接口
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/approvals/record/{record_id}/history` | 审批历史 | 登录用户 |
| GET | `/approvals/chain-config` | 获取审批链配置 | admin/hr |
| PUT | `/approvals/chain-config` | 修改审批链配置 | admin |
| POST | `/approvals/{record_id}/reassign` | 重新指派审批人 | hr |
| POST | `/scores/{record_id}/reassign-reviewer` | 重新指派评分人 | hr |

#### 系统配置
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/config/grade-rules` | 获取等级规则 | admin |
| PUT | `/config/grade-rules` | 更新等级规则 | admin |
| GET | `/config/dimension-weights` | 获取维度权重 | admin |
| PUT | `/config/dimension-weights` | 更新维度权重 | admin |
| GET | `/config/reviewer-weights` | 获取评分人权重 | admin |
| PUT | `/config/reviewer-weights` | 更新评分人权重 | admin |
| GET | `/config/small-dept-exemption` | 获取小部门豁免配置 | admin |
| PUT | `/config/small-dept-exemption` | 更新小部门豁免配置 | admin |
| GET | `/config/peer-review-enabled` | 获取协作评分开关全局默认值 | admin |
| PUT | `/config/peer-review-enabled` | 更新协作评分开关全局默认值 | admin |
#### 首页仪表盘与统计
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/dashboard` | 首页仪表盘数据 | 登录用户 |
| GET | `/dashboard/cycles` | 考核周期统计 | admin/hr |
| GET | `/dashboard/approvals` | 待审批统计 | manager/hr |
| GET | `/dashboard/scores` | 评分进度统计 | manager/hr |

#### 审计日志
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/logs` | 操作日志查询 | admin/hr |
| GET | `/logs/record/{record_id}` | 某考核记录的操作日志 | admin/hr |

#### 账户管理
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/auth/change-password` | 修改密码 | 登录用户 |
| POST | `/auth/logout` | 退出登录 | 登录用户 |

#### KPI 模板管理
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/kpi-templates` | 模板列表 | admin |
| POST | `/kpi-templates` | 新增模板 | admin |
| PUT | `/kpi-templates/{id}` | 修改模板 | admin |
| DELETE | `/kpi-templates/{id}` | 删除模板 | admin |

---

## 5. 核心算法与计算逻辑

### 5.1 加权总分计算算法

```python
def calculate_weighted_score(record: AssessmentRecord) -> dict:
    """
    计算加权总分与各维度加权分
    """
    # 从考核周期读取权重配置
    dim_weights = json.loads(record.cycle.dimension_weights)  # {"performance":0.6, "ability":0.2, "attitude":0.2}
    reviewer_weights = json.loads(record.cycle.reviewer_weights)
    # reviewer_weights 示例:
    # {
    #   "performance": {"self": 0.3, "manager": 0.7},
    #   "ability": {"self": 0.2, "manager": 0.6, "peer": 0.2},
    #   "attitude": {"self": 0.2, "manager": 0.8}
    # }
    
    result = {}
    for dimension, dim_weight in dim_weights.items():
        # 获取该维度下各评分人的分数
        scores = {
            "self": getattr(record, "self_scores", {}).get(dimension),
            "manager": getattr(record, "manager_scores", {}).get(dimension),
            "peer": getattr(record, "peer_scores", {}).get(dimension),
        }
        # 加权计算（仅取已提交的评分）
        rw = reviewer_weights[dimension]
        total_w = 0
        weighted_sum = 0
        for reviewer, score in scores.items():
            if score is not None and reviewer in rw:
                weighted_sum += score * rw[reviewer]
                total_w += rw[reviewer]
        # 归一化：如果某评分人未提交，将其权重按比例分配给已提交人
        if total_w > 0 and total_w < 1.0:
            weighted_sum = weighted_sum / total_w
        result[dimension] = round(weighted_sum, 1)
    
    # 计算总分
    total = sum(result[d] * dim_weights[d] for d in result)
    result["total"] = round(total, 1)
    return result
```

### 5.2 等级映射算法

```python
def map_grade(total_score: float, grade_rules: dict) -> str:
    """
    根据总分映射等级
    grade_rules 示例: {"A": {"min": 90, "max": 100}, "B": {"min": 80, "max": 89.9}, ...}
    """
    for grade, rule in grade_rules.items():
        if rule["min"] <= total_score <= rule["max"]:
            return grade
    return "D"  # 默认兜底
```

### 5.3 异常分数检测

```python
def detect_anomalies(record: AssessmentRecord) -> list:
    """
    检测异常分数并返回标红提示
    """
    alerts = []
    if record.total_score and (record.total_score < 60 or record.total_score > 98):
        alerts.append(f"总分异常: {record.total_score}")
    
    # 上级评分与自评分差异超过20分
    if record.manager_scores and record.self_scores:
        for dim in ["performance", "ability", "attitude"]:
            m_score = record.manager_scores.get(dim, 0)
            s_score = record.self_scores.get(dim, 0)
            if abs(m_score - s_score) > 20:
                alerts.append(f"维度[{dim}] 上级评分与自评分差异过大: {m_score} vs {s_score}")
    return alerts
```

### 5.4 考核状态机（完整版，含异常处理）

```
not_started → pending_self → pending_manager → pending_peer（可选） →
pending_summary → pending_distribution_review（可选） →
pending_approval → pending_interview → published → [appealed] → archived

异常分支:
• 任何活跃状态 → cancelled (管理员取消考核)
• pending_self / pending_manager / pending_peer → overdue (deadline 超时，需HR干预)
```

#### 正常流转规则

| 触发条件 | 源状态 | 目标状态 | 执行者 | 说明 |
|---------|--------|---------|--------|------|
| HR 发起考核 | `not_started` | `pending_self` | HR | 系统生成评分表，通知员工自评 |
| 员工提交自评 | `pending_self` | `pending_manager` | 员工 | 校验所有维度已填写，锁定自评数据 |
| 上级提交评分 | `pending_manager` | `pending_peer` | 上级 | 如无协作评配置，则直接跳转 `pending_summary` |
| 协作人提交评分 | `pending_peer` | `pending_summary` | 协作人 | 最后一位协作人提交后自动跳转 |
| 所有评分截止 | `pending_peer` | `pending_summary` | 系统 | 超时自动跳过未提交者，标记为 skipped |
| HR 触发汇总 | `pending_summary` | `pending_distribution_review` | HR | 系统执行加权计算 + 等级映射 |
| 强制分布合规 | `pending_distribution_review` | `pending_approval` | 系统 | 自动通过，无需人工干预 |
| 强制分布不合规 + HR 确认调整 | `pending_distribution_review` | `pending_approval` | HR | HR 确认系统推荐的降级方案 |
| 审批链 Step 1 通过 | `pending_approval` | `pending_approval` | 直属上级 | Step 1 确认后进入 Step 2 |
| 审批链 Step 2 通过 | `pending_approval` | `pending_interview` | HR 负责人 | 最终审批通过，进入面谈阶段 |
| 审批驳回 | `pending_approval` | `pending_manager` | 审批人 | 返回上级修改评分，保留历史审批记录 |
| 审批打回重评 | `pending_approval` | `pending_self` | 审批人 | 清除所有评分数据，考核回到自评阶段 |
| HR 发布归档 | `published` | `archived` | HR | 数据锁定，生成 PDF 档案 |

#### 异常与边界处理

| 异常场景 | 当前状态 | 处理方式 | 目标状态 | 说明 |
|---------|---------|---------|---------|------|
| **考核取消** | 任意活跃状态 | 管理员手动取消 | `cancelled` | 已提交的评分数据保留但标记为 cancelled，不可恢复 |
| **自评超时** | `pending_self` | 系统提醒 → 员工仍未提交 | `pending_self` (overdue标记) | HR 可手动关闭该员工的自评（标记为 skipped），强制流转至 `pending_manager` |
| **上级评超时** | `pending_manager` | 截止日后上级未提交 | `pending_manager` (overdue标记) | HR 可手动指派代理人或跳过该上级评分 |
| **协作评超时** | `pending_peer` | 截止日后协作人未提交 | `pending_summary` | 系统自动跳过该协作人评分，权重按比例分配给已提交者 |
| **申诉发起** | `published` | 员工发起申诉 | `appealed` | 锁定已发布结果，HR 复核期间不可修改 |
| **申诉复核通过** | `appealed` | HR 维持原结果 | `published` | 结果不变，记录申诉驳回 |
| **申诉复核修改** | `appealed` | HR 修改结果 | `published` | 更新等级/分数，记录修改原因，通知员工 |
| **审批人离职/休假** | `pending_approval` | 原审批人无法处理 | `pending_approval` | HR 可手动重新指派审批人（需记录指派日志） |

### 5.5 强制分布校验与调整算法

系统在汇总阶段自动按部门执行强制分布校验，若超标则自动降级或拦截。

```python
def enforce_distribution(records, grade_rules, dept_size):
    """
    按部门强制分布规则校验并调整等级
    """
    from collections import Counter
    
    sorted_records = sorted(records, key=lambda r: r.total_score, reverse=True)
    
    if dept_size <= 5:
        caps = _small_dept_caps(dept_size)
    else:
        caps = {grade: int(dept_size * rule["max_ratio"]) 
                for grade, rule in grade_rules.items()}
    
    grade_counts = Counter(r.grade for r in sorted_records)
    overflow = {g: max(0, grade_counts.get(g, 0) - caps.get(g, 0)) for g in caps}
    
    adjustment_log = []
    for grade in ["A", "B", "C"]:
        if overflow[grade] > 0:
            candidates = [r for r in sorted_records if r.grade == grade]
            candidates.sort(key=lambda r: r.total_score)
            
            for i in range(overflow[grade]):
                if i < len(candidates):
                    record = candidates[i]
                    next_grade = _get_next_lower_grade(grade)
                    old_grade = record.grade
                    
                    if not record.original_grade:
                        record.original_grade = old_grade
                    
                    record.grade = next_grade
                    adjustment_log.append({
                        "employee_id": record.employee_id,
                        "total_score": record.total_score,
                        "from_grade": old_grade,
                        "to_grade": next_grade,
                        "reason": f"因{grade}等级超限（上限{caps[grade]}人），系统自动降级"
                    })
    
    final_counts = Counter(r.grade for r in sorted_records)
    is_compliant = all(final_counts.get(g, 0) <= caps.get(g, 0) for g in caps)
    
    return {
        "adjusted_records": sorted_records,
        "adjustment_log": adjustment_log,
        "is_compliant": is_compliant
    }


def _small_dept_caps(dept_size):
    if dept_size <= 1:
        return {"A": 1, "B": 1, "C": 1, "D": 1}
    elif dept_size <= 3:
        return {"A": 1, "B": 10, "C": 10, "D": 1}
    else:
        return {"A": 1, "B": 10, "C": 10, "D": 1}


def _get_next_lower_grade(grade):
    mapping = {"A": "B", "B": "C", "C": "D", "D": "D"}
    return mapping.get(grade, "D")
```

**算法说明**：
1. **按部门独立核算**：以 `department_id` 为维度分组统计。
2. **小部门豁免**：部门人数 ≤5 时，仅限制 A 和 D 各不超过 1 人，B/C 不限制。
3. **溢出降级策略**：从超限等级中按「总分由低到高」依次降级，确保高分者尽可能保留原等级。
4. **原始等级保留**：所有被强制调整的记录，系统自动在 `original_grade` 中保留调整前等级，用于审计追溯。
5. **降级日志**：每次降级操作记录详细日志，包含员工ID、总分、原始等级、调整后等级、降级原因，供审计追溯。


---

## 6. 安全与权限设计

### 6.1 角色权限矩阵 (RBAC)

| 功能 | admin (01) | hr (02) | manager (03) | employee (04) | peer (05) | executive (06) |
|------|:----------:|:-------:|:------------:|:-------------:|:---------:|:--------------:|
| 系统配置 (权重/等级规则) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 员工管理 | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| 发起考核 | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| 查看全公司汇总 | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| 查看部门汇总 | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| 查看下属绩效 | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| 查看本人绩效 | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| 自评 | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| 上级评分 | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| 协作评分 | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| 审批 | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| 申诉 | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| 申诉复核 | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| 导出报表 | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| 高管仪表盘查看 | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

### 6.2 数据隔离规则
- 员工只能查看 `employee_id` 等于本人的记录。
- 上级只能查看 `manager_id` 链下所管辖的员工的记录。
- 部门负责人可查看本部门及子部门的所有记录。
- HR 和 admin 可查看全部记录。

### 6.3 数据安全
- 密码使用 **bcrypt** 哈希存储，永不存明文。
- 已归档考核周期数据标记为 `is_locked = True`，仅 admin 可解冻修改。
- 所有敏感操作（审批通过/驳回、结果修改）写入操作日志表。

---

## 7. 项目目录结构

```
performance_evaluation_system/
├── docs/                           # 设计文档
│   ├── PRD_绩效考核评分系统_v1.0.md    # PRD (已定稿)
│   └── TECH_绩效考核评分系统_v1.0.md   # 本技术方案文档
├── backend/                        # FastAPI 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # 应用入口
│   │   ├── database.py             # SQLAlchemy 配置
│   │   ├── models.py               # 数据模型
│   │   ├── schemas.py              # Pydantic 请求/响应模型
│   │   ├── auth.py                 # JWT 认证与密码工具
│   │   ├── dependencies.py         # 依赖注入 (权限校验)
│   │   ├── routers/                # 路由模块
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # 登录认证
│   │   │   ├── employees.py        # 员工管理
│   │   │   ├── departments.py      # 部门与岗位管理
│   │   │   ├── cycles.py           # 考核周期
│   │   │   ├── scores.py           # 评分管理
│   │   │   ├── approvals.py        # 审批流程
│   │   │   ├── appeals.py          # 申诉管理
│   │   │   ├── interviews.py       # 绩效面谈
│   │   │   ├── peers.py            # 协作评分
│   │   │   ├── reports.py          # 报表分析
│   │   │   ├── kpi_templates.py    # KPI模板
│   │   │   ├── config.py           # 系统配置
│   │   │   ├── dashboard.py        # 仪表盘
│   │   │   └── logs.py             # 操作日志
│   │   ├── services/               # 业务逻辑层
│   │   │   ├── __init__.py
│   │   │   ├── score_calculator.py # 加权计算算法
│   │   │   ├── grade_mapper.py     # 等级映射算法
│   │   │   ├── distribution_enforcer.py  # 强制分布校验与调整算法
│   │   │   └── anomaly_detector.py # 异常检测算法
│   │   └── utils/                  # 工具函数
│   │       ├── __init__.py
│   │       ├── excel_import.py     # Excel导入
│   │       ├── pdf_generator.py    # PDF档案生成
│   │       └── export_excel.py     # Excel导出
│   ├── alembic/                    # 数据库迁移
│   ├── requirements.txt            # Python依赖
│   └── config.py                   # 配置文件
├── tests/                          # 系统级测试目录（根级）
│   ├── design/                     # 测试设计文档
│   ├── cases/                      # 测试用例（Markdown / Excel）
│   ├── scripts/
│   │   ├── backend/                # pytest 后端单元/集成测试
│   │   ├── frontend/               # Vitest 前端组件测试
│   │   └── e2e/                    # Playwright 端到端系统测试
│   └── debug/                      # 问题定位与调试脚本
├── frontend/                       # Vue 3 前端
│   ├── public/
│   ├── src/
│   │   ├── api/                    # Axios 请求封装
│   │   ├── assets/
│   │   ├── components/             # 公共组件
│   │   ├── router/                 # 路由配置
│   │   ├── stores/                 # Pinia 状态管理
│   │   ├── views/                  # 页面视图
│   │   │   ├── login/              # 登录页
│   │   │   ├── dashboard/          # 角色仪表盘（按角色渲染不同内容）
│   │   │   ├── employees/          # 员工管理
│   │   │   ├── departments/        # 部门与岗位管理
│   │   │   ├── cycles/             # 考核周期管理
│   │   │   ├── kpi-templates/      # KPI模板管理
│   │   │   ├── config/             # 系统配置
│   │   │   ├── score-sheet/        # 评分页（自评/上级评/协作评）
│   │   │   ├── my-performance/     # 我的绩效（历史趋势/档案/申诉）
│   │   │   ├── summary/            # 分数汇总与强制分布处理
│   │   │   ├── distribution-review/ # 强制分布处理（HR专用）
│   │   │   ├── approval-workbench/ # 审批工作台（待审批/已审批）
│   │   │   ├── peer-review/        # 协作评分待办
│   │   │   ├── interview/          # 绩效面谈记录
│   │   │   ├── appeal/             # 申诉提交与跟踪
│   │   │   ├── audit/              # 操作日志审计
│   │   │   ├── reports/            # 报表分析（分布图/趋势图/导出）
│   │   │   └── admin/              # 系统配置（权重/等级规则/KPI模板）
│   │   ├── App.vue
│   │   └── main.js
│   ├── package.json
│   └── vite.config.js
└── README.md                       # 项目启动说明
```

---



## 7.5 系统冷启动与初始化流程

### 7.5.1 首次部署后初始化步骤

系统冷启动时数据库为空，需按以下顺序初始化：

1. 系统管理员创建管理员账号
2. 管理员登录，下载「员工批量导入模板」
3. HR 填写模板（工号、姓名、部门、岗位、直属上级工号）
4. 上传模板，系统预览校验，修正错误，确认导入
5. 核对导入结果，补充缺失的考核关系
6. 配置岗位 KPI 模板
7. 配置考核周期（维度权重、等级规则、审批链）
8. 发起首次考核



### 7.5.2 Excel 导入模板规范

**模板字段**：

| 字段名 | 必填 | 格式说明 | 示例 |
|--------|------|---------|------|
| 工号 | ✅ | 唯一，50字符以内 | EMP001 |
| 姓名 | ✅ | 100字符以内 | 张三 |
| 部门名称 | ✅ | 若部门不存在则自动创建 | 技术部 |
| 岗位名称 | ✅ | 若岗位不存在则自动创建 | Java开发工程师 |
| 直属上级工号 | ❌ | 必须在系统中已存在；可为空 | EMP002 |
| 是否部门负责人 | ❌ | 是/否；默认否 | 否 |
| 入职日期 | ❌ | YYYY-MM-DD | 2023-01-15 |
| 状态 | ❌ | 在职/离职；默认在职 | 在职 |

**模板下载**：系统提供  模板文件，包含：
- 第 1 行为表头（字段名）
- 第 2 行为示例数据（供 HR 参考格式）
- 第 3 行起为待填写区域
- 字段旁附批注说明（如「直属上级工号必须已在系统中存在」）

### 7.5.3 导入校验与错误报告

**前置校验（预览阶段）**：
- 工号重复检测（模板内 + 数据库内）
- 必填字段空值检测
- 部门/岗位名称长度限制
- 直属上级工号存在性校验（允许为空，不允许不存在）
- 日期格式校验

**导入执行**：
- 校验通过的数据批量插入 、、 表
- 部门/岗位自动创建时记录 
- 导入完成后生成「导入结果报告」：成功 X 条 / 失败 Y 条

**错误报告格式**：
返回 Excel 文件，在原模板基础上增加「错误原因」列，标红错误行，HR 可直接修正后重新上传。



### 7.5.4 日常运维流程

**新员工入职**：
- HR 在后台「员工管理」页面点击「新增员工」
- 填写表单（工号、姓名、部门、岗位、直属上级）
- 系统自动校验工号唯一性，保存后即时生效

**员工调岗/离职**：
- HR 在员工列表页搜索员工，点击「编辑」
- 修改部门/岗位/直属上级，或标记状态为「离职」
- 已离职员工自动从后续考核周期中排除（）

## 8. 部署方案

### 8.1 开发环境启动

**后端启动**:
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**前端启动**:
```bash
cd frontend
npm install
npm run dev
```

**数据库**: SQLite 零配置，首次启动自动创建。

### 8.2 生产环境部署
- 后端使用 `uvicorn` + `gunicorn`（Linux）或直接使用 `uvicorn`（Windows）。
- 数据库迁移：`alembic upgrade head`。
- 前端构建：`npm run build`，产物部署到静态文件服务器或让 FastAPI 挂载 `dist/` 目录。
- 系统配置：通过环境变量或 `config.py` 配置 JWT 密钥、数据库路径等。

---

## 9. 开发规范

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

---

> **文档结束**  
> 请评审本技术方案，确认或补充后进入 **测试用例编写阶段**。
