# 绩效考核评分系统 — 开发优先级 Todo List

> **文档版本**: v1.0  
> **生成日期**: 2026-07-04  
> **状态**: 待评审  
> **依据**: PRD v1.0 + TECH v1.0  
> **约束**: 每个任务预估 Token ≤ 100k，确保单轮对话可完成开发与测试

---

## 文档说明

本清单将 PRD 中的 25 个 Story 和 TECH 中的 4 层架构进一步拆解为 **可独立执行的最小开发任务**。每个任务包含：任务编号、名称、所属 Story、对应用户场景、技术范围、预估 Token 消耗、验收标准、前置依赖。

**Token 消耗估算原则**（基于代码生成经验）：

| 任务类型 | 预估 Token | 说明 |
|---------|-----------|------|
| 单数据库模型定义 | ~5-10k | 纯 SQLAlchemy Model，无业务逻辑 |
| 单 Pydantic Schema | ~5-10k | 请求/响应模型定义 |
| 单 API Endpoint（CRUD 之一） | ~15-25k | Router + Service + Repository 一层 |
| 单工具函数/算法 | ~10-20k | 纯逻辑函数，无 HTTP 上下文 |
| 单 Vue 组件（简单） | ~20-30k | 表单/列表/详情页 |
| 单 Vue 组件（复杂） | ~40-60k | 含图表、多 Tab、复杂交互 |
| 前端基础设施模块 | ~40-60k | 路由/状态管理/API 封装等 |
| 端到端测试（单 Story） | ~20-30k | pytest 用例 5-10 个 |

---

## 开发阶段总览

| 阶段 | 名称 | 任务数 | 覆盖范围 | 业务目标 |
|------|------|--------|---------|---------|
| **P0** | 基础设施与架构 | 22 | 数据库、认证、状态机框架、API 基础、前端基础 | 搭建可运行的技术骨架 |
| **P1** | 系统配置模块 | 18 | Story-01 ~ Story-05 | 管理员可配置全局规则 |
| **P2** | 员工与组织模块 | 16 | Story-06 ~ Story-07 | 员工导入、组织架构建立 |
| **P3** | 考核管理模块 | 14 | Story-08 ~ Story-09 | HR 可创建并启动考核周期 |
| **P4** | 评分管理模块 | 22 | Story-10 ~ Story-15 | 自评 → 上级评 → 协作评 |
| **P5** | 汇总与审批模块 | 18 | Story-16 ~ Story-20 | 加权计算、强制分布、审批、面谈 |
| **P6** | 发布与归档模块 | 16 | Story-21 ~ Story-25 | 结果发布、申诉、高管仪表盘、归档导出 |
| **P7** | 集成测试与验收 | 10 | 全流程 E2E、性能测试、安全测试 | 确保系统可交付 |
| **合计** | — | **136** | 25 Story + 8 场景 | — |

---

## P0 基础设施与架构（22 个任务）

> **目标**: 搭建可运行的技术骨架，确保后续所有 Story 有统一的开发基础。  
> **前置条件**: 无（项目冷启动）。

### P0-01 项目目录初始化
| 项目 | 内容 |
|------|------|
| **任务名称** | 创建标准项目目录结构 |
| **技术范围** | 目录创建 |
| **所属 Story** | — |
| **用户场景** | — |
| **任务描述** | 按 TECH 文档 7.1 节创建目录：`backend/app/{api,core,db,models,schemas,crud,services,utils}`、`backend/.venv/`（Python 虚拟环境）、`frontend/src/{views,components,api,stores,router,composables,types,assets}`、`scripts/`、`tests/`、`data/db/`、`logs/`、`uploads/` |
| **预估 Token** | ~5k |
| **验收标准** | 所有目录存在，backend 和 frontend 下分别存在 `__init__.py` / `package.json` 使用 bash 脚本执行验证（`bash scripts/xxx.sh` 或 `cmd scripts/xxx.bat`），严格断言文件生成、命令退出码和输出内容。 |
| **前置依赖** | 无 |

### P0-02 后端虚拟环境与依赖配置
| 项目 | 内容 |
|------|------|
| **任务名称** | 创建 backend/requirements.txt 并安装依赖 |
| **技术范围** | 配置文件 |
| **所属 Story** | — |
| **用户场景** | — |
| **任务描述** | ① 创建虚拟环境：`cd backend && python -m venv .venv`；② 定义 `backend/requirements.txt`：fastapi、uvicorn、sqlalchemy、alembic、pydantic、pyjwt、bcrypt、python-multipart、openpyxl、playwright、pytest、httpx、apscheduler；③ 激活虚拟环境并安装依赖：`.venv\Scripts\activate && pip install -r requirements.txt` |
| **预估 Token** | ~5k |
| **验收标准** | `pip install -r requirements.txt` 成功，无版本冲突 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-01 |

### P0-03 前端依赖与 Vite 配置
| 项目 | 内容 |
|------|------|
| **任务名称** | 初始化 Vue 3 + Vite + Element Plus 项目 |
| **技术范围** | 配置文件 |
| **所属 Story** | — |
| **用户场景** | — |
| **任务描述** | 配置 package.json（vue@^3.4, vite@^5, element-plus@^2.7, vue-router@^4.3, pinia@^2.1, echarts@^5.5, axios），配置 vite.config.ts（别名、代理到 localhost:8000）、tsconfig.json |
| **预估 Token** | ~10k |
| **验收标准** | `npm install && npm run dev` 成功启动，浏览器可访问 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-01 |

### P0-04 数据库连接与引擎配置
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 database.py（SQLAlchemy 引擎 + Session） |
| **技术范围** | 后端基础设施 |
| **所属 Story** | — |
| **用户场景** | — |
| **任务描述** | 按 TECH 文档实现 `backend/app/database.py`：创建 engine、SessionLocal、get_db() 依赖、init_db()，数据库路径指向 `data/db/performance_evaluation.db` |
| **预估 Token** | ~10k |
| **验收标准** | `python -c "from app.database import engine; print(engine.url)"` 输出正确路径；`init_db()` 可创建空数据库文件 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-02 |

### P0-05 核心实体模型（一）— 用户与员工
| 项目 | 内容 |
|------|------|
| **任务名称** | 创建 Employee、User、Department、Position 模型 |
| **技术范围** | 后端数据库模型 |
| **所属 Story** | Story-06、Story-07 |
| **用户场景** | 场景 1.5 |
| **任务描述** | 按 PRD 8.6/8.7/8.8 节实现 SQLAlchemy 模型，包含完整字段、类型、约束、索引、外键关系。注意 Employee 的 manager_id 自关联 |
| **预估 Token** | ~15k |
| **验收标准** | 模型可 import，`Base.metadata.create_all(engine)` 不报错；`Department` 和 `Position` 有 `parent_id` / `department_id` 外键 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-04 |

### P0-06 核心实体模型（二）— 考核与评分
| 项目 | 内容 |
|------|------|
| **任务名称** | 创建 AssessmentCycle、AssessmentRecord、KpiTemplate 模型 |
| **技术范围** | 后端数据库模型 |
| **所属 Story** | Story-08、Story-09、Story-05 |
| **用户场景** | 场景 2 |
| **任务描述** | 按 PRD 8.3/8.4/8.5 节实现模型，包含 JSON 字段（scores、weights、rules）、状态枚举、外键关联。AssessmentRecord 包含 self_scores、manager_scores、peer_scores、peer_comments、interview_record 等 JSON 字段 |
| **预估 Token** | ~15k |
| **验收标准** | 模型可 import，字段类型与 PRD 一致；JSON 字段使用 SQLAlchemy JSON 类型 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-05 |

### P0-07 核心实体模型（三）— 审批与协作
| 项目 | 内容 |
|------|------|
| **任务名称** | 创建 ApprovalRecord、PeerReviewTask、SystemConfig、OperationLog 模型 |
| **技术范围** | 后端数据库模型 |
| **所属 Story** | Story-18、Story-15、Story-01、Story-25 |
| **用户场景** | 场景 4、5、1 |
| **任务描述** | 按 PRD 8.9/8.10/8.11/8.12 节实现模型。ApprovalRecord 记录 step_index、action；PeerReviewTask 记录 reviewer_id、status、ability_score |
| **预估 Token** | ~15k |
| **验收标准** | 所有模型可 import，`Base.metadata.create_all()` 成功创建全部 18 张表 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-06 |

### P0-08 数据库初始化脚本（init_db.py）完善
| 项目 | 内容 |
|------|------|
| **任务名称** | 完善 init_db.py 支持全表创建 + 默认配置 + 预置用户 |
| **技术范围** | 后端脚本 |
| **所属 Story** | — |
| **用户场景** | 冷启动 |
| **任务描述** | 基于已有 `scripts/init_db.py` 扩展：① 确保所有 18 张表创建；② 插入 5 项默认 SystemConfig（grade_rules、dimension_weights、reviewer_weights、small_dept_exemption、peer_review_enabled）；③ 预置 7 个演示账号（张系管/张燕子/李建国/王志强/刘芳/赵晓峰/陈志强） |
| **预估 Token** | ~15k |
| **验收标准** | `python scripts/init_db.py` 成功执行；数据库中可查 7 个用户 + 5 条配置 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-07 |

### P0-09 自定义异常类定义
| 项目 | 内容 |
|------|------|
| **任务名称** | 创建 app/core/exceptions.py |
| **技术范围** | 后端基础设施 |
| **所属 Story** | — |
| **用户场景** | — |
| **任务描述** | 定义 BizError、AuthError、NotFoundError、ValidationError，统一结构 `{code, message, data}`，支持 HTTP 状态码与业务码分离 |
| **预估 Token** | ~10k |
| **验收标准** | 异常可被 raise 和 catch，FastAPI 可注册全局 exception handler 返回统一 JSON 结构 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-02 |

### P0-10 统一响应封装
| 项目 | 内容 |
|------|------|
| **任务名称** | 创建 app/core/response.py（统一 API 响应格式） |
| **技术范围** | 后端基础设施 |
| **所属 Story** | — |
| **用户场景** | — |
| **任务描述** | 封装 `success_response(data, message)` 和 `error_response(code, message)`，所有 Router 返回此结构。定义 Pydantic BaseResponse 模型 |
| **预估 Token** | ~10k |
| **验收标准** | 任意 API 返回 `{"code": 0, "message": "ok", "data": ...}` 结构 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-09 |

### P0-11 JWT 认证与密码工具
| 项目 | 内容 |
|------|------|
| **任务名称** | 创建 app/core/security.py |
| **技术范围** | 后端基础设施 |
| **所属 Story** | — |
| **用户场景** | 全部场景（登录） |
| **任务描述** | 实现 `create_access_token(user_id, role)`（JWT，2小时过期）、`verify_password(plain, hashed)`（bcrypt）、`get_password_hash(plain)`、依赖项 `get_current_user(token)` |
| **预估 Token** | ~15k |
| **验收标准** | `create_access_token` 生成可解码的 JWT；`verify_password` 可正确校验密码；`get_current_user` 可从 Header 提取并验证 Token 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-02 |

### P0-12 角色权限守卫（RBAC Dependency）
| 项目 | 内容 |
|------|------|
| **任务名称** | 创建 app/core/dependencies.py（RequireRole） |
| **技术范围** | 后端基础设施 |
| **所属 Story** | — |
| **用户场景** | 全部场景（权限控制） |
| **任务描述** | 实现 `require_role(*roles)` FastAPI Dependency，校验当前用户角色是否在允许列表中，未授权返回 403。实现 `get_current_user_or_403` 通用依赖 |
| **预估 Token** | ~15k |
| **验收标准** | 在 Router 中应用 `@router.get("/xxx", dependencies=[require_role("admin", "hr")])` 可正确拦截无权限用户 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-11 |

### P0-13 操作日志中间件
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现操作日志自动记录中间件 |
| **技术范围** | 后端基础设施 |
| **所属 Story** | — |
| **用户场景** | 全部场景（审计） |
| **任务描述** | 创建 `app/utils/audit_logger.py`，封装 `log_operation()`；在 FastAPI 中注册 middleware，拦截所有 POST/PUT/DELETE 请求，自动记录 operator_id、action、target_type、target_id、old_value、new_value 到 operation_logs 表 |
| **预估 Token** | ~20k |
| **验收标准** | 任意写操作后，operation_logs 表新增一条记录； old_value / new_value 正确序列化为 JSON 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-07、P0-12 |

### P0-14 状态机框架（State Machine Base）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 workflow_state_machine.py 基类 |
| **技术范围** | 后端核心算法 |
| **所属 Story** | Story-08 ~ Story-25 |
| **用户场景** | 全部场景（状态流转） |
| **任务描述** | 按 TECH 5.14 实现状态机基类：定义所有状态常量（not_started → archived）、允许的状态转换规则字典、transition(current, action, **kwargs) 方法、状态变更时写入 operation_logs |
| **预估 Token** | ~20k |
| **验收标准** | `transition("pending_self", "submit_self")` 返回 `"pending_manager"`；非法转换抛出 BizError；转换成功写入操作日志 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-09、P0-13 |

