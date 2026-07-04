import re
import sys

file_path = r"D:\cc_project\performance_evaluation_system\DEV_TODO_LIST.md"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    new_lines.append(line)

    # 检查是否是验收标准行
    if "| **验收标准** |" in line:
        # 判断任务类型：向前查找 "| **技术范围** |" 或 "| **任务名称** |"
        tech_scope = ""
        task_name = ""
        for j in range(max(0, i - 10), i):
            prev = lines[j]
            if "| **技术范围** |" in prev:
                tech_scope = prev.split("|")[2].strip().lower()
            if "| **任务名称** |" in prev:
                task_name = prev.split("|")[2].strip().lower()

        # 判断属于哪类任务
        is_frontend = any(k in task_name or k in tech_scope for k in [
            "前端", "vue", "echarts", "element plus", "pinia", "页面", "组件",
            "vitest", "dashboard", "login", "config", "list", "edit", "view",
            "selfassessment", "scoresheet", "peerreview", "approval", "interview",
            "myperformance", "reportexport", "dashboardhr", "dashboardmanager",
            "dashboardemployee", "dashboardexecutive", "organizationchart",
            "employeelist", "departmentlist", "positionlist", "kpitemplatelist",
            "cyclelist", "summarydashboard", "appeal", "interviewlist", "approvalworkbench"
        ])

        is_e2e = any(k in task_name or k in tech_scope for k in [
            "e2e", "playwright", "端到端"
        ])

        is_backend = any(k in task_name or k in tech_scope for k in [
            "后端", "api", "service", "schema", "模型", "算法", "基础设施",
            "pytest", "fastapi", "sqlalchemy", "pydantic", "orm", "jwt",
            "异常", "响应", "中间件", "数据库", "路由", "依赖", "权限",
            "单元测试", "集成测试", "安全测试", "性能测试"
        ])

        is_script = any(k in task_name or k in tech_scope for k in [
            "脚本", "bash", "batch", "bat", "备份", "重启", "目录", "配置"
        ])

        # 提取原有验收标准内容（去掉末尾的 | 和换行）
        parts = line.rstrip().split("|")
        if len(parts) >= 3:
            existing = parts[2].strip()
        else:
            existing = ""

        # 避免重复追加
        if "测试脚本" in existing or "pytest" in existing or "playwright" in existing or "curl" in existing or "bash" in existing:
            i += 1
            continue

        append = ""
        if is_e2e:
            append = " 使用 `npx playwright test --project=chromium` 执行 E2E 测试，严格断言页面元素和状态流转。"
        elif is_frontend:
            append = " 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。"
        elif is_backend:
            append = " 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。"
        elif is_script:
            append = " 使用 bash 脚本执行验证（`bash scripts/xxx.sh` 或 `cmd scripts/xxx.bat`），严格断言文件生成、命令退出码和输出内容。"
        else:
            # 兜底：看任务描述行
            desc = ""
            for j in range(max(0, i - 10), i):
                if "| **任务描述** |" in lines[j]:
                    desc = lines[j].split("|")[2].strip().lower()
                    break
            if any(k in desc for k in ["前端", "vue", "页面", "组件"]):
                append = " 使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素和交互结果。"
            elif any(k in desc for k in ["api", "接口", "后端", "数据库", "算法"]):
                append = " 使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。"
            else:
                append = " 使用 `pytest` 或 `bash` 编写测试脚本，严格断言功能正确性。"

        # 构建新行
        new_standard = existing + append
        # 替换原行
        new_lines[-1] = f"| **验收标准** | {new_standard} |\n"

    i += 1

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("SUCCESS: 所有验收标准已补充测试脚本要求")
