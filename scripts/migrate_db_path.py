#!/usr/bin/env python3
"""
一键更新数据库路径脚本
将 SQLite 数据库从 backend/ 迁移到 data/db/
"""
import os
import shutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLD_DB_PATH = os.path.join(PROJECT_ROOT, "backend", "performance_evaluation.db")
NEW_DB_DIR = os.path.join(PROJECT_ROOT, "data", "db")
NEW_DB_PATH = os.path.join(NEW_DB_DIR, "performance_evaluation.db")

def migrate_database():
    os.makedirs(NEW_DB_DIR, exist_ok=True)

    if os.path.exists(OLD_DB_PATH) and not os.path.exists(NEW_DB_PATH):
        shutil.move(OLD_DB_PATH, NEW_DB_PATH)
        print(f"[+] 数据库已迁移: {OLD_DB_PATH} -> {NEW_DB_PATH}")
    elif os.path.exists(NEW_DB_PATH):
        print(f"[~] 数据库已在新位置: {NEW_DB_PATH}")
    else:
        print(f"[*] 新位置已就绪，等待创建: {NEW_DB_PATH}")

if __name__ == "__main__":
    migrate_database()