### P0-15 前端 API 请求封装
| 项目 | 内容 |
|------|------|
| **任务名称** | 创建 frontend/src/api/request.js |
| **技术范围** | 前端基础设施 |
| **所属 Story** | — |
| **用户场景** | — |
| **任务描述** | 基于 axios 封装：统一 baseURL（/api/v1）、请求拦截器（注入 JWT Token）、响应拦截器（统一错误处理、token 过期跳转登录）、请求/响应日志 |
| **预估 Token** | ~15k |
| **验收标准** | 任意前端页面可调用 `api.get('/users/me')` 并自动携带 Token；401 时自动跳转登录页 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P0-03 |

### P0-16 Pinia 状态管理基础
| 项目 | 内容 |
|------|------|
| **任务名称** | 创建 Pinia Store（auth.js + app.js） |
| **技术范围** | 前端基础设施 |
| **所属 Story** | — |
| **用户场景** | — |
| **任务描述** | `auth.js`：存储 token、userInfo、role、isAuthenticated；提供 login/logout/getUserInfo actions；`app.js`：存储 sidebarCollapsed、notificationCount、theme 等全局 UI 状态 |
| **预估 Token** | ~20k |
| **验收标准** | 登录后 Pinia 中可读取 userInfo；刷新页面后通过 localStorage 恢复 token 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P0-15 |

### P0-17 前端路由与导航守卫
| 项目 | 内容 |
|------|------|
| **任务名称** | 配置 Vue Router + 路由守卫 + 角色过滤 |
| **技术范围** | 前端基础设施 |
| **所属 Story** | — |
| **用户场景** | 全部场景（页面导航） |
| **任务描述** | 创建 `frontend/src/router/index.js`：定义路由表（/login、/dashboard、/config 等），按角色配置 `meta: { roles: ['admin'] }`，导航守卫校验 token 和角色权限，无权限重定向到 403 页面 |
| **预估 Token** | ~20k |
| **验收标准** | 未登录访问任意页面自动跳转 /login；admin 角色访问 /config 正常；employee 访问 /config 被拦截到 403 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P0-16 |

### P0-18 前端布局组件（Layout）
| 项目 | 内容 |
|------|------|
| **任务名称** | 创建 MainLayout.vue（侧边栏 + 顶部栏 + 内容区） |
| **技术范围** | 前端组件 |
| **所属 Story** | — |
| **用户场景** | — |
| **任务描述** | 使用 Element Plus 实现经典后台布局：左侧菜单栏（根据角色动态渲染）、顶部面包屑 + 用户信息 + 退出按钮、内容区 router-view。菜单项对应各角色可访问的页面 |
| **预估 Token** | ~30k |
| **验收标准** | admin 登录后侧边栏显示「系统配置、员工管理、考核周期」等；employee 登录后仅显示「我的绩效」等；点击菜单正确跳转 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P0-17 |

### P0-19 登录页面（LoginView.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现登录页面（含首次登录强制修改密码） |
| **技术范围** | 前端页面 + 后端 API |
| **所属 Story** | — |
| **用户场景** | 全部场景（登录入口） |
| **任务描述** | 前端：登录表单（username、password）、首次登录弹窗（修改密码、强度校验）；后端：`POST /api/v1/auth/login`（校验密码、返回 token + userInfo + is_first_login）、`POST /api/v1/auth/change-password` |
| **预估 Token** | ~30k |
| **验收标准** | 使用预置账号登录成功，Token 存入 Pinia 和 localStorage；首次登录强制修改密码后方可进入系统 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-11、P0-16、P0-18 |

### P0-20 后端健康检查接口
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 GET /api/v1/health |
| **技术范围** | 后端 API |
| **所属 Story** | — |
| **用户场景** | — |
| **任务描述** | 返回系统状态：数据库连接状态、当前时间、版本号。用于部署后验证和监控 |
| **预估 Token** | ~10k |
| **验收标准** | `curl http://localhost:8000/api/v1/health` 返回 `{"code":0,"data":{"db":"ok","version":"1.0.0"}}` |
| **前置依赖** | P0-04 |

### P0-21 数据脱敏工具（data_masking.py）
| 项目 | 内容 |
|------|------|
| **任务名称** | 创建 app/utils/data_masking.py |
| **技术范围** | 后端工具 |
| **所属 Story** | Story-21、Story-24 |
| **用户场景** | 场景 3、6 |
| **任务描述** | 实现手机号脱敏（153****3992）、身份证号脱敏、分数脱敏（未发布状态不返回 total_score/grade）。封装为 Pydantic 响应模型用的 validator |
| **预估 Token** | ~10k |
| **验收标准** | `mask_phone("1535363992")` 返回 `"153****3992"`；未发布状态的考核记录 API 不返回 total_score 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-10 |

### P0-22 重启脚本与环境检查
| 项目 | 内容 |
|------|------|
| **任务名称** | 完善 scripts/restart.bat 和 scripts/backup.bat |
| **技术范围** | 运维脚本 |
| **所属 Story** | — |
| **用户场景** | — |
| **任务描述** | restart.bat：检查端口 8000 占用、终止旧 uvicorn 进程、启动新进程、输出 Swagger 地址；backup.bat：复制 data/db/performance_evaluation.db 到 backups/，按日期命名 |
| **预估 Token** | ~10k |
| **验收标准** | 双击 restart.bat 后端正常重启；执行 backup.bat 生成带时间戳的数据库备份文件 使用 bash 脚本执行验证（`bash scripts/xxx.sh` 或 `cmd scripts/xxx.bat`），严格断言文件生成、命令退出码和输出内容。 |
| **前置依赖** | P0-08 |

---

## P1 系统配置模块（18 个任务）

> **目标**: 实现管理员配置全局规则的能力。  
> **覆盖 Story**: Story-01（等级规则）、Story-02（维度权重）、Story-03（评价人权重）、Story-04（协作评分开关）、Story-05（KPI 模板）。  
> **用户场景**: 场景 1（张系管配置全局）。

### P1-01 等级规则配置 — 后端 Schema 与校验
| 项目 | 内容 |
|------|------|
| **任务名称** | 创建 GradeRules Pydantic Schema + 校验器 |
| **技术范围** | 后端 Schema |
| **所属 Story** | Story-01 |
| **用户场景** | 场景 1 |
| **任务描述** | 定义 `GradeRulesSchema`（A/B/C/D 各含 min/max/ratio_limit），实现 Pydantic validator：区间连续不重叠、ratio_limit 合计 ≤ 100% |
| **预估 Token** | ~10k |
| **验收标准** | 传入 `{"A": {"min": 90, "max": 100, "ratio_limit": 0.2}}` 校验通过；传入重叠区间校验失败并提示具体字段 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-10 |

### P1-02 等级规则配置 — 后端 API（CRUD）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 SystemConfig 的 grade_rules 读写接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-01 |
| **用户场景** | 场景 1 |
| **任务描述** | `GET /api/v1/config/grade-rules`（读取当前配置）、`PUT /api/v1/config/grade-rules`（更新配置，写入 SystemConfig 表），仅 admin 可访问。更新时记录 operation_logs |
| **预估 Token** | ~20k |
| **验收标准** | admin 可读写；hr/employee 访问返回 403；更新后数据库 config_value 正确 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P1-01、P0-12 |

### P1-03 等级规则配置 — 前端页面（ConfigView.vue 等级 Tab）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现「系统配置」页面中的「等级规则」Tab |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-01 |
| **用户场景** | 场景 1 |
| **任务描述** | Element Plus 表单：4 个等级卡片，每卡片含 min/max/ratio_limit 输入框；保存时调用 PUT 接口；前端预校验（区间连续、ratio 合计 ≤ 100%）；保存成功 toast 提示 |
| **预估 Token** | ~30k |
| **验收标准** | 页面可填写并保存等级规则；保存后刷新页面数据正确恢复；非法输入前端拦截 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P1-02、P0-18 |

### P1-04 维度权重配置 — 后端 Schema + API + 前端页面
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现维度权重配置（业绩/能力/ attitude）完整链路 |
| **技术范围** | 后端 + 前端 |
| **所属 Story** | Story-02 |
| **用户场景** | 场景 1 |
| **任务描述** | Schema：三项之和 = 100%；API：GET/PUT `/api/v1/config/dimension-weights`；前端：ConfigView.vue 新增「维度权重」Tab，三个滑块/输入框（performance、ability、attitude），实时显示合计百分比，不等于 100% 时禁用保存按钮 |
| **预估 Token** | ~40k |
| **验收标准** | 合计 100% 时保存成功；99.9% 时前端拦截；非 admin 访问返回 403 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P1-03 |

### P1-05 评价人权重配置 — 后端 Schema + API + 前端页面
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现评价人权重配置（自评/上级/协作）完整链路 |
| **技术范围** | 后端 + 前端 |
| **所属 Story** | Story-03 |
| **用户场景** | 场景 1 |
| **任务描述** | 每个维度内评分人权重合计 100%（如业绩：self 30% + manager 70%）。后端 Pydantic validator 校验三层结构；前端 ConfigView.vue 新增「评价人权重」Tab，按维度分组展示权重输入框 |
| **预估 Token** | ~40k |
| **验收标准** | 各维度内权重合计 100% 方可保存；JSON 结构正确存储到 SystemConfig.reviewer_weights 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P1-04 |

### P1-06 协作评分开关 — 后端 API + 前端页面
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现协作评分开关配置完整链路 |
| **技术范围** | 后端 + 前端 |
| **所属 Story** | Story-04 |
| **用户场景** | 场景 1 |
| **任务描述** | 后端：GET/PUT `/api/v1/config/peer-review-enabled`（Boolean 类型）；前端：ConfigView.vue 新增「协作评分开关」Tab，单个 Switch 组件，开启/关闭保存后提示 |
| **预估 Token** | ~30k |
| **验收标准** | Switch 切换后保存，数据库 `peer_review_enabled` 值同步变更；仅 admin 可操作 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P1-05 |

### P1-07 小部门豁免配置 — 后端 API + 前端页面
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现小部门豁免配置完整链路 |
| **技术范围** | 后端 + 前端 |
| **所属 Story** | Story-01（附属配置） |
| **用户场景** | 场景 1 |
| **任务描述** | 后端：GET/PUT `/api/v1/config/small-dept-exemption`（threshold 整数 1-50，enabled Boolean）；前端：ConfigView.vue 新增「小部门豁免」Tab，输入阈值 + Switch 开关 |
| **预估 Token** | ~30k |
| **验收标准** | 阈值输入校验为整数 1-50；保存后数据库正确；后续强制分布算法读取此配置 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P1-06 |

### P1-08 岗位 KPI 模板 — 后端模型补充与 Schema
| 项目 | 内容 |
|------|------|
| **任务名称** | 完善 KpiTemplate 的 indicators JSON Schema 校验 |
| **技术范围** | 后端 Schema |
| **所属 Story** | Story-05 |
| **用户场景** | 场景 1 |
| **任务描述** | 定义 `KpiIndicatorSchema`（name, weight, target_value, scoring_method, description），Pydantic validator：同一模板内 weight 合计 = 100%；name 唯一性校验 |
| **预估 Token** | ~15k |
| **验收标准** | 传入 indicators 权重合计 100% 通过；99% 或 101% 失败 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-06 |

### P1-09 岗位 KPI 模板 — 后端 API（CRUD + 复制）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 KPI 模板的后端 CRUD + 复制接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-05 |
| **用户场景** | 场景 1 |
| **任务描述** | `POST /api/v1/kpi-templates`（创建）、`GET /api/v1/kpi-templates`（列表）、`GET /api/v1/kpi-templates/{id}`（详情）、`PUT /api/v1/kpi-templates/{id}`（编辑）、`DELETE /api/v1/kpi-templates/{id}`（删除，引用保护）、`POST /api/v1/kpi-templates/{id}/copy`（复制，名称自动加「-副本」） |
| **预估 Token** | ~30k |
| **验收标准** | 创建模板后列表可查询；删除已关联快照的模板返回 400；复制后名称正确 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P1-08、P0-12 |

### P1-10 岗位 KPI 模板 — 前端列表页（KpiTemplateList.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 KPI 模板列表页 |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-05 |
| **用户场景** | 场景 1 |
| **任务描述** | Element Plus 表格：模板名称、关联岗位、指标数量、创建时间；操作列：编辑、删除、复制；顶部搜索框（按名称）；分页 |
| **预估 Token** | ~30k |
| **验收标准** | 表格正确渲染模板数据；删除时二次确认；复制后列表刷新出现新模板 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P1-09、P0-18 |

### P1-11 岗位 KPI 模板 — 前端编辑页（KpiTemplateEdit.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 KPI 模板编辑/创建页（含动态增删指标行） |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-05 |
| **用户场景** | 场景 1 |
| **任务描述** | 表单：模板名称、关联岗位选择器（下拉）、指标列表（动态增删行），每行含指标名称、权重、目标值、评分标准、计分方式；底部实时显示权重合计百分比；保存时前端校验权重 = 100% |
| **预估 Token** | ~40k |
| **验收标准** | 可添加 3 个指标并保存；权重合计 ≠ 100% 时保存按钮禁用；创建后跳转列表页 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P1-10 |

### P1-12 系统配置模块 — 单元测试
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写 SystemConfig、KpiTemplate 的 pytest 单元测试 |
| **技术范围** | 后端测试 |
| **所属 Story** | Story-01 ~ Story-05 |
| **用户场景** | — |
| **任务描述** | 测试：① 各配置项的 Pydantic validator（边界值、非法值）；② 配置 API 的权限控制（admin 可写、hr 不可写）；③ KPI 模板 CRUD（创建、复制、删除保护）；④ 权重合计 100% 校验 |
| **预估 Token** | ~30k |
| **验收标准** | `pytest tests/test_config.py` 全部通过（≥ 15 个用例） |
| **前置依赖** | P1-07、P1-09 |

### P1-13 系统配置页面整合（ConfigView.vue 完整版）
| 项目 | 内容 |
|------|------|
| **任务名称** | 整合 ConfigView.vue 全部 5 个 Tab |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-01 ~ Story-04 |
| **用户场景** | 场景 1 |
| **任务描述** | 将 P1-03 ~ P1-07 的 5 个 Tab 整合到同一页面，使用 Element Plus Tabs 组件。左侧显示「待配置项」红点提示（未配置时）。页面顶部显示「配置变更将仅影响新考核周期」提示 |
| **预估 Token** | ~20k |
| **验收标准** | 5 个 Tab 切换正常，数据加载正确；未配置项显示红点；admin 角色可见 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P1-03、P1-04、P1-05、P1-06、P1-07 |

### P1-14 配置读取 Service 封装
| 项目 | 内容 |
|------|------|
| **任务名称** | 封装 ConfigService（统一读取系统配置） |
| **技术范围** | 后端 Service |
| **所属 Story** | Story-01 ~ Story-05 |
| **用户场景** | 全部场景 |
| **任务描述** | 创建 `app/services/config_service.py`，封装 `get_grade_rules()`、`get_dimension_weights()`、`get_reviewer_weights()`、`get_peer_review_enabled()`、`get_small_dept_exemption()`，缓存到内存（减少数据库查询） |
| **预估 Token** | ~15k |
| **验收标准** | 各 Service 函数返回正确的 Python dict；多次调用仅查询数据库一次（缓存生效） 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P1-02、P1-04、P1-05、P1-06、P1-07 |

### P1-15 评分锚点数据常量
| 项目 | 内容 |
|------|------|
| **任务名称** | 定义评分锚点前端常量与后端枚举 |
| **技术范围** | 前后端常量 |
| **所属 Story** | Story-10、Story-13、Story-15 |
| **用户场景** | 场景 3、4、5 |
| **任务描述** | 前端 `frontend/src/constants/scoringAnchors.js`：90-100优秀、80-89良好、60-79合格、0-59待改进；后端 `app/core/constants.py`：SCORING_ANCHORS 字典 |
| **预估 Token** | ~5k |
| **验收标准** | 前后端常量一致，前端评分页面正确显示锚点说明 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-03 |

### P1-16 配置模块前端测试
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写 ConfigView 的 Vitest 组件测试 |
| **技术范围** | 前端测试 |
| **所属 Story** | Story-01 ~ Story-05 |
| **用户场景** | — |
| **任务描述** | 测试：① 页面加载时 5 个 Tab 正确渲染；② 保存按钮触发 API 调用；③ 权重合计 ≠ 100% 时保存按钮禁用；④ 非 admin 角色访问时显示 403 |
| **预估 Token** | ~20k |
| **验收标准** | `npm run test:unit` 通过（≥ 5 个用例） 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P1-13 |

### P1-17 配置模块集成测试
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写配置模块的 API 集成测试 |
| **技术范围** | 后端测试 |
| **所属 Story** | Story-01 ~ Story-05 |
| **用户场景** | — |
| **任务描述** | 使用 FastAPI TestClient 测试完整链路：登录获取 token → 修改等级规则 → 读取等级规则 → 验证数据一致性。测试 KPI 模板创建 → 复制 → 删除 → 引用保护 |
| **预估 Token** | ~20k |
| **验收标准** | `pytest tests/test_config_integration.py` 全部通过 |
| **前置依赖** | P1-12 |

### P1-18 系统配置模块端到端测试（场景 1）
| 项目 | 内容 |
|------|------|
| **任务名称** | 使用 Playwright 测试「管理员配置全局」场景 |
| **技术范围** | E2E 测试 |
| **所属 Story** | Story-01 ~ Story-05 |
| **用户场景** | 场景 1 |
| **任务描述** | 自动化测试：登录（张系管）→ 进入系统配置 → 填写等级规则 → 填写维度权重 → 填写评价人权重 → 开启协作评分 → 保存 → 验证各 Tab 数据持久化 |
| **预估 Token** | ~25k |
| **验收标准** | `npx playwright test tests/e2e/scenario1-admin-config.spec.ts` 通过 |
| **前置依赖** | P1-13、P1-16 |

---

## P2 员工与组织模块（16 个任务）

> **目标**: 实现员工信息导入、部门岗位管理、组织架构建立。  
> **覆盖 Story**: Story-06（员工导入）、Story-07（部门岗位管理）。  
> **用户场景**: 场景 1.5（张燕子导入员工）。

### P2-01 部门管理 — 后端 API（CRUD + 树形查询）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 Department 的 CRUD + 树形结构查询 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-07 |
| **用户场景** | 场景 1.5 |
| **任务描述** | `POST /api/v1/departments`（创建）、`GET /api/v1/departments`（列表，支持树形返回）、`PUT /api/v1/departments/{id}`、`DELETE /api/v1/departments/{id}`（删除保护：有子部门或员工时禁止删除）。树形查询使用递归 CTE |
| **预估 Token** | ~25k |
| **验收标准** | 创建研发部→创建产品部（parent_id=研发部）→ 树形查询返回正确层级；删除有员工的部门返回 400 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-05 |

### P2-02 部门管理 — 前端页面（DepartmentList.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现部门管理页面（树形表格） |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-07 |
| **用户场景** | 场景 1.5 |
| **任务描述** | Element Plus 树形表格：部门名称、上级部门、经理、人数、排序；操作：新增、编辑、删除（二次确认）；支持拖拽排序；顶部显示部门架构图（简化版） |
| **预估 Token** | ~35k |
| **验收标准** | 树形表格正确渲染层级关系；删除有子部门的部门时提示「该部门存在子部门，无法删除」 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P2-01、P0-18 |

### P2-03 岗位管理 — 后端 API（CRUD）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 Position 的 CRUD |
| **技术范围** | 后端 API |
| **所属 Story** | Story-07 |
| **用户场景** | 场景 1.5 |
| **任务描述** | `POST /api/v1/positions`（创建，含 department_id）、`GET /api/v1/positions`（按部门筛选）、`PUT /api/v1/positions/{id}`、`DELETE /api/v1/positions/{id}`（删除保护：有员工时禁止删除） |
| **预估 Token** | ~20k |
| **验收标准** | 创建「研发工程师」岗位（department_id=研发部）成功；删除有员工的岗位返回 400 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-05 |

### P2-04 岗位管理 — 前端页面（PositionList.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现岗位管理页面 |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-07 |
| **用户场景** | 场景 1.5 |
| **任务描述** | 表格：岗位名称、所属部门、描述、人数；操作：新增、编辑、删除；按部门筛选下拉框 |
| **预估 Token** | ~30k |
| **验收标准** | 表格正确渲染；按部门筛选正确过滤；删除有员工的岗位时提示 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P2-03、P0-18 |

### P2-05 员工管理 — 后端 API（单条 CRUD）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 Employee 的单条 CRUD + 汇报关系查询 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-06 |
| **用户场景** | 场景 1.5 |
| **任务描述** | `POST /api/v1/employees`（创建，含 manager_id）、`GET /api/v1/employees`（列表，支持按部门/岗位/姓名搜索、分页）、`GET /api/v1/employees/{id}`（含直属上级信息）、`PUT /api/v1/employees/{id}`、`DELETE /api/v1/employees/{id}`（软删除，is_active=false）。`GET /api/v1/employees/{id}/subordinates`（查询下属列表，含递归） |
| **预估 Token** | ~30k |
| **验收标准** | 创建李建国（manager_id=null）→ 创建王志强（manager_id=李建国）→ 查询李建国下属返回王志强；查询王志强下属返回空数组 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-05 |

### P2-06 员工管理 — 前端列表页（EmployeeList.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现员工列表页 |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-06 |
| **用户场景** | 场景 1.5 |
| **任务描述** | Element Plus 表格：姓名、工号、部门、岗位、直属上级、状态；顶部搜索（姓名/工号）、部门筛选、岗位筛选；分页；操作：新增、编辑、删除（软删除） |
| **预估 Token** | ~30k |
| **验收标准** | 表格渲染正确；搜索「王志强」正确过滤；分页正常；删除后状态变为「已停用」 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P2-05、P0-18 |

### P2-07 员工管理 — 前端编辑页（EmployeeEdit.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现员工编辑/创建页 |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-06 |
| **用户场景** | 场景 1.5 |
| **任务描述** | 表单：姓名、工号、部门（下拉）、岗位（级联下拉）、直属上级（下拉，可选）、邮箱、手机号、状态。工号唯一性校验（异步）、邮箱格式校验、手机号 11 位校验 |
| **预估 Token** | ~30k |
| **验收标准** | 创建员工时工号重复提示错误；选择部门后岗位下拉框仅显示该部门岗位；保存成功跳转列表 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P2-06 |

### P2-08 员工 Excel 导入 — 后端模板下载接口
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现员工导入模板下载 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-06 |
| **用户场景** | 场景 1.5 |
| **任务描述** | `GET /api/v1/employees/import-template` 生成标准 Excel 模板（表头：姓名、工号、部门、岗位、直属上级工号、邮箱、手机号），使用 openpyxl 生成 |
| **预估 Token** | ~15k |
| **验收标准** | 下载的 .xlsx 文件可在 Excel/WPS 正确打开，表头完整 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P2-05 |

### P2-09 员工 Excel 导入 — 后端导入接口
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现员工 Excel 批量导入 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-06 |
| **用户场景** | 场景 1.5 |
| **任务描述** | `POST /api/v1/employees/import`（multipart/form-data），解析 Excel，逐行校验：工号唯一性（模板内 + 数据库内）、直属上级工号存在性、部门与岗位匹配、邮箱格式、手机号 11 位；通过则插入，失败返回错误报告（含行号和具体错误） |
| **预估 Token** | ~30k |
| **验收标准** | 导入 28 人成功，失败 0 人；工号重复时返回错误行号；直属上级工号不存在时返回具体错误 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P2-08 |

### P2-10 员工 Excel 导入 — 前端页面（导入弹窗）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现员工导入弹窗组件 |
| **技术范围** | 前端组件 |
| **所属 Story** | Story-06 |
| **用户场景** | 场景 1.5 |
| **任务描述** | Element Plus 上传组件：「下载模板」按钮、「上传文件」拖拽区、导入进度条（如支持）、导入结果展示（成功 N 人，失败 M 人，错误列表可下载）。上传前校验文件类型（.xlsx） |
| **预估 Token** | ~30k |
| **验收标准** | 上传非 Excel 文件前端拦截；导入成功后列表页刷新；导入失败时显示错误行号和原因 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P2-09、P2-06 |

### P2-11 组织架构图展示（简化）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现组织架构图页面（OrganizationChart.vue） |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-07 |
| **用户场景** | 场景 1.5 |
| **任务描述** | 使用 Element Plus Tree 或第三方组件展示部门树，每个节点显示部门名称、经理、人数；点击部门展开下属部门和员工列表 |
| **预估 Token** | ~30k |
| **验收标准** | 树形结构正确展示；点击「研发部」展开显示下属员工（李建国、王志强等）；经理姓名正确显示 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P2-02、P2-05 |

### P2-12 员工与组织模块 — 单元测试
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写 Employee、Department、Position 的 pytest 单元测试 |
| **技术范围** | 后端测试 |
| **所属 Story** | Story-06、Story-07 |
| **用户场景** | — |
| **任务描述** | 测试：① 员工 CRUD（含软删除）；② 汇报关系递归查询；③ 部门删除保护；④ 岗位删除保护；⑤ Excel 导入校验（工号重复、上级不存在） |
| **预估 Token** | ~30k |
| **验收标准** | `pytest tests/test_employees.py` 全部通过（≥ 20 个用例） |
| **前置依赖** | P2-05、P2-01、P2-03 |

