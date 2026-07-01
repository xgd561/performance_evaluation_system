# 端到端（E2E）测试用例设计 —— 按角色梳理

> 来源：PRD_绩效考核评分系统_v1.0.md 角色使用场景
> 框架：Playwright + Chromium
> 环境前提：后端 `http://localhost:8014` + 前端 `http://localhost:3000`

---

## 一、角色与测试账号

| 角色 | 账号 | 密码 | 核心场景 |
|------|------|------|---------|
| admin | admin | admin123 | 系统配置、员工管理、全公司汇总 |
| hr | hr001 | Hr001@123 | 考核周期、强制分布、申诉处理、报表导出 |
| manager | mgr001 | Mgr001@123 | 下属评分、审批、绩效面谈、KPI调整审批 |
| employee | emp001 | Emp001@123 | 自评、查看绩效、发起申诉 |
| peer | peer001 | Peer001@123 | 协作评分 |
| executive | exec001 | Exec001@123 | 查看公司/部门绩效分布（只读） |

---

## 二、通用前置条件

1. 后端服务已启动（`uvicorn app.main:app --port 8014`）。
2. 数据库中已存在基础种子数据（员工、部门、岗位、考核周期）。
3. 前端 Dev Server 由 Playwright `webServer` 自动启动。

---

## 三、Admin（系统管理员）场景

### 场景 1：登录后查看仪表盘全局统计
- **步骤**：打开登录页 → 输入 admin/admin123 → 点击登录 → 跳转仪表盘
- **断言**：
  - URL 包含 `/dashboard`
  - 页面标题 "仪表盘" 可见
  - 统计卡片 "员工总数"、"部门数量"、"考核周期"、"进行中" 可见
  - 快捷操作入口不存在（admin 不属于 manager/peer/employee）

### 场景 2：进入员工管理页面
- **步骤**：登录 → 点击导航菜单 "员工管理" → 进入员工列表页
- **断言**：
  - URL 包含 `/employees`
  - 页面标题/表格区域可见

---

## 四、HR（绩效专员）场景

### 场景 1：登录后查看仪表盘全局统计
- **步骤**：登录 → 跳转仪表盘
- **断言**：
  - 统计卡片 "员工总数"、"部门数量" 等可见

### 场景 2：进入考核周期管理
- **步骤**：登录 → 点击导航菜单 "考核周期" → 进入周期列表页
- **断言**：
  - URL 包含 `/cycles`
  - 页面标题/表格区域可见

### 场景 3：进入强制分布处理页
- **步骤**：登录 → 点击导航菜单 "强制分布处理" → 进入处理页
- **断言**：
  - URL 包含 `/distribution-review`
  - 页面标题 "强制分布处理" 可见
  - 查询表单（周期选择器）可见

---

## 五、Manager（直属上级/部门负责人）场景

### 场景 1：登录后查看经理专属仪表盘
- **步骤**：登录 → 跳转仪表盘
- **断言**：
  - 统计卡片 "下属人数"、"待评分"、"待审批"、"待面谈" 可见
  - 快捷操作入口包含 "批量评分"、"审批下属绩效"、"记录面谈"

### 场景 2：进入评分表
- **步骤**：登录 → 点击 "评分表" 导航或快捷操作 → 进入评分页
- **断言**：
  - URL 包含 `/score-sheet`
  - 页面包含评分区域（维度列表、分数输入、提交按钮）

### 场景 3：进入审批工作台
- **步骤**：登录 → 点击 "审批工作台" 导航 → 进入审批页
- **断言**：
  - URL 包含 `/approval-workbench`
  - 页面标题 "审批工作台" 可见
  - 审批操作按钮（通过/驳回/打回）或空状态提示可见

---

## 六、Employee（普通员工）场景

### 场景 1：登录后查看员工专属仪表盘
- **步骤**：登录 → 跳转仪表盘
- **断言**：
  - 统计卡片 "考核记录"、"待自评"、"当前考核"、"当前状态" 可见
  - 快捷操作入口包含 "进入自评"、"查看历史绩效"、"发起申诉"

### 场景 2：进入自评页面
- **步骤**：登录 → 点击 "自评" 导航或快捷操作 → 进入自评页
- **断言**：
  - URL 包含 `/self-assessment`
  - 页面标题 "自评" 可见
  - 提交按钮 "提交自评" 可见

### 场景 3：进入我的绩效页面
- **步骤**：登录 → 点击 "我的绩效" 导航 → 进入绩效页
- **断言**：
  - URL 包含 `/my-performance`
  - 页面标题 "我的绩效" 可见
  - 状态卡片或历史记录表格可见

---

## 七、Peer（跨部门协作人）场景

### 场景 1：登录后查看协作人专属仪表盘
- **步骤**：登录 → 跳转仪表盘
- **断言**：
  - 统计卡片 "待协作评分"、"已完成评分"、"总协作评分" 可见
  - 快捷操作入口包含 "进入协作评分"

### 场景 2：进入协作评分待办列表
- **步骤**：登录 → 点击 "协作评分" 导航 → 进入待办页
- **断言**：
  - URL 包含 `/peer-review`
  - 页面标题 "协作评分待办" 可见
  - 评分卡片列表或空状态提示可见

---

## 八、Executive（高层管理者）场景

### 场景 1：登录后查看仪表盘
- **步骤**：登录 → 跳转仪表盘
- **断言**：
  - URL 包含 `/dashboard`
  - 页面标题 "仪表盘" 可见
  - 通用统计卡片 "员工总数"、"部门数量" 等可见（executive 无专属统计，显示 admin/hr 通用视图）

---

## 九、选择器策略规范

| 元素类型 | 推荐选择器 | 示例 |
|---------|----------|------|
| 页面标题 | `getByRole('heading', { name: '...' })` | `getByRole('heading', { name: '仪表盘' })` |
| 输入框 | `getByPlaceholder('...')` | `getByPlaceholder('用户名')` |
| 按钮 | `getByRole('button', { name: '...' })` | `getByRole('button', { name: '登录' })` |
| 统计标签 | `locator('.stat-label').filter({ hasText: '...' })` | `locator('.stat-label').filter({ hasText: '员工总数' })` |
| 导航菜单 | `getByRole('menuitem', { name: '...' })` | `getByRole('menuitem', { name: '员工管理' })` |
| 表格 | `locator('table')` 或 `getByRole('table')` | `locator('table').first()` |
| 空状态 | `getByText('暂无数据')` 或 `getByText('No Data')` | 根据实际空状态文本 |

⚠️ **禁忌**：避免直接使用 `page.getByText('考核周期')` 等宽泛文本，因为 Element Plus 导航菜单可能包含相同文本，导致 `strict mode violation`。

---

## 十、测试运行命令

```bash
cd frontend

# 运行所有角色场景测试
npm run test:e2e

# 运行单个角色场景
npx playwright test tests/e2e/admin-scenarios.spec.ts --project=chromium
npx playwright test tests/e2e/hr-scenarios.spec.ts --project=chromium
npx playwright test tests/e2e/manager-scenarios.spec.ts --project=chromium
npx playwright test tests/e2e/employee-scenarios.spec.ts --project=chromium
npx playwright test tests/e2e/peer-scenarios.spec.ts --project=chromium
npx playwright test tests/e2e/executive-scenarios.spec.ts --project=chromium

# 有头模式观察
npx playwright test --project=chromium --headed

# UI 调试模式
npm run test:e2e:ui
```
