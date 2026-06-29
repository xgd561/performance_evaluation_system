# 后端接口测试规范与开发流程

## 一、测试归档结构

```
backend/tests/
├── __init__.py
├── conftest.py          # 全局 fixtures：数据库、客户端、认证令牌、用户角色
├── test_auth.py         # 对应 /auth/* 接口（21 个用例）
├── test_employees.py    # 对应 /employees/* 接口（37 个用例）
├── test_departments.py  # 对应 /departments/* + /positions/* 接口（27 个用例）
├── test_cycles.py       # 对应 /assessment-cycles/* 接口（23 个用例）
├── test_kpi_templates.py # 对应 /kpi-templates/* 接口（17 个用例）
├── test_config.py       # 对应 /config/* 接口（18 个用例）
└── test_dashboard.py    # 对应 /dashboard/* 接口（9 个用例）
```

**总计：151 个严格测试用例，100% 覆盖现有接口，全部通过。**

## 二、测试对应关系表

| 接口文件 | 测试文件 | 覆盖端点 |
|---------|---------|---------|
| `routers/auth.py` | `test_auth.py` | `/auth/login`, `/auth/refresh`, `/auth/me`, `/auth/password`, `/auth/change-password`, `/auth/logout` |
| `routers/employees.py` | `test_employees.py` | `/employees`, `/employees/{id}`, `/employees/import`, `/employees/import-preview`, `/employees/import-status`, `/employees/template` |
| `routers/departments.py` | `test_departments.py` | `/departments`, `/departments/{id}`, `/positions`, `/positions/{id}` |
| `routers/cycles.py` | `test_cycles.py` | `/assessment-cycles`, `/assessment-cycles/{id}`, `/assessment-cycles/launch`, `/assessment-cycles/add-employees`, `/assessment-cycles/{id}/employees/{eid}`, `/assessment-cycles/{id}/progress` |
| `routers/kpi_templates.py` | `test_kpi_templates.py` | `/kpi-templates`, `/kpi-templates/{id}`, `/kpi-templates/{id}/adjust`, `/kpi-templates/kpi-adjustments/pending`, `/kpi-templates/kpi-adjustments/{id}/approve` |
| `routers/config.py` | `test_config.py` | `/config/grade-rules`, `/config/dimension-weights`, `/config/reviewer-weights`, `/config/small-dept-exemption` |
| `routers/dashboard.py` | `test_dashboard.py` | `/dashboard`, `/dashboard/cycles`, `/dashboard/approvals`, `/dashboard/scores` |

## 三、严格断言规范（强制）

每个接口的测试必须覆盖以下维度，且**断言必须具体到字段值**，不能仅检查状态码或键存在：

### 1. 正常路径（Happy Path）
- 请求合法参数，验证返回码 200/201/204
- **验证返回数据结构完整，每个关键字段的值正确**
- **List 接口**：验证 `items` 中每个 item 包含所有预期字段，且字段值正确
- **Get/Create/Update 接口**：验证返回对象包含所有字段（id, name, 关联字段, enriched 字段, created_at 等）
- **禁止仅检查 `status_code == 200` 或 `"key" in data`**

### 2. 输入校验（Validation）
- 必填字段缺失 → 422
- 格式错误（如日期、数字、邮箱） → 422
- 业务规则违反（如权重和不等于100） → 422
- **验证错误消息内容必须包含预期关键字**

### 3. 认证校验（Authentication）
- 未携带 Token → 401
- Token 无效/过期 → 401
- Token 格式错误 → 401
- **验证错误消息内容**

### 4. 权限校验（Authorization）
- 角色不足（如 employee 访问 admin 接口） → 403
- 多角色接口验证各角色可访问性
- **验证返回数据结构和字段完整性**

### 5. 资源状态（Resource State）
- 资源不存在 → 404
- 资源已存在（重复创建） → 409
- 资源被关联（如部门下有员工不可删除） → 409
- 资源状态不可操作（如已发起周期不可编辑） → 409
- **验证错误消息内容必须包含预期关键字**

### 6. 特殊逻辑
- 分页查询：验证 `total`, `page`, `size`, `items` 结构及字段完整性
- 关键词搜索：验证返回结果全部匹配搜索条件，且包含 enriched 字段
- 排序：验证返回顺序正确
- 软删除/级联限制：验证关联数据阻止删除
- 文件上传/下载：验证 Content-Type 和文件名
- 限流（如登录失败锁定）：验证锁定消息和 429 状态码
- 配置更新：验证持久化（更新后 GET 应返回新值）

## 四、反模式清单（严禁）

以下写法在测试中被视为严重错误，禁止出现：

