---
kind: build_system
name: 构建与本地开发流水线（Vite + Uvicorn + pytest）
category: build_system
scope:
    - '**'
source_files:
    - backend/requirements.txt
    - frontend/package.json
    - frontend/vite.config.js
    - backend/run_tests.bat
    - backend/restart.sh
    - scripts/restart.bat
    - restart-services.bat
    - scripts/init_db.py
    - scripts/verify_p0_01.sh
---

## 1. 构建系统与工具链

仓库采用**前后端分离、各自独立构建**的轻量级方案，没有 Makefile / Dockerfile / CI YAML：

- **后端 (Python/FastAPI)**：依赖通过 `backend/requirements.txt` 锁定版本（fastapi==0.111.0, uvicorn==0.30.0, sqlalchemy==2.0.31, alembic==1.13.1, pydantic==2.7.4 等），运行由 `uvicorn app.main:app` 驱动。
- **前端 (Vue3/Vite)**：依赖通过 `frontend/package.json` 管理，构建命令为 `vite build`，开发服务器 `vite dev`（端口 3000，代理 `/api` → `http://localhost:8014`）。
- **测试**：后端使用 `pytest`（`backend/run_tests.bat` 封装），前端使用 `vitest run`（单元测试）+ `playwright test`（E2E，见 `frontend/package.json` scripts）。根目录 `tests/` 下还有一套跨模块的 pytest 用例（依赖校验、数据库模型、脚本验证等）。
- **无容器化/CI**：仓库中未发现 `Dockerfile`、`.github/workflows`、`Jenkinsfile`、`Makefile`、`pyproject.toml`、`setup.py` 等文件；所有构建与启动均由 `.bat` / `.sh` 脚本完成，面向 Windows Git Bash 本地开发。

## 2. 关键文件

| 用途 | 文件 |
|---|---|
| Python 依赖锁定 | `backend/requirements.txt` |
| 前端依赖与脚本入口 | `frontend/package.json` |
| 前端 Vite 配置（含 API 代理） | `frontend/vite.config.js` |
| 后端测试运行器 | `backend/run_tests.bat` |
| 后端重启（Git Bash） | `backend/restart.sh` |
| 后端重启（Windows cmd） | `scripts/restart.bat` |
| 前后端一键启动 | `restart-services.bat` |
| 数据库初始化 & 种子数据 | `scripts/init_db.py` |
| 项目结构校验 | `scripts/verify_p0_01.sh` |
| 根入口（FastAPI 应用装配） | `main.py` |

## 3. 架构与约定

### 3.1 启动流程

1. **数据库初始化**：`python ../scripts/init_db.py`（从 `scripts/` 目录执行，自动 `cd backend` 并注入 `sys.path`），负责创建表、默认部门/岗位、系统配置、7 个演示账号，并在 `data/db/performance_evaluation.db` 落库。
2. **后端服务**：`python -m uvicorn app.main:app --host 0.0.0.0 --port 8014`（或 8000，取决于脚本），`restart-services.bat` 同时拉起后端与前端两个 cmd 窗口。
3. **前端服务**：`npm run dev`，Vite 在 3000 端口提供静态资源，并通过 proxy 将 `/api/*` 转发到后端 8014 端口。
4. **健康检查**：`backend/restart.sh` 启动后轮询 `http://localhost:8000/api/v1/auth/login`，HTTP 200/405 视为就绪，最多重试 10 秒。

### 3.2 目录结构约束

`scripts/verify_p0_01.sh` 显式断言以下目录必须存在，否则退出码非 0：

```
backend/app/{api,core,db,models,schemas,crud,services,utils}
backend/.venv
frontend/src/{views,components,api,stores,router,composables,types,assets}
scripts/
tests/
data/db/
logs/
uploads/
```

该脚本以 `set -euo pipefail` 运行，任何缺失都会导致整体失败，是本项目对目录结构的**硬性约束**。

### 3.3 测试组织

- 后端单测位于 `backend/tests/test_*.py`，通过 `backend/run_tests.bat [module_name]` 按模块名筛选（内部拼接 `tests/test_{name}.py`）。
- 前端单测位于 `frontend/tests/**`，E2E 位于 `frontend/tests/e2e/**`，分别由 `npm run test` 和 `npm run test:e2e` 触发。
- 根级 `tests/` 包含跨模块验收用例（`test_p0_02_deps.py`、`test_p0_04_database.py` 等）以及 `scripts/` 下的通用 fixture 与辅助函数。

### 3.4 端口约定

| 服务 | 默认端口 | 来源 |
|---|---:|---|
| 后端 API | 8014 | `restart-services.bat` 中 `BACKEND_PORT=8014` |
| 前端 Dev Server | 3000 | `frontend/vite.config.js` server.port |
| 旧版脚本兼容端口 | 8000 | `scripts/restart.bat`、`backend/restart.sh` |

## 4. 约定与约束

- **依赖锁定**：后端使用 `requirements.txt` 精确 pin 版本（如 `fastapi==0.111.0`），前端使用 npm lockfile（`package-lock.json`）。
- **无全局构建编排**：不存在统一的 `build` 任务；前后端分别用各自的包管理器命令启动/构建。
- **Windows 优先**：主要运维脚本为 `.bat`（`restart-services.bat`、`scripts/restart.bat`、`backend/run_tests.bat`），仅少数脚本（`init_db.py`、`verify_p0_01.sh`、`backend/restart.sh`）使用 bash/python，且注释明确标注“本机仅用于开发调测，无其他 Python 进程”。
- **目录结构强制校验**：`scripts/verify_p0_01.sh` 定义了项目骨架清单，任何缺失都会使校验失败（exit 1）。
- **数据库路径固定**：初始化脚本硬编码 `data/db/performance_evaluation.db`，并通过 `os.makedirs(..., exist_ok=True)` 确保目录存在。
- **无容器化/CI**：仓库未包含 Dockerfile、GitHub Actions、Jenkins 或其他持续集成配置；部署与发布流程未在代码中体现。