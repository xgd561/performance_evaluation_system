import re

file_path = r"D:\cc_project\performance_evaluation_system\DEV_TODO_LIST.md"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
changed = 0
for i, line in enumerate(lines):
    new_lines.append(line)

    if "| **验收标准** |" not in line:
        continue

    # 向前查找技术范围
    tech_scope = ""
    for j in range(max(0, i - 10), i):
        if "| **技术范围** |" in lines[j]:
            parts = lines[j].split("|")
            if len(parts) >= 3:
                tech_scope = parts[2].strip()
            break

    # 修正规则：技术范围明确是"后端"的，若误标为 playwright 则改为 pytest
    if "后端" in tech_scope or "运维" in tech_scope or "脚本" in tech_scope or "配置文件" in tech_scope:
        if "npx playwright" in line:
            new_line = line.replace(
                "使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。",
                "使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。"
            )
            new_lines[-1] = new_line
            changed += 1
            print(f"Fixed line {i+1}: {tech_scope}")

    # 修正规则：技术范围明确是"前端"的，若误标为 pytest 则改为 playwright
    elif "前端" in tech_scope or "E2E" in tech_scope:
        if "pytest" in line and "FastAPI" in line:
            new_line = line.replace(
                "使用 `pytest` 编写测试脚本，基于 FastAPI TestClient 进行接口测试，严格断言状态码、响应结构和数据正确性。",
                "使用 `npx playwright test --project=chromium` 进行页面校验测试，严格断言 DOM 元素、表单值、状态提示。"
            )
            new_lines[-1] = new_line
            changed += 1
            print(f"Fixed line {i+1}: {tech_scope}")

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print(f"\nTotal fixed: {changed}")
