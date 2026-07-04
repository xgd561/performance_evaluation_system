import re
import os

project_root = r"D:\cc_project\performance_evaluation_system"

# 1. 更新 backend/app/database.py
db_py_path = os.path.join(project_root, "backend", "app", "database.py")
with open(db_py_path, "r", encoding="utf-8") as f:
    content = f.read()

# 插入 os 导入和新的路径定义
old_import = "from app.models import Base\n\n"
new_import = "from app.models import Base\n\nimport os\n\n# 数据库文件统一放在项目根级 data/db/ 目录下，便于备份和运维\nDB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), \"data\", \"db\")\nos.makedirs(DB_DIR, exist_ok=True)\n"

content = content.replace(old_import, new_import)
content = content.replace(
    'SQLALCHEMY_DATABASE_URL = "sqlite:///./performance_evaluation.db"',
    "SQLALCHEMY_DATABASE_URL = f\"sqlite:///{os.path.join(DB_DIR, 'performance_evaluation.db')}\""
)

with open(db_py_path, "w", encoding="utf-8") as f:
    f.write(content)
print("[+] 更新 backend/app/database.py")

# 2. 更新 backend/clean_db.py
clean_py_path = os.path.join(project_root, "backend", "clean_db.py")
with open(clean_py_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "db_path = 'performance_evaluation.db'",
    "db_path = os.path.join('..', 'data', 'db', 'performance_evaluation.db')"
)

# 确保文件顶部有 os 导入
if "import os" not in content:
    content = content.replace("import sqlite3", "import os\nimport sqlite3")

with open(clean_py_path, "w", encoding="utf-8") as f:
    f.write(content)
print("[+] 更新 backend/clean_db.py")

# 3. 更新 scripts/init_db.py
init_py_path = os.path.join(project_root, "scripts", "init_db.py")
with open(init_py_path, "r", encoding="utf-8") as f:
    content = f.read()

# 确保 data/db 目录存在
old_main = "def main():\n    print(\"=\" * 50)"
new_main = """def main():\n    # 确保数据库目录存在\n    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), \"data\", \"db\"), exist_ok=True)\n    print(\"=\" * 50)"""

content = content.replace(old_main, new_main)

with open(init_py_path, "w", encoding="utf-8") as f:
    f.write(content)
print("[+] 更新 scripts/init_db.py")

print("\n完成。数据库路径已统一指向 data/db/performance_evaluation.db")