### P2-13 员工与组织模块 — 集成测试
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写员工与组织模块的 API 集成测试 |
| **技术范围** | 后端测试 |
| **所属 Story** | Story-06、Story-07 |
| **用户场景** | — |
| **任务描述** | 测试完整链路：创建部门 → 创建岗位 → 创建经理 → 创建员工（指定上级）→ 查询员工详情（含上级）→ 查询上级下属列表 → 导入员工 Excel → 查询导入结果 |
| **预估 Token** | ~20k |
| **验收标准** | `pytest tests/test_employees_integration.py` 全部通过 |
| **前置依赖** | P2-12 |

### P2-14 员工与组织模块 — 前端测试
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写 EmployeeList、DepartmentList 的 Vitest 组件测试 |
| **技术范围** | 前端测试 |
| **所属 Story** | Story-06、Story-07 |
| **用户场景** | — |
| **任务描述** | 测试：① 列表页加载渲染；② 搜索过滤；③ 删除确认弹窗；④ 导入弹窗上传文件 |
| **预估 Token** | ~20k |
| **验收标准** | `npm run test:unit` 通过（≥ 6 个用例） 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P2-06、P2-02 |

### P2-15 员工与组织模块 E2E（场景 1.5）
| 项目 | 内容 |
|------|------|
| **任务名称** | 使用 Playwright 测试「HR 导入员工」场景 |
| **技术范围** | E2E 测试 |
| **所属 Story** | Story-06、Story-07 |
| **用户场景** | 场景 1.5 |
| **任务描述** | 自动化测试：登录（张燕子）→ 进入员工管理 → 下载导入模板 → 准备测试 Excel → 上传导入 → 验证导入成功提示 → 核对员工列表（李建国、王志强等）→ 核对部门管理（研发部 15 人） |
| **预估 Token** | ~25k |
| **验收标准** | `npx playwright test tests/e2e/scenario1.5-hr-import.spec.ts` 通过 |
| **前置依赖** | P2-10、P2-14 |

### P2-16 预置用户数据脚本
| 项目 | 内容 |
|------|------|
| **任务名称** | 完善 init_db.py 中 7 个演示账号的创建逻辑 |
| **技术范围** | 后端脚本 |
| **所属 Story** | — |
| **用户场景** | 冷启动 |
| **任务描述** | 在 `scripts/init_db.py` 中补充：创建 7 个演示账号（张系管/张燕子/李建国/王志强/刘芳/赵晓峰/陈志强），建立正确的部门、岗位、汇报关系，密码使用 bcrypt 哈希 |
| **预估 Token** | ~15k |
| **验收标准** | 清空数据库后执行 `init_db.py`，7 个账号可正常登录，汇报关系正确（李建国是王志强的上级） 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P2-05 |

---

（后续阶段 P3~P7 因篇幅限制，将在文档续篇中继续展开。）

---

## P3 考核管理模块（14 个任务）

> **目标**: 实现 HR 创建考核周期、选择考核对象、配置截止时间、启动考核的能力。  
> **覆盖 Story**: Story-08（考核周期创建）、Story-09（考核周期启动）。  
> **用户场景**: 场景 2（张燕子发起考核）、场景 7/8（全流程）。

### P3-01 考核周期 — 后端 Schema 与校验
| 项目 | 内容 |
|------|------|
| **任务名称** | 创建 AssessmentCycle Pydantic Schema + 校验器 |
| **技术范围** | 后端 Schema |
| **所属 Story** | Story-08 |
| **用户场景** | 场景 2 |
| **任务描述** | 定义 `AssessmentCycleCreateSchema`（name, type, start_date, end_date, self_review_deadline, manager_review_deadline, peer_review_deadline, peer_review_enabled, department_ids）；实现 validator：名称唯一性、截止时间递增（self < manager < peer）、考核对象非空、时间必须大于当前时间 |
| **预估 Token** | ~15k |
| **验收标准** | 合法的周期数据校验通过；名称重复、截止时间逆序、空考核对象均校验失败并提示具体字段 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-06 |

### P3-02 考核周期 — 后端 API（CRUD）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 AssessmentCycle 的 CRUD 接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-08 |
| **用户场景** | 场景 2 |
| **任务描述** | `POST /api/v1/cycles`（创建）、`GET /api/v1/cycles`（列表，支持按状态/类型/时间筛选、分页）、`GET /api/v1/cycles/{id}`（详情，含考核对象部门列表）、`PUT /api/v1/cycles/{id}`（编辑，仅 not_started 可编辑）、`DELETE /api/v1/cycles/{id}`（仅 not_started 可删除） |
| **预估 Token** | ~30k |
| **验收标准** | 创建周期后列表可查询；已启动周期编辑返回 400；非 not_started 删除返回 400 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P3-01、P0-12 |

### P3-03 考核周期 — 前端列表页（CycleList.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现考核周期列表页 |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-08 |
| **用户场景** | 场景 2 |
| **任务描述** | Element Plus 表格：周期名称、类型、状态（Tag 颜色区分）、考核对象、各阶段截止时间、操作列（编辑、删除、启动、查看详情）；顶部筛选：状态下拉、类型下拉、时间范围；分页 |
| **预估 Token** | ~35k |
| **验收标准** | 表格渲染正确；not_started 行显示编辑/删除/启动按钮；published 行仅显示查看 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P3-02、P0-18 |

### P3-04 考核周期 — 前端创建/编辑页（CycleEdit.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现考核周期创建/编辑页 |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-08 |
| **用户场景** | 场景 2 |
| **任务描述** | 表单：周期名称、考核类型（季度/年度）、考核对象（部门多选树形选择器）、自评截止（日期时间选择器）、上级评分截止、协作评分截止（协作评分开关开启时显示，关闭时隐藏）；前端校验：名称必填、时间递增、至少选一个部门 |
| **预估 Token** | ~40k |
| **验收标准** | 创建「2026年Q1季度考核」成功；选择研发部和产品部；时间递增校验正确；关闭协作评分时协作评分截止隐藏 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P3-03 |

### P3-05 考核周期启动 — 后端启动接口
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 `POST /api/v1/cycles/{id}/start` 启动考核 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-09 |
| **用户场景** | 场景 2 |
| **任务描述** | 启动逻辑：① 校验前置条件（系统配置已生效、员工已导入、岗位已关联模板）；② 为每个被考核员工创建 AssessmentRecord（状态 not_started）；③ 根据岗位关联 KPI 模板生成 kpi_snapshots；④ 更新周期状态为 pending_self；⑤ 记录 operation_logs；⑥ 发送通知（站内消息）给被考核员工 |
| **预估 Token** | ~40k |
| **验收标准** | 启动后周期状态变为 pending_self；数据库 assessment_records 数量等于考核人数；kpi_snapshots 正确生成；未关联模板的岗位记录警告日志 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P3-02、P1-14、P2-05 |

### P3-06 考核周期启动 — 进度监控数据接口
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现仪表盘进度监控聚合接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-08 |
| **用户场景** | 场景 2 |
| **任务描述** | `GET /api/v1/cycles/{id}/progress`：返回自评完成率、上级评分完成率、协作评分完成率、各部门完成率、未完成人员名单。按 assessment_records 状态聚合计算 |
| **预估 Token** | ~20k |
| **验收标准** | 28 人参与考核，10 人已自评，返回自评完成率 35.7%；各部门完成率正确分组 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P3-05 |

### P3-07 仪表盘 — HR 首页（DashboardHR.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 HR 仪表盘首页 |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-08 |
| **用户场景** | 场景 2 |
| **任务描述** | 统计卡片：当前考核周期数、待汇总计算、待审批（Step 2）、待处理申诉、强制分布超标；下方表格：当前周期列表（含进度条）；点击卡片跳转对应页面 |
| **预估 Token** | ~40k |
| **验收标准** | 卡片数据正确；待汇总计算为 1 时显示红色高亮；点击跳转正确 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P3-06、P0-18 |

### P3-08 仪表盘 — 经理首页（DashboardManager.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现经理仪表盘首页 |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-12 |
| **用户场景** | 场景 4 |
| **任务描述** | 统计卡片：待评分人数、待审批（Step 1）、待面谈人数；下方表格：待评分员工列表（快速入口）；点击卡片跳转对应页面 |
| **预估 Token** | ~35k |
| **验收标准** | 李建国登录后显示待评分 3 人；点击跳转上级评分页 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P3-07 |

### P3-09 仪表盘 — 员工首页（DashboardEmployee.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现员工仪表盘首页 |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-10 |
| **用户场景** | 场景 3 |
| **任务描述** | 显示当前考核状态卡片（「待自评」或「待上级评分」等）；6 阶段流程图高亮当前阶段；快捷操作按钮（「去自评」或「查看结果」） |
| **预估 Token** | ~30k |
| **验收标准** | 王志强登录后显示「待自评」和绿色高亮的第 2 阶段；点击「去自评」跳转 SelfAssessment.vue 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P3-07 |

### P3-10 考核周期 — 状态机与启动校验
| 项目 | 内容 |
|------|------|
| **任务名称** | 完善状态机：not_started → pending_self 转换 |
| **技术范围** | 后端核心算法 |
| **所属 Story** | Story-09 |
| **用户场景** | 场景 2 |
| **任务描述** | 在 P0-14 状态机中注册 `start_cycle` 动作：校验当前状态为 not_started，校验前置条件，执行后状态变为 pending_self。定义非法启动的异常码和提示信息 |
| **预估 Token** | ~15k |
| **验收标准** | `transition("not_started", "start_cycle")` 返回 "pending_self"；已启动周期再次启动抛出 BizError 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-14 |

### P3-11 考核管理模块 — 单元测试
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写 AssessmentCycle、AssessmentRecord 的 pytest 单元测试 |
| **技术范围** | 后端测试 |
| **所属 Story** | Story-08、Story-09 |
| **用户场景** | — |
| **任务描述** | 测试：① 周期创建校验（名称重复、时间逆序）；② 启动考核前置校验（未配置、无员工）；③ 启动后生成正确数量的考核记录；④ KPI 快照生成；⑤ 进度监控计算 |
| **预估 Token** | ~30k |
| **验收标准** | `pytest tests/test_cycles.py` 全部通过（≥ 15 个用例） |
| **前置依赖** | P3-05 |

### P3-12 考核管理模块 — 集成测试
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写考核管理完整链路集成测试 |
| **技术范围** | 后端测试 |
| **所属 Story** | Story-08、Story-09 |
| **用户场景** | — |
| **任务描述** | 测试链路：创建周期 → 启动考核 → 验证考核记录生成 → 验证 KPI 快照 → 验证进度监控 → 验证员工收到通知 |
| **预估 Token** | ~20k |
| **验收标准** | `pytest tests/test_cycles_integration.py` 全部通过 |
| **前置依赖** | P3-11 |

### P3-13 考核管理模块 — 前端测试
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写 CycleList、CycleEdit 的 Vitest 组件测试 |
| **技术范围** | 前端测试 |
| **所属 Story** | Story-08 |
| **用户场景** | — |
| **任务描述** | 测试：① 列表加载渲染；② 筛选功能；③ 创建表单提交；④ 时间校验逻辑 |
| **预估 Token** | ~20k |
| **验收标准** | `npm run test:unit` 通过（≥ 5 个用例） 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P3-04 |

### P3-14 考核管理模块 E2E（场景 2）
| 项目 | 内容 |
|------|------|
| **任务名称** | 使用 Playwright 测试「HR 发起考核」场景 |
| **技术范围** | E2E 测试 |
| **所属 Story** | Story-08、Story-09 |
| **用户场景** | 场景 2 |
| **任务描述** | 自动化测试：登录（张燕子）→ 创建考核周期 → 选择研发部和产品部 → 设置截止时间 → 保存 → 启动考核 → 验证仪表盘显示待自评状态 → 验证员工（王志强）收到待自评通知 |
| **预估 Token** | ~25k |
| **验收标准** | `npx playwright test tests/e2e/scenario2-hr-create-cycle.spec.ts` 通过 |
| **前置依赖** | P3-13 |

---

## P4 评分管理模块（22 个任务）

> **目标**: 实现自评 → 上级评分 → 协作评分的完整链路。  
> **覆盖 Story**: Story-10（自评加载/草稿）、Story-11（自评提交）、Story-12（上级评分列表）、Story-13（上级评分表）、Story-14（上级评分提交/协作人分配）、Story-15（协作人评分）。  
> **用户场景**: 场景 3（王志强自评）、场景 4（李建国评分）、场景 5（赵晓峰协作评分）、场景 7/8（全流程）。

### P4-01 评分草稿 — 后端模型与 API
| 项目 | 内容 |
|------|------|
| **任务名称** | 创建 ScoreDraft 模型与读写接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-10、Story-13 |
| **用户场景** | 场景 3、4 |
| **任务描述** | 创建 `score_drafts` 表（id, record_id, draft_type, draft_data, created_at, updated_at）；`POST /api/v1/score-drafts`（保存草稿）、`GET /api/v1/score-drafts/{record_id}`（读取草稿）。draft_type: self/manager/peer |
| **预估 Token** | ~20k |
| **验收标准** | 保存草稿后数据库有记录；读取草稿返回正确 JSON；同一 record_id 同一 type 仅保留最新一条 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-06 |

