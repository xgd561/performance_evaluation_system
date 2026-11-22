---
kind: dependency_management
name: 依赖管理：Python requirements.txt + Node package.json 双清单锁定
category: dependency_management
scope:
    - '**'
source_files:
    - backend/requirements.txt
    - backend/package.json
    - frontend/package.json
    - backend/package-lock.json
    - frontend/package-lock.json
    - docs/ACCEPTANCE_REPORT.md
    - docs/DEV_TODO_LIST.md
---

## 1. 使用的系统/工具

仓库采用**多语言、分层式**的依赖声明方式，没有统一的顶层聚合清单：
- **后端（Python/FastAPI）**：使用 `pip` + `requirements.txt` 声明运行时与测试依赖。
- **前端（Vue3 + Vite）**：使用 `npm` + `package.json` 声明运行时与开发依赖，并通过 `package-lock.json` 锁定版本。
- **后端内嵌的轻量 Node 工具**（如 Playwright）：在 `backend/package.json` 中单独声明，与前端解耦。

未使用 `poetry`、`Pipfile`、`pyproject.toml` 等现代 Python 包管理器；也未见私有 PyPI 源或 `GOPRIVATE` 类配置。所有第三方库均来自公共 PyPI / npm registry。

## 2. 关键文件

- `backend/requirements.txt` — Python 运行时与测试依赖的唯一声明入口。
- `backend/package.json` — 后端侧 Node 工具（@testing-library/jest-dom、vitest 等 devDependencies）。
- `frontend/package.json` — 前端应用依赖（vue、element-plus、axios、pinia、vite、playwright 等）。
- `backend/package-lock.json`、`frontend/package-lock.json` — npm 锁文件，用于复现确定性安装。
- `tests/test_p0_12_dependencies.py` — 针对 FastAPI 依赖注入层（`get_current_user_or_403`、`require_role`）的行为测试，属于业务依赖而非包依赖。

## 3. 架构与约定

### Python 依赖（`backend/requirements.txt`）
- 全部使用**精确版本号**（`==`），例如 `fastapi==0.111.0`、`sqlalchemy==2.0.31`、`alembic==1.13.1`、`pydantic==2.7.4`、`pytest==8.2.2`、`playwright==1.44.0` 等，避免 pip 解析时产生可变的次版本升级。
- 依赖按功能分组排列：Web 框架（fastapi、uvicorn）、ORM/迁移（sqlalchemy、alembic）、认证（python-jose、passlib）、数据处理（openpyxl）、测试（pytest、httpx、playwright）、PDF 生成（reportlab）、调度（apscheduler）。
- 通过 `python -m venv .venv` 创建虚拟环境后执行 `pip install -r requirements.txt` 安装（见 `docs/DEV_TODO_LIST.md` 中的任务描述）。

### Node 依赖（`frontend/package.json`）
- 运行时代码位于 `dependencies`，开发/构建/测试工具位于 `devDependencies`，遵循 npm 常规约定。
- 版本范围使用 `^` 语义化版本前缀（如 `"vue": "^3.4.27"`、`"element-plus": "^2.7.5"`），允许小版本自动升级；实际锁定由 `package-lock.json` 保证。
- 提供标准脚本：`dev`、`build`、`preview`、`test`、`test:unit`、`test:watch`、`test:coverage`、`test:e2e`、`test:e2e:ui`。

### 后端内嵌 Node 依赖（`backend/package.json`）
- 仅包含测试相关 devDependencies（`@testing-library/jest-dom`、`vitest`、`jsdom` 等），不包含业务运行时依赖，表明该 `package.json` 是辅助用途。

## 4. 约定与约束

- **Python 依赖必须写死到 `backend/requirements.txt`**：验收文档 `ACCEPTANCE_REPORT.md` 将“`requirements.txt` 完整，可安装”列为 P0-02 验收项，且 `DEV_TODO_LIST.md` 明确列出应包含的包集合（fastapi、uvicorn、sqlalchemy、alembic、pydantic、pyjwt、bcrypt、python-multipart、openpyxl、playwright、pytest、httpx、apscheduler）。
- **Node 依赖通过 `package.json` + `package-lock.json` 共同管理**：`frontend/package.json` 定义版本范围，`package-lock.json` 锁定具体解析结果；`backend/package.json` 作为独立作用域隔离后端 Node 工具依赖。
- **无私有源/代理配置**：未发现 `.pip.conf`、`setup.cfg`、`.npmrc`、`pnpm-workspace.yaml` 等自定义注册表配置，默认使用公共 PyPI 与 npm registry。
- **无 vendoring**：Python 依赖不随代码提交（无 `vendor/` 目录），Node 依赖通过 `node_modules/` 本地缓存但通常被忽略（根 `.gitignore` 未显示其内容）。
- **FastAPI 依赖注入与包依赖分离**：`app/core/dependencies.py` 与 `tests/test_p0_12_dependencies.py` 验证的是 FastAPI 的 `Depends` 机制（用户鉴权、角色守卫），不属于第三方包依赖管理的范畴。