| 反模式 | 示例 | 风险 |
|-------|------|------|
| 仅检查状态码 | `assert resp.status_code == 200` | 后端返回空对象也能通过 |
| 仅检查键存在 | `assert "name" in data` | 值为 null 也能通过 |
| 状态码或关系 | `assert resp.status_code in [422, 200]` | 后端完全不做校验也能通过 |
| 宽松类型检查 | `assert isinstance(data, list)` | 空列表也能通过 |
| 缺少持久化检查 | PUT 后不 GET 验证 | 更新可能未实际保存 |

## 五、运行方式

### 运行全部测试
```bash
cd backend
python -m pytest tests/ -v --tb=short
```

### 运行指定模块
```bash
python -m pytest tests/test_auth.py -v
python -m pytest tests/test_employees.py -v
```

### 使用 Windows 批处理
```bash
run_tests.bat          # 全部
run_tests.bat auth     # 仅认证
run_tests.bat employees
```

## 六、测试基础设施（conftest.py）

- **数据库**：`sqlite:///:memory:` + `StaticPool`，确保多连接共享同一内存数据库，每个测试函数独立隔离
- **用户角色**：预置 `admin`, `hr`, `manager`, `employee` 四级用户及其关联 Employee
- **Token 生成**：`admin_token`, `hr_token`, `manager_token`, `employee_token` 自动登录并获取 Bearer Token
- **依赖注入**：覆盖 `get_db` 依赖，确保所有 HTTP 请求路由到测试数据库

## 七、后续开发规范（强制）

> ⚠️ **以下规范必须严格执行，任何新接口或接口变更前必须先跑通测试。**

### 1. 新接口开发流程

```
① 编写测试用例（test_xxx.py）
      ↓
② 运行测试确认失败（RED）
      ↓
③ 实现接口代码
      ↓
④ 运行测试确认通过（GREEN）
      ↓
⑤ 代码审查与重构（REFACTOR）
      ↓
⑥ 提交并归档
```

### 2. 接口变更流程

```
① 修改接口代码前，先完整运行现有测试
      ↓
② 若测试失败，分析影响范围
      ↓
③ 同步修改/补充测试脚本
      ↓
④ 再次运行全部测试，确认 151+ 用例全部通过
      ↓
⑤ 提交代码
```

### 3. 测试用例编写规范

- 每个测试类名必须对应接口文件中的一个类或一组端点
- 测试方法名格式：`test_<操作>_<场景>_<期望结果>`，例如 `test_create_employee_duplicate_employee_no`
- **断言必须验证：HTTP 状态码、错误消息关键字、返回数据结构及字段值**
- **禁止仅检查状态码或键存在**
- 禁止跳过失败测试（no `pytest.skip`），除非有明确 TODO 注释并记录 Issue

### 4. 提交检查清单

- [ ] 新接口是否有对应测试文件/用例？
- [ ] 所有现有测试是否全部通过？
- [ ] 测试是否覆盖 401/403/404/409/422 等异常分支？
- [ ] 正常路径测试是否验证了所有返回字段的值？
- [ ] 配置更新类测试是否做了持久化回检查验？
- [ ] conftest.py 中的 fixtures 是否需要补充？
- [ ] 测试文档（本文件）是否需要更新？

## 八、当前测试统计

| 模块 | 用例数 | 状态 |
|------|--------|------|
| test_auth.py | 21 | ✅ 通过 |
| test_employees.py | 37 | ✅ 通过 |
| test_departments.py | 27 | ✅ 通过 |
| test_cycles.py | 23 | ✅ 通过 |
| test_kpi_templates.py | 17 | ✅ 通过 |
| test_config.py | 18 | ✅ 通过 |
| test_dashboard.py | 9 | ✅ 通过 |
| **合计** | **151** | **✅ 全部通过** |

## 九、本次加固修复记录

### 后端修复
- `config.py` — 新增负数权重校验（返回 422 + 错误消息）
- `cycles.py` — `create_cycle` 返回体补充 `created_at` 字段

### 测试加固
- `test_auth.py` — login/refresh/me 增加 token 结构、用户字典字段、错误消息严格校验
- `test_employees.py` — list/get/create/update 增加 `department_name`, `position_name`, `manager_name`, `manager_employee_no`, `created_at` 等 enriched 字段严格校验
- `test_departments.py` — list/create/update 增加 `position_count`, `employee_count`, `parent_name`, `created_at` 严格校验
- `test_cycles.py` — create 增加 `created_at`/`weights`/`grade_rules` 校验；launch/add-employees 增加返回结构校验
- `test_kpi_templates.py` — list/create/update 增加 item 字段值校验；adjustment 增加 `id`/`record_id`/`reason` 校验
- `test_dashboard.py` — stats/recent_cycles/pending_tasks/approvals/scores 增加嵌套结构和字段类型校验
- `test_config.py` — grade-rules 增加 `min`/`max` 结构校验；dimension-weights 增加求和校验；small-dept 增加类型校验；消除 `in [422, 200]` 反模式

---
**最后更新**：2026-06-29
**维护人**：开发团队