### P4-02 自评 — 后端 API（加载评分表）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 `GET /api/v1/assessment-records/{id}/self` 自评数据加载接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-10 |
| **用户场景** | 场景 3 |
| **任务描述** | 返回：员工基本信息、KPI 明细（快照）、三维度评分锚点、评分草稿（如有）、历史自评（如有）。仅当前登录员工可访问自己的评分表，返回 403 |
| **预估 Token** | ~20k |
| **验收标准** | 王志强登录后请求返回自己的 KPI 快照和评分锚点；请求他人记录返回 403 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P4-01 |

### P4-03 自评 — 前端页面（SelfAssessment.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现自评页面 |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-10、Story-11 |
| **用户场景** | 场景 3 |
| **任务描述** | 页面布局：基本信息区（姓名、工号、岗位、周期）、KPI 明细区（只读，指标/权重/目标值/评分标准）、三维度评分区（每个维度含锚点提示、得分输入框 0-100、事实描述文本域 ≤200 字）、底部操作区（保存草稿、提交自评）。前端校验：得分必填、范围 0-100 |
| **预估 Token** | ~40k |
| **验收标准** | 页面加载正确显示 KPI 快照；输入 82/84/88 可保存草稿；提交后按钮变为「已提交，不可修改」 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P4-02、P0-18 |

### P4-04 自评提交 — 后端 API
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 `POST /api/v1/assessment-records/{id}/self-submit` 自评提交接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-11 |
| **用户场景** | 场景 3 |
| **任务描述** | 校验：当前状态为 pending_self、所有维度得分已填写且范围 0-100；写入 self_scores、self_facts、self_submitted=true；更新状态为 pending_manager；清除草稿；记录 operation_logs；发送通知给直属上级（经理仪表盘待办 +1） |
| **预估 Token** | ~25k |
| **验收标准** | 提交后数据库 self_submitted=true、status=pending_manager；经理收到待办通知；草稿已清除 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P4-02 |

### P4-05 自评 — 状态机转换
| 项目 | 内容 |
|------|------|
| **任务名称** | 注册 `submit_self` 状态转换规则 |
| **技术范围** | 后端核心算法 |
| **所属 Story** | Story-11 |
| **用户场景** | 场景 3 |
| **任务描述** | 在状态机中注册：pending_self + submit_self → pending_manager。校验：self_scores 完整、self_facts 可选。非法状态提交时返回明确错误 |
| **预估 Token** | ~10k |
| **验收标准** | `transition("pending_self", "submit_self")` 返回 "pending_manager"；非 pending_self 状态提交抛出 BizError 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P3-10 |

### P4-06 上级评分列表 — 后端 API
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 `GET /api/v1/manager/score-list` 上级评分列表接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-12 |
| **用户场景** | 场景 4 |
| **任务描述** | 查询当前经理的所有下属考核记录，支持筛选：状态（pending_manager/pending_peer/pending_summary）、部门、搜索（姓名/工号）；返回：员工姓名、工号、岗位、当前状态、自评完成时间、剩余截止时间、部门 |
| **预估 Token** | ~20k |
| **验收标准** | 李建国登录后返回 3 名下属；仅返回 manager_id 匹配的员工；按状态筛选正确 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P2-05 |

### P4-07 上级评分列表 — 前端页面（ScoreSheetList.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现上级评分列表页 |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-12 |
| **用户场景** | 场景 4 |
| **任务描述** | 表格：员工姓名、工号、部门、当前状态（Tag）、自评完成时间、剩余截止时间；顶部筛选：状态下拉、部门下拉、搜索框；点击员工姓名进入评分详情页 |
| **预估 Token** | ~30k |
| **验收标准** | 李建国登录后显示 3 名待评分员工；状态筛选「pending_manager」正确过滤；点击跳转评分详情 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P4-06、P0-18 |

### P4-08 上级评分详情 — 后端 API（加载）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 `GET /api/v1/assessment-records/{id}/manager` 上级评分详情加载接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-13 |
| **用户场景** | 场景 4 |
| **任务描述** | 返回：员工基本信息、自评结果（含事实描述）、KPI 快照（含 actual_score 输入）、三维度评分区、评分草稿（如有）、协作人评分结果（如已完成）。校验：仅当前经理可访问自己下属的评分详情 |
| **预估 Token** | ~25k |
| **验收标准** | 李建国访问王志强记录返回完整数据；赵晓峰访问王志强记录返回 403；自评事实描述正确返回 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P4-06 |

### P4-09 上级评分详情 — 前端页面（ScoreSheetView.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现上级评分详情页 |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-13 |
| **用户场景** | 场景 4 |
| **任务描述** | 页面分区：基本信息区（只读）、自评结果区（只读，含事实描述）、KPI 评分区（实际得分输入）、三维度评分区（得分输入 + 锚点）、评语区（文本域，≥20 字，实时计数）、协作人评分结果区（如已完成）、协作人分配区（如开启）。差异提示：任一维度与自评差异 >20 分弹窗确认 |
| **预估 Token** | ~50k |
| **验收标准** | KPI 实际得分可输入；评语少于 20 字提交时拦截；差异 >20 分弹出确认框；保存草稿功能正常 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P4-08、P0-18 |

### P4-10 上级评分提交 — 后端 API
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 `POST /api/v1/assessment-records/{id}/manager-submit` 上级评分提交接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-14 |
| **用户场景** | 场景 4 |
| **任务描述** | 校验：状态 pending_manager、KPI 得分完整、三维度得分完整、评语 ≥20 字；写入 manager_scores、manager_comment、manager_submitted=true；若协作评分开启，创建 PeerReviewTask 记录（1-3 人）；更新状态（开启协作 → pending_peer，关闭协作 → pending_summary）；清除草稿；发送通知 |
| **预估 Token** | ~30k |
| **验收标准** | 提交后 manager_submitted=true；协作评分开启时创建 PeerReviewTask 且状态为 pending；关闭协作评分时状态变为 pending_summary 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P4-08 |

### P4-11 协作人分配 — 后端候选协作人查询接口
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 `GET /api/v1/employees/candidates?exclude_id={id}` 候选协作人查询 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-14 |
| **用户场景** | 场景 4 |
| **任务描述** | 返回：其他部门在职员工（排除被评分人自己、已分配协作人、非在职员工）。支持按姓名/工号搜索。返回字段：id、姓名、工号、部门、岗位 |
| **预估 Token** | ~15k |
| **验收标准** | 查询王志强候选协作人时返回赵晓峰（产品部）等；不包含王志强自己；不包含已停用员工 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P2-05 |

### P4-12 协作人分配 — 前端协作人选择器组件
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现协作人多选组件（PeerReviewerSelector.vue） |
| **技术范围** | 前端组件 |
| **所属 Story** | Story-14 |
| **用户场景** | 场景 4 |
| **任务描述** | 弹窗选择器：搜索框（姓名/工号）、部门筛选、员工列表（多选 checkbox）、已选区域（显示 1-3 人，可删除）。提交时校验：至少选 1 人、最多 3 人。防自我评分：列表中排除被评分人 |
| **预估 Token** | ~30k |
| **验收标准** | 选择 1-3 人提交成功；选 0 人时提交拦截；选 4 人时提交拦截；被评分人不在列表中 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P4-11 |

### P4-13 协作评分 — 后端待评列表接口
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 `GET /api/v1/peer/review-list` 协作人待评列表接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-15 |
| **用户场景** | 场景 5 |
| **任务描述** | 查询当前用户作为协作人的所有 PeerReviewTask 记录，按截止时间排序。返回：被评分人姓名、部门、岗位、周期名称、状态（pending/completed）、截止时间 |
| **预估 Token** | ~15k |
| **验收标准** | 赵晓峰登录后返回待评王志强（研发部）；已评任务显示在「已评」区域 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-07 |

### P4-14 协作评分 — 后端评分提交接口
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 `POST /api/v1/peer/review-tasks/{id}/submit` 协作评分提交接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-15 |
| **用户场景** | 场景 5 |
| **任务描述** | 校验：当前用户是任务分配的 reviewer、状态 pending、工作能力得分 0-100、协作评语 ≥20 字且 ≤500 字；写入 ability_score、comment、status=completed、submitted_at；检查该 record 的所有协作任务是否均已完成，若全部完成则更新 assessment_record 状态为 pending_summary，通知 HR |
| **预估 Token** | ~25k |
| **验收标准** | 提交后 task 状态变为 completed；所有协作任务完成后 record 状态变为 pending_summary；HR 收到通知 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P4-13 |

### P4-15 协作评分 — 前端页面（PeerReviewScore.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现协作评分页面 |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-15 |
| **用户场景** | 场景 5 |
| **任务描述** | 页面：被评分人基本信息（只读）、工作能力维度评分（输入框 + 锚点）、协作评语文本域（≥20 字，实时计数）、其他维度锁定显示「协作人仅可评分工作能力维度」。提交后页面锁定 |
| **预估 Token** | ~30k |
| **验收标准** | 输入 86 分和评语后提交成功；提交后页面显示「已提交，不可修改」；其他维度显示锁定提示 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P4-14、P0-18 |

### P4-16 评分管理 — 状态机完整转换注册
| 项目 | 内容 |
|------|------|
| **任务名称** | 注册所有评分阶段状态转换规则 |
| **技术范围** | 后端核心算法 |
| **所属 Story** | Story-11、Story-14、Story-15 |
| **用户场景** | 场景 3、4、5 |
| **任务描述** | 在状态机中注册：pending_manager + submit_manager → pending_peer（协作开启）或 pending_summary（协作关闭）；pending_peer + complete_peer → pending_summary；每个转换绑定对应的校验逻辑和副作用（通知、日志） |
| **预估 Token** | ~20k |
| **验收标准** | 所有评分阶段转换单元测试通过（≥ 6 个用例） 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P4-05、P4-10、P4-14 |

### P4-17 评分管理 — 单元测试（自评）
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写自评相关 pytest 单元测试 |
| **技术范围** | 后端测试 |
| **所属 Story** | Story-10、Story-11 |
| **用户场景** | — |
| **任务描述** | 测试：① 自评加载（权限隔离）；② 自评草稿保存/读取；③ 自评提交（校验、状态变更、通知）；④ 非法状态提交（如已提交再次提交） |
| **预估 Token** | ~25k |
| **验收标准** | `pytest tests/test_self_assessment.py` 全部通过（≥ 10 个用例） |
| **前置依赖** | P4-04 |

### P4-18 评分管理 — 单元测试（上级评分）
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写上级评分相关 pytest 单元测试 |
| **技术范围** | 后端测试 |
| **所属 Story** | Story-12 ~ Story-14 |
| **用户场景** | — |
| **任务描述** | 测试：① 评分列表（权限隔离、筛选）；② 评分详情加载（含自评事实描述）；③ 评分提交（KPI/维度/评语校验）；④ 协作人分配（1-3 人）；⑤ 差异提示（差异 >20 分） |
| **预估 Token** | ~30k |
| **验收标准** | `pytest tests/test_manager_score.py` 全部通过（≥ 12 个用例） |
| **前置依赖** | P4-10 |

### P4-19 评分管理 — 单元测试（协作评分）
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写协作评分相关 pytest 单元测试 |
| **技术范围** | 后端测试 |
| **所属 Story** | Story-15 |
| **用户场景** | — |
| **任务描述** | 测试：① 待评列表；② 评分提交（得分/评语校验）；③ 防自我评分；④ 所有协作人完成后状态自动推进；⑤ 通知触发 |
| **预估 Token** | ~25k |
| **验收标准** | `pytest tests/test_peer_review.py` 全部通过（≥ 10 个用例） |
| **前置依赖** | P4-14 |

### P4-20 评分管理 — 前端测试
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写 SelfAssessment、ScoreSheetView、PeerReviewScore 的 Vitest 测试 |
| **技术范围** | 前端测试 |
| **所属 Story** | Story-10、Story-13、Story-15 |
| **用户场景** | — |
| **任务描述** | 测试：① 页面加载渲染；② 表单校验（得分范围、评语字数）；③ 保存草稿；④ 提交后状态锁定 |
| **预估 Token** | ~25k |
| **验收标准** | `npm run test:unit` 通过（≥ 8 个用例） 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P4-09、P4-15 |

### P4-21 评分管理 E2E（场景 3 — 自评）
| 项目 | 内容 |
|------|------|
| **任务名称** | 使用 Playwright 测试「员工自评」场景 |
| **技术范围** | E2E 测试 |
| **所属 Story** | Story-10、Story-11 |
| **用户场景** | 场景 3 |
| **任务描述** | 自动化测试：登录（王志强）→ 进入「我的绩效」→ 点击「去自评」→ 填写三维度得分（82/84/88）→ 保存草稿 → 刷新页面恢复草稿 → 提交自评 → 验证状态变为「待上级评分」 |
| **预估 Token** | ~25k |
| **验收标准** | `npx playwright test tests/e2e/scenario3-employee-self.spec.ts` 通过 |
| **前置依赖** | P4-20 |

### P4-22 评分管理 E2E（场景 4+5 — 上级评分+协作评分）
| 项目 | 内容 |
|------|------|
| **任务名称** | 使用 Playwright 测试「上级评分+协作评分」场景 |
| **技术范围** | E2E 测试 |
| **所属 Story** | Story-13、Story-14、Story-15 |
| **用户场景** | 场景 4、5 |
| **任务描述** | 自动化测试：登录（李建国）→ 上级评分列表 → 给王志强评分（85/88/90）→ 填写评语（≥20字）→ 分配协作人（赵晓峰）→ 提交 → 登录（赵晓峰）→ 协作评分 → 给王志强工作能力评分 86 → 提交 → 验证状态变为 pending_summary |
| **预估 Token** | ~30k |
| **验收标准** | `npx playwright test tests/e2e/scenario4-manager-score.spec.ts` 通过 |
| **前置依赖** | P4-21 |

---

## P5 汇总与审批模块（18 个任务）

> **目标**: 实现加权计算、强制分布、审批链、绩效面谈。  
> **覆盖 Story**: Story-16（加权计算）、Story-17（强制分布）、Story-18（审批列表）、Story-19（审批操作）、Story-20（绩效面谈）。  
> **用户场景**: 场景 2（汇总）、场景 4（审批/面谈）、场景 7/8（全流程）。

### P5-01 加权计算算法 — 后端 Service
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 score_calculator.py（加权计算核心） |
| **技术范围** | 后端核心算法 |
| **所属 Story** | Story-16 |
| **用户场景** | 场景 2 |
| **任务描述** | 按 PRD 4.4.2 公式实现：① 维度得分 = Σ(评分人维度分 × 评分人维度权重)；② 总分 = Σ(维度得分 × 维度权重)；③ 精度控制（中间结果保留 2 位小数，最终总分保留 1 位）。支持从 ConfigService 读取权重配置 |
| **预估 Token** | ~20k |
| **验收标准** | 输入自评(82/84/88)+上级(85/88/90)+协作(86)，按默认权重计算总分 = 87.1；精度计算正确（用边界值测试） 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P1-14 |

### P5-02 加权计算 — 后端汇总触发接口
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 `POST /api/v1/cycles/{id}/trigger-summary` 触发汇总计算接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-16 |
| **用户场景** | 场景 2 |
| **任务描述** | 校验：周期状态 pending_summary、所有评分已完成、权重配置合计 100%；批量计算：查询所有考核记录，逐人调用 score_calculator 计算，写入 total_score、dimension_scores、initial_grade；若触发强制分布则状态变为 pending_distribution_review，否则变为 pending_approval；返回计算结果摘要（总人数、异常分数人数） |
| **预估 Token** | ~30k |
| **验收标准** | 触发计算后所有记录有 total_score；异常分数（<60 或 >98）正确标出；未触发强制分布时状态变为 pending_approval 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P5-01 |

### P5-03 强制分布算法 — 后端 Service
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 distribution_enforcer.py（强制分布核心算法） |
| **技术范围** | 后端核心算法 |
| **所属 Story** | Story-17 |
| **用户场景** | 场景 2 |
| **任务描述** | 按 PRD 4.5.3 实现：① 按部门统计人数 N；② 计算各等级上限 floor(N × ratio)；③ 按总分排序；④ 首次映射等级；⑤ 降级调整（迭代最多 10 轮，从低到高依次降级）；⑥ 小部门豁免（≤5 人时放宽规则）；⑦ 记录降级日志（original_grade、adjusted_grade、reason） |
| **预估 Token** | ~30k |
| **验收标准** | PRD 4.5.3 示例（20 人 A=5→4, B=8→10, C=4→5, D=3→1）计算结果与文档一致；小部门（3 人）仅限制 A≤1、D≤1 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P5-01 |

### P5-04 强制分布 — 后端确认接口
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 `POST /api/v1/cycles/{id}/confirm-distribution` 强制分布确认接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-17 |
| **用户场景** | 场景 2 |
| **任务描述** | 校验：周期状态 pending_distribution_review；将 adjusted_grade 写入 grade；更新状态为 pending_approval；记录 operation_logs（含降级名单） |
| **预估 Token** | ~15k |
| **验收标准** | 确认后所有被降级员工的 grade = adjusted_grade；状态变为 pending_approval 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P5-03 |

### P5-05 汇总处理 — 前端页面（SummaryDashboard.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现汇总处理页面（HR 专用） |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-16、Story-17 |
| **用户场景** | 场景 2 |
| **任务描述** | 页面：「触发汇总计算」按钮（校验通过后可用）、汇总结果表格（姓名、部门、总分、初始等级、调整后等级、强制调整标识🔴）、部门分布统计（原始 vs 调整后饼图）、强制调整人员高亮筛选。异常分数标红（<60 或 >98） |
| **预估 Token** | ~50k |
| **验收标准** | 点击「触发汇总计算」后表格刷新显示总分和等级；强制调整人员显示红色图标和降级原因；饼图正确展示原始/调整后分布 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P5-04、P0-18 |

### P5-06 审批 — 后端列表接口（Step 1 + Step 2）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现审批列表接口（按角色隔离） |
| **技术范围** | 后端 API |
| **所属 Story** | Story-18 |
| **用户场景** | 场景 4 |
| **任务描述** | `GET /api/v1/approvals`：按当前用户角色返回不同列表。manager（Step 1）：返回自己下属且待 Step 1 审批的记录；hr（Step 2）：返回所有已通过 Step 1 的记录。支持筛选：部门、异常分数、强制调整 |
| **预估 Token** | ~25k |
| **验收标准** | 李建国登录仅返回自己下属；张燕子登录返回全量 Step 2 待审批；经理访问 Step 2 列表返回 403 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P5-04 |

### P5-07 审批 — 后端详情接口
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 `GET /api/v1/approvals/{record_id}` 审批详情接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-18 |
| **用户场景** | 场景 4 |
| **任务描述** | 返回：员工基本信息、自评结果（含事实描述）、上级评分（含 KPI、评语）、协作评分（含评语）、加权计算结果（维度得分、总分、等级）、强制调整记录（如有）、历史绩效（近 3 周期）、异常提示（标红/黄）。按角色隔离数据权限 |
| **预估 Token** | ~25k |
| **验收标准** | 返回完整评分数据；异常分数显示🔴；强制调整显示具体原因；历史绩效正确 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P5-06 |

### P5-08 审批 — 后端操作接口（通过/驳回/打回）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 `POST /api/v1/approvals/{record_id}/action` 审批操作接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-19 |
| **用户场景** | 场景 4 |
| **任务描述** | 请求体：{action: "approve"|"reject"|"rollback", comment: "...", step_index: 1|2}。校验：当前用户是当前步骤审批人、审批意见 ≥10 字。approve：Step 1→保持 pending_approval 等 Step 2；Step 2→pending_interview。reject：保持当前状态，记录拒绝。rollback：状态回退到 pending_manager，清除 manager_scores、manager_comment，保留自评和协作评 |
| **预估 Token** | ~30k |
| **验收标准** | Step 1 通过后状态仍为 pending_approval；Step 2 通过后变为 pending_interview；rollback 后 manager_scores 被清空；重复审批返回 409 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P5-07 |

### P5-09 审批 — 状态机注册（审批链）
| 项目 | 内容 |
|------|------|
| **任务名称** | 注册审批阶段状态转换规则 |
| **技术范围** | 后端核心算法 |
| **所属 Story** | Story-19 |
| **用户场景** | 场景 4 |
| **任务描述** | 注册：pending_approval + approve（Step 1）→ pending_approval；pending_approval + approve（Step 2）→ pending_interview；pending_approval + reject → 保持 pending_approval；pending_approval + rollback → pending_manager。每个动作记录 approval_records |
| **预估 Token** | ~15k |
| **验收标准** | 所有审批动作单元测试通过（≥ 8 个用例） 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P4-16 |

### P5-10 审批 — 前端列表页（ApprovalWorkbench.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现审批工作台页面 |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-18 |
| **用户场景** | 场景 4 |
| **任务描述** | 表格：员工姓名、工号、部门、总分、等级、异常标记、强制调整标记、提交时间；顶部筛选：部门、异常分数、强制调整；操作：查看详情（进入审批详情页）。经理视角显示「Step 1 待审批」标签；HR 视角显示「Step 2 待审批」标签 |
| **预估 Token** | ~35k |
| **验收标准** | 李建国登录显示 Step 1 列表；张燕子登录显示 Step 2 列表；异常分数行标红；强制调整行标黄 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P5-06、P0-18 |

### P5-11 审批 — 前端详情页（ApprovalDetail.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现审批详情页 |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-18、Story-19 |
| **用户场景** | 场景 4 |
| **任务描述** | 页面分区：基本信息、评分详情（自评/上级/协作）、加权结果、异常提示区（标红/黄）、历史绩效区、审批操作区（审批意见文本域 ≥10 字、通过/驳回/打回按钮）。底部显示部门当前等级分布比例（如 A: 5/4 人🔴） |
| **预估 Token** | ~45k |
| **验收标准** | 页面加载正确显示所有评分数据；差异 >20 分显示黄色提示；操作按钮点击后弹出确认对话框 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P5-07、P0-18 |

### P5-12 绩效面谈 — 后端 API
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 `POST /api/v1/assessment-records/{id}/interview` 面谈记录接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-20 |
| **用户场景** | 场景 4 |
| **任务描述** | 校验：状态 pending_interview、当前用户是员工直属上级、面谈时间 ≤ 当前时间、沟通内容 ≥50 字、C/D 等级改进计划 ≥30 字；写入 interview_record JSON；更新状态为 published；发送通知给员工 |
| **预估 Token** | ~20k |
| **验收标准** | C 等级员工未填写改进计划返回 400；填写后状态变为 published；员工收到结果发布通知 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P5-08 |

### P5-13 绩效面谈 — 后端列表接口
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 `GET /api/v1/manager/interview-list` 面谈列表接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-20 |
| **用户场景** | 场景 4 |
| **任务描述** | 返回经理的「待面谈」和「已面谈」列表。待面谈：状态 pending_interview 的下属；已面谈：已提交面谈记录的下属。C/D 等级员工标记红色高亮。支持按姓名/工号搜索 |
| **预估 Token** | ~15k |
| **验收标准** | 李建国登录返回待面谈 3 人；C/D 等级员工标记正确；搜索「王志强」正确过滤 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P5-12 |

### P5-14 绩效面谈 — 前端页面（InterviewList.vue + InterviewForm.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现绩效面谈列表和表单页面 |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-20 |
| **用户场景** | 场景 4 |
| **任务描述** | 列表页：「待面谈」和「已面谈」两个分区，C/D 等级高亮，点击员工进入表单。表单页：员工基本信息（只读）、总分、等级、各维度得分（参考）、面谈时间/地点输入、沟通内容文本域（≥50 字）、改进计划文本域（C/D 必填 ≥30 字）。支持批量提交 |
| **预估 Token** | ~40k |
| **验收标准** | 列表正确分区；C/D 等级红色高亮；表单校验字数；提交后状态变为 published 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P5-13、P0-18 |

### P5-15 汇总与审批 — 状态机完整注册（汇总→审批→面谈）
| 项目 | 内容 |
|------|------|
| **任务名称** | 注册汇总、审批、面谈阶段全部状态转换 |
| **技术范围** | 后端核心算法 |
| **所属 Story** | Story-16、Story-17、Story-19、Story-20 |
| **用户场景** | 场景 2、4 |
| **任务描述** | 注册：pending_summary + trigger_summary → pending_distribution_review（触发强制分布）或 pending_approval（未触发）；pending_distribution_review + confirm_distribution → pending_approval；pending_approval + approve_step2 → pending_interview；pending_interview + submit_interview → published |
| **预估 Token** | ~15k |
| **验收标准** | 所有状态转换单元测试通过（≥ 10 个用例） 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P5-09、P5-12 |

### P5-16 汇总与审批模块 — 单元测试（汇总+强制分布）
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写加权计算和强制分布的 pytest 单元测试 |
| **技术范围** | 后端测试 |
| **所属 Story** | Story-16、Story-17 |
| **用户场景** | — |
| **任务描述** | 测试：① 加权计算（边界值、精度）；② 强制分布（正常部门、小部门、超限降级、迭代收敛）；③ 降级记录完整性；④ 触发/未触发强制分布的状态分支 |
| **预估 Token** | ~30k |
| **验收标准** | `pytest tests/test_summary.py` 全部通过（≥ 15 个用例） |
| **前置依赖** | P5-03 |

### P5-17 汇总与审批模块 — 单元测试（审批+面谈）
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写审批和面谈的 pytest 单元测试 |
| **技术范围** | 后端测试 |
| **所属 Story** | Story-18 ~ Story-20 |
| **用户场景** | — |
| **任务描述** | 测试：① 审批列表权限隔离（Step 1/Step 2）；② 审批详情数据完整性；③ 通过/驳回/打回动作；④ 打回后 manager_scores 清空；⑤ 面谈校验（C/D 必填改进计划）；⑥ 面谈后状态变为 published |
| **预估 Token** | ~30k |
| **验收标准** | `pytest tests/test_approval.py` 全部通过（≥ 15 个用例） |
| **前置依赖** | P5-12 |

### P5-18 汇总与审批模块 E2E（场景 7 核心链路）
| 项目 | 内容 |
|------|------|
| **任务名称** | 使用 Playwright 测试「汇总→审批→面谈」核心链路 |
| **技术范围** | E2E 测试 |
| **所属 Story** | Story-16 ~ Story-20 |
| **用户场景** | 场景 7 |
| **任务描述** | 自动化测试：登录（张燕子）→ 触发汇总计算 → 查看强制分布结果 → 确认调整 → 登录（李建国）→ 审批工作台 → 确认王志强通过 → 登录（张燕子）→ 最终审批通过 → 登录（李建国）→ 绩效面谈 → 填写记录 → 提交 → 验证状态变为 published |
| **预估 Token** | ~35k |
| **验收标准** | `npx playwright test tests/e2e/scenario7-summary-approval.spec.ts` 通过 |
| **前置依赖** | P5-17 |

---

## P6 发布与归档模块（16 个任务）

> **目标**: 实现结果发布、员工查看、申诉、高管仪表盘、归档导出。  
> **覆盖 Story**: Story-21（结果发布/员工查看）、Story-22（申诉发起）、Story-23（申诉复核）、Story-24（高管仪表盘）、Story-25（归档导出）。  
> **用户场景**: 场景 3（查看结果）、场景 6（高管查看）、场景 8（申诉）、场景 7/8（归档）。

### P6-01 结果发布 — 员工「我的绩效」后端 API
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 `GET /api/v1/my-performance` 员工我的绩效接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-21 |
| **用户场景** | 场景 3 |
| **任务描述** | 返回：当前考核状态（如有）、历史考核记录列表（按周期倒序，含总分、等级、发布日期）、各维度得分、经理评语、KPI 明细、强制调整说明（如有）、申诉状态（如有）。权限：仅返回当前登录员工的数据；未发布状态脱敏（不返回 total_score/grade） |
| **预估 Token** | ~25k |
| **验收标准** | 王志强登录返回自己的历史绩效；未发布状态仅显示「当前状态：待审批」；已发布状态显示完整数据 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P5-12 |

### P6-02 结果发布 — 员工「我的绩效」前端页面（MyPerformance.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现我的绩效页面 |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-21 |
| **用户场景** | 场景 3 |
| **任务描述** | 页面：当前状态卡片（「您的考核结果已发布」或「当前状态：待审批」）、历史记录列表（周期名称、总分、等级、发布日期，点击展开详情抽屉）、详情抽屉（各维度得分、评分人明细、经理评语、KPI 明细、强制调整提示、申诉状态）。若等级被强制调整，顶部显示黄色提示条 |
| **预估 Token** | ~40k |
| **验收标准** | 页面加载正确；点击记录展开抽屉显示详情；强制调整员工显示黄色提示条；未发布状态脱敏 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P6-01、P0-18 |

### P6-03 趋势分析 — 后端趋势数据接口
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 `GET /api/v1/my-performance/trend` 个人趋势接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-21 |
| **用户场景** | 场景 3 |
| **任务描述** | 返回近 4-8 个周期的趋势数据：总分走势、各维度得分走势、等级变化。支持切换 4 周期/8 周期。仅返回 published/archived 状态的记录 |
| **预估 Token** | ~15k |
| **验收标准** | 返回正确的 JSON 数组（x: 周期名称, y: 分数）；空数组时返回友好提示 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P6-01 |

### P6-04 趋势分析 — 前端趋势图（ECharts）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现个人绩效趋势图组件 |
| **技术范围** | 前端组件 |
| **所属 Story** | Story-21 |
| **用户场景** | 场景 3 |
| **任务描述** | ECharts 折线图：X 轴周期名称，Y 轴分数 0-100；数据系列：总分（黑色实线）、业绩（蓝色虚线）、能力（绿色虚线）、态度（橙色虚线）；鼠标悬停显示具体分数和等级；支持切换近 4 周期/8 周期 |
| **预估 Token** | ~30k |
| **验收标准** | 图表正确渲染；悬停显示 Tooltip；切换 4/8 周期数据正确更新 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P6-03、P0-03 |

### P6-05 申诉 — 后端发起接口
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 `POST /api/v1/assessment-records/{id}/appeal` 申诉发起接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-22 |
| **用户场景** | 场景 8 |
| **任务描述** | 校验：当前状态 published、申诉理由 ≥20 字且 ≤1000 字；写入 appeal_reason、appeal_status=appealed；记录 operation_logs；通知 HR |
| **预估 Token** | ~15k |
| **验收标准** | 发起后 appeal_status=appealed；HR 收到待处理申诉通知；非 published 状态发起返回 400 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P6-01 |

### P6-06 申诉 — 后端复核接口
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 `POST /api/v1/appeals/{id}/resolve` 申诉复核接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-23 |
| **用户场景** | 场景 8 |
| **任务描述** | 请求体：{resolution: "maintain"|"adjust", new_grade: "A"|"B"|"C"|"D"|null, comment: "..."}。校验：当前用户为 hr/admin、appeal_status=appealed；maintain：状态回 published，记录复核结论；adjust：更新 grade、记录调整原因，状态回 published。通知员工复核结果 |
| **预估 Token** | ~20k |
| **验收标准** | 维持原结果后员工收到「维持」通知；调整后 grade 更新；非 hr 访问返回 403 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P6-05 |

### P6-07 申诉 — 前端申诉页面（AppealView.vue + AppealManage.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现申诉发起页和申诉管理页 |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-22、Story-23 |
| **用户场景** | 场景 8 |
| **任务描述** | 员工端：「我的绩效」中点击「发起申诉」，弹窗填写申诉理由（≥20 字），提交后显示申诉状态。HR 端：「申诉管理」列表页，展示申诉人、理由、状态；点击处理进入详情页，可查看评分原始数据、强制分布记录、计算过程，选择「维持」或「调整」，填写复核结论 |
| **预估 Token** | ~40k |
| **验收标准** | 员工发起申诉后状态变为「申诉中」；HR 复核后员工收到通知；调整时显示调整原因 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P6-06、P0-18 |

### P6-08 高管仪表盘 — 后端聚合数据接口
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 `GET /api/v1/executive/dashboard` 高管仪表盘数据接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-24 |
| **用户场景** | 场景 6 |
| **任务描述** | 返回：统计卡片（员工总数、考核覆盖率、公司平均总分、待审批数）、绩效分布饼图数据（A/B/C/D 占比）、部门平均分对比数据、近 4 季度趋势数据、强制调整人员列表。仅 executive 角色可访问，只读 |
| **预估 Token** | ~25k |
| **验收标准** | 陈志强登录返回全公司数据；其他角色访问返回 403；数据聚合正确（覆盖率、平均分、分布比例） 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P5-12 |

### P6-09 高管仪表盘 — 前端页面（DashboardExecutive.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现高管仪表盘页面 |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-24 |
| **用户场景** | 场景 6 |
| **任务描述** | 统计卡片区（4 个卡片）、绩效分布饼图（ECharts）、部门平均分对比柱状图、绩效趋势折线图、强制调整人员列表（标红）。全程只读，无操作按钮。支持按部门筛选 |
| **预估 Token** | ~45k |
| **验收标准** | 页面正确渲染所有图表；强制调整人员标红；切换部门时数据正确更新；无「评分/审批/配置」按钮 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P6-08、P0-18 |

### P6-10 归档 — 后端归档接口
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 `POST /api/v1/cycles/{id}/archive` 归档接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-25 |
| **用户场景** | 场景 7、8 |
| **任务描述** | 校验：周期状态 published、仅 hr/admin 可操作；更新周期状态为 archived、archived_at=当前时间；所有 assessment_records 设置 is_locked=true；记录 operation_logs；触发 PDF 档案生成（异步） |
| **预估 Token** | ~20k |
| **验收标准** | 归档后状态变为 archived；考核记录不可修改（更新接口返回 400）；is_locked=true 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P5-12 |

### P6-11 归档 — 后端 PDF 生成 Service
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现 pdf_archive_generator.py（PDF 档案生成） |
| **技术范围** | 后端核心算法 |
| **所属 Story** | Story-25 |
| **用户场景** | 场景 7、8 |
| **任务描述** | 使用 Playwright 或 WeasyPrint 生成 PDF：封面（员工信息、周期）、基本信息、评分详情（自评/上级/协作）、加权结果、强制调整记录、面谈记录、申诉记录。每个员工一个 PDF，存储到 uploads/archives/ |
| **预估 Token** | ~40k |
| **验收标准** | 生成的 PDF 包含全部内容；排版正确；可在浏览器正常预览；文件路径正确存入数据库 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P6-10 |

### P6-12 归档 — 后端 Excel 导出接口
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现考核汇总报表 Excel 导出接口 |
| **技术范围** | 后端 API |
| **所属 Story** | Story-25 |
| **用户场景** | 场景 2、7、8 |
| **任务描述** | `GET /api/v1/cycles/{id}/export-excel`：生成 Excel 汇总表，含姓名、部门、总分、等级、各维度得分、强制调整标记。支持按部门筛选。使用 openpyxl 生成，支持流式下载 |
| **预估 Token** | ~25k |
| **验收标准** | 下载的 .xlsx 可在 Excel/WPS 正确打开；数据与数据库一致；按部门筛选正确 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P5-12 |

### P6-13 归档 — 前端报表导出页（ReportExport.vue）
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现报表导出页面 |
| **技术范围** | 前端页面 |
| **所属 Story** | Story-25 |
| **用户场景** | 场景 2、7、8 |
| **任务描述** | 页面：选择周期（下拉）、选择部门（多选）、导出格式（Excel/PDF）、「导出」按钮。导出时显示进度条（大文件时）。下方显示历史导出记录（文件名、时间、状态） |
| **预估 Token** | ~30k |
| **验收标准** | 选择周期和部门后点击导出，浏览器下载文件；大文件导出时显示进度条 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。 |
| **前置依赖** | P6-12、P0-18 |

### P6-14 归档锁定 — 后端拦截中间件
| 项目 | 内容 |
|------|------|
| **任务名称** | 实现归档后数据修改拦截 |
| **技术范围** | 后端基础设施 |
| **所属 Story** | Story-25 |
| **用户场景** | 场景 7、8 |
| **任务描述** | 在 Service 层或 Router 层添加拦截：若 assessment_record.cycle.status == archived，则所有更新/删除/评分/审批/申诉操作返回 400「已归档，不可修改」。仅 admin 可执行解冻（unarchive），解冻需记录操作日志 |
| **预估 Token** | ~15k |
| **验收标准** | 归档后尝试修改评分返回 400；admin 可执行解冻；解冻记录正确写入 operation_logs 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P6-10 |

### P6-15 发布与归档 — 单元测试
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写发布、申诉、归档的 pytest 单元测试 |
| **技术范围** | 后端测试 |
| **所属 Story** | Story-21 ~ Story-25 |
| **用户场景** | — |
| **任务描述** | 测试：① 我的绩效权限隔离（仅本人）；② 趋势数据正确性；③ 申诉发起/复核；④ 高管仪表盘权限；⑤ 归档后数据锁定；⑥ 归档前状态校验 |
| **预估 Token** | ~30k |
| **验收标准** | `pytest tests/test_publish_archive.py` 全部通过（≥ 15 个用例） |
| **前置依赖** | P6-06、P6-10 |

### P6-16 发布与归档 E2E（场景 8 — 申诉+归档）
| 项目 | 内容 |
|------|------|
| **任务名称** | 使用 Playwright 测试「申诉+归档」完整场景 |
| **技术范围** | E2E 测试 |
| **所属 Story** | Story-22、Story-23、Story-25 |
| **用户场景** | 场景 8 |
| **任务描述** | 自动化测试：登录（孙伟）→ 查看结果 → 发起申诉 → 填写理由 → 登录（张燕子）→ 申诉管理 → 查看申诉详情 → 复核评分数据 → 选择「维持原结果」→ 录入结论 → 登录（孙伟）→ 查看申诉结果 → 登录（张燕子）→ 执行归档 → 验证状态变为 archived → 下载 PDF 档案 |
| **预估 Token** | ~30k |
| **验收标准** | `npx playwright test tests/e2e/scenario8-appeal-archive.spec.ts` 通过 |
| **前置依赖** | P6-15 |

---

## P7 集成测试与验收（10 个任务）

> **目标**: 确保系统可交付，覆盖全流程、性能、安全。  
> **覆盖范围**: 全量 Story、全量场景。

### P7-01 全流程 E2E 测试（场景 7 — 完整链路）
| 项目 | 内容 |
|------|------|
| **任务名称** | 使用 Playwright 测试全流程场景 7（研发部王志强） |
| **技术范围** | E2E 测试 |
| **所属 Story** | Story-01 ~ Story-25 |
| **用户场景** | 场景 7 |
| **任务描述** | 自动化测试完整链路：admin 配置 → HR 导入员工 → 创建周期 → 启动考核 → 员工自评 → 上级评分（关闭协作）→ 触发汇总 → 强制分布 → 审批 Step 1 → 审批 Step 2 → 绩效面谈 → 结果发布 → 高管查看 → 归档 |
| **预估 Token** | ~40k |
| **验收标准** | `npx playwright test tests/e2e/scenario7-full-flow.spec.ts` 通过（完整链路无报错） |
| **前置依赖** | P6-16 |

### P7-02 性能测试 — 汇总计算（500 人）
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写汇总计算性能测试 |
| **技术范围** | 性能测试 |
| **所属 Story** | Story-16 |
| **用户场景** | — |
| **任务描述** | 使用 pytest + 数据工厂生成 500 条完整评分数据，触发汇总计算，断言后端处理时间 < 3 秒；强制分布计算时间 < 2 秒 |
| **预估 Token** | ~20k |
| **验收标准** | 500 人汇总计算响应 < 3s；强制分布计算 < 2s；pytest 通过 |
| **前置依赖** | P5-16 |

### P7-03 性能测试 — 并发评分（50 并发）
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写并发评分压力测试 |
| **技术范围** | 性能测试 |
| **所属 Story** | Story-10、Story-13、Story-15 |
| **用户场景** | — |
| **任务描述** | 使用 Locust 或 JMeter 模拟 50 并发用户同时提交评分，断言成功率 100%、响应时间 < 2 秒、数据库无数据冲突 |
| **预估 Token** | ~20k |
| **验收标准** | 50 并发同时提交，成功率 100%，P95 响应时间 < 2s 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P4-22 |

### P7-04 安全测试 — 权限隔离渗透测试
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写权限隔离安全测试 |
| **技术范围** | 安全测试 |
| **所属 Story** | 全部 |
| **用户场景** | — |
| **任务描述** | 测试：① 员工 A 访问员工 B 的评分/绩效/审批详情 → 返回 403；② 经理访问非下属记录 → 返回 403；③ 非 executive 访问高管仪表盘 → 返回 403；④ 未登录访问任意 API → 返回 401 |
| **预估 Token** | ~20k |
| **验收标准** | `pytest tests/test_security.py` 全部通过（≥ 20 个用例） |
| **前置依赖** | P6-15 |

### P7-05 安全测试 — SQL 注入与 XSS 防护测试
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写 SQL 注入和 XSS 防护测试 |
| **技术范围** | 安全测试 |
| **所属 Story** | 全部 |
| **用户场景** | — |
| **任务描述** | 测试：① 在表单中输入 SQL 注入字符串（如 `' OR 1=1 --`），验证后端返回 400 而非数据库错误；② 输入 XSS 脚本（如 `<script>alert(1)</script>`），验证前端渲染时自动转义，不执行脚本 |
| **预估 Token** | ~15k |
| **验收标准** | SQL 注入被拦截；XSS 脚本不被执行 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P7-04 |

### P7-06 备份与恢复测试
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写数据库备份与恢复测试 |
| **技术范围** | 运维测试 |
| **所属 Story** | — |
| **用户场景** | — |
| **任务描述** | 测试 `scripts/backup.bat`：生成备份文件 → 删除原数据库 → 从备份恢复 → 验证数据完整性。测试备份脚本失败告警 |
| **预估 Token** | ~15k |
| **验收标准** | 备份文件生成成功；恢复后数据完整；备份失败时日志正确记录 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P0-22 |

### P7-07 数据一致性测试（归档后）
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写归档后数据一致性校验测试 |
| **技术范围** | 后端测试 |
| **所属 Story** | Story-25 |
| **用户场景** | — |
| **任务描述** | 测试：归档后尝试修改 assessment_record、approval_record、interview_record → 均返回 400；验证 PDF 档案与数据库数据一致（总分、等级、维度得分） |
| **预估 Token** | ~15k |
| **验收标准** | 归档后所有修改操作被拦截；PDF 档案数据与数据库一致 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P6-15 |

### P7-08 通知模块测试
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写通知模块完整测试 |
| **技术范围** | 后端测试 |
| **所属 Story** | 全部 |
| **用户场景** | — |
| **任务描述** | 测试通知触发点：周期启动、评分提交、审批通过、结果发布、申诉复核。验证 notifications 表正确记录、未读数正确、已读状态正确更新 |
| **预估 Token** | ~20k |
| **验收标准** | 每个关键节点通知记录正确；未读数统计正确；已读标记生效 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P7-01 |

### P7-09 操作日志审计测试
| 项目 | 内容 |
|------|------|
| **任务名称** | 编写操作日志审计测试 |
| **技术范围** | 后端测试 |
| **所属 Story** | 全部 |
| **用户场景** | — |
| **任务描述** | 测试：所有写操作（增删改）均记录 operation_logs；old_value/new_value 正确序列化；敏感操作（强制分布调整、申诉复核）变更前后值完整；操作日志不可删除 |
| **预估 Token** | ~15k |
| **验收标准** | 任意写操作后 operation_logs 新增记录；old_value/new_value JSON 正确；日志删除接口返回 403 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。 |
| **前置依赖** | P7-08 |

### P7-10 系统验收测试报告
| 项目 | 内容 |
|------|------|
| **任务名称** | 生成系统验收测试报告 |
| **技术范围** | 文档 |
| **所属 Story** | 全部 |
| **用户场景** | — |
| **任务描述** | 汇总所有测试用例执行结果：单元测试通过率、集成测试通过率、E2E 测试通过率、性能测试指标、安全测试结论。列出遗留问题（如有）和下一步计划 |
| **预估 Token** | ~10k |
| **验收标准** | 报告包含：测试用例总数、通过数、失败数、覆盖率；性能指标截图；安全测试结论 使用 `pytest` 或 `bash` 编写测试脚本，严格断言功能正确性。 |
| **前置依赖** | P7-09 |

---

## 附录 A：任务依赖关系图（关键路径）

```
P0 基础设施（22 任务）
  ├── P1 系统配置（18 任务）
  │     ├── P2 员工与组织（16 任务）
  │     │     ├── P3 考核管理（14 任务）
  │     │     │     ├── P4 评分管理（22 任务）
  │     │     │     │     ├── P5 汇总与审批（18 任务）
  │     │     │     │     │     ├── P6 发布与归档（16 任务）
  │     │     │     │     │     │     └── P7 集成验收（10 任务）
```

**关键路径**：P0 → P1 → P2 → P3 → P4 → P5 → P6 → P7  
**可并行路径**：P1 与 P2 部分重叠（P2-01 部门管理可在 P1 完成前启动）。

---

## 附录 B：Story → 任务映射表

| Story | 任务编号 | 任务数 |
|-------|---------|--------|
| Story-01 等级规则 | P1-01 ~ P1-03 | 3 |
| Story-02 维度权重 | P1-04 | 1 |
| Story-03 评价人权重 | P1-05 | 1 |
| Story-04 协作评分开关 | P1-06 | 1 |
| Story-05 KPI 模板 | P1-08 ~ P1-11 | 4 |
| Story-06 员工导入 | P2-05 ~ P2-10 | 6 |
| Story-07 部门岗位 | P2-01 ~ P2-04, P2-11 | 5 |
| Story-08 考核周期 | P3-01 ~ P3-04, P3-06 ~ P3-07 | 6 |
| Story-09 考核启动 | P3-05, P3-10 | 2 |
| Story-10 自评加载 | P4-01 ~ P4-03 | 3 |
| Story-11 自评提交 | P4-04 ~ P4-05 | 2 |
| Story-12 上级评分列表 | P4-06 ~ P4-07 | 2 |
| Story-13 上级评分表 | P4-08 ~ P4-09 | 2 |
| Story-14 上级评分提交 | P4-10 ~ P4-12 | 3 |
| Story-15 协作评分 | P4-13 ~ P4-15 | 3 |
| Story-16 加权计算 | P5-01 ~ P5-02, P5-05 | 3 |
| Story-17 强制分布 | P5-03 ~ P5-04, P5-05 | 3 |
| Story-18 审批列表 | P5-06 ~ P5-07, P5-10 ~ P5-11 | 4 |
| Story-19 审批操作 | P5-08 ~ P5-09 | 2 |
| Story-20 绩效面谈 | P5-12 ~ P5-14 | 3 |
| Story-21 结果发布 | P6-01 ~ P6-04 | 4 |
| Story-22 申诉发起 | P6-05, P6-07 | 2 |
| Story-23 申诉复核 | P6-06, P6-07 | 2 |
| Story-24 高管仪表盘 | P6-08 ~ P6-09 | 2 |
| Story-25 归档导出 | P6-10 ~ P6-13 | 4 |

---

## 附录 C：用户场景 → 任务映射表

| 场景 | 覆盖任务 | 验证方式 |
|------|---------|---------|
| 场景 1：管理员配置 | P1-01 ~ P1-07, P1-13 | P1-18 E2E |
| 场景 1.5：HR 导入员工 | P2-01 ~ P2-11 | P2-15 E2E |
| 场景 2：HR 发起考核 | P3-01 ~ P3-07, P5-05 | P3-14 E2E |
| 场景 3：员工自评 | P4-01 ~ P4-05, P6-01 ~ P6-04 | P4-21 E2E |
| 场景 4：经理评分/审批/面谈 | P4-06 ~ P4-12, P5-06 ~ P5-14 | P4-22, P5-18 E2E |
| 场景 5：协作评分 | P4-13 ~ P4-15 | P4-22 E2E |
| 场景 6：高管查看 | P6-08 ~ P6-09 | P7-01 E2E（含高管验证） |
| 场景 7：全流程（王志强） | P3-05, P4-04, P4-10, P5-02, P5-04, P5-08, P5-12, P6-10 | P7-01 E2E |
| 场景 8：全流程（孙伟+申诉） | P6-05 ~ P6-07 | P6-16 E2E |

---

## 附录 D：Token 预算汇总

| 阶段 | 任务数 | 预估总 Token | 说明 |
|------|--------|-------------|------|
| P0 基础设施 | 22 | ~400k | 架构搭建，一次性投入 |
| P1 系统配置 | 18 | ~360k | 可独立并行开发 |
| P2 员工与组织 | 16 | ~340k | 可独立并行开发 |
| P3 考核管理 | 14 | ~330k | 依赖 P1/P2 |
| P4 评分管理 | 22 | ~470k | 核心链路，任务最多 |
| P5 汇总与审批 | 18 | ~410k | 依赖 P4 |
| P6 发布与归档 | 16 | ~380k | 依赖 P5 |
| P7 集成验收 | 10 | ~170k | 最终验收 |
| **合计** | **136** | **~2,860k** | 按单任务 ≤100k 拆分 |

> **说明**：2,860k 为全部任务的预估总和。实际开发中，每个任务独立执行，单轮对话仅消耗对应任务的 Token（≤100k），不会一次性消耗全部。

---

## 附录 E：开发建议与风险提示

### 1. 并行开发策略
- **P0（基础设施）** 必须优先完成，所有后续阶段依赖它。
- **P1（系统配置）** 和 **P2（员工与组织）** 可在 P0 完成后并行开发。
- **P3（考核管理）** 需等待 P1/P2 完成（依赖配置和员工数据）。
- **P4（评分管理）** 需等待 P3 完成（依赖考核周期启动）。
- **P5/P6/P7** 按顺序串行。

### 2. 风险缓解
| 风险 | 应对措施 |
|------|---------|
| 任务拆分不够细，单轮超 100k | 按「单模型/单 API/单组件」继续拆分 |
| 前后端联调耗时 | 先定义 Pydantic Schema 作为契约，前后端按契约独立开发 |
| 状态机复杂度高 | 先写状态机单元测试，再写业务逻辑 |
| 性能不达标 | P7-02/P7-03 尽早执行，发现问题提前优化 |

### 3. 推荐开发节奏
- **第 1 周**：P0（基础设施）+ P1/P2（配置+组织）
- **第 2 周**：P3（考核管理）+ P4 前半（自评+上级评分）
- **第 3 周**：P4 后半（协作评分）+ P5（汇总+审批+面谈）
- **第 4 周**：P6（发布+归档+申诉+高管）+ P7（集成测试）
- **第 5 周**：Bug 修复 + 性能优化 + 验收

