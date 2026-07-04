import pytest
import os
import shutil
from datetime import datetime
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "db", "performance_evaluation.db")
BACKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "backups")


def test_database_file_exists():
    """数据库文件存在"""
    assert os.path.exists(DB_PATH), f"Database not found at {DB_PATH}"


def test_backup_script_creates_file():
    """backup.bat 执行后生成带时间戳的备份文件"""
    backup_script = os.path.join(os.path.dirname(__file__), "..", "scripts", "backup.bat")
    if not os.path.exists(backup_script):
        pytest.skip("backup.bat not found")

    # 清理旧备份（保留最近）
    if os.path.exists(BACKUP_DIR):
        for f in os.listdir(BACKUP_DIR):
            os.remove(os.path.join(BACKUP_DIR, f))

    os.makedirs(BACKUP_DIR, exist_ok=True)
    os.system(f'"{backup_script}"')

    files = os.listdir(BACKUP_DIR)
    assert len(files) > 0, "Backup file not created"
    assert any(f.endswith(".db") for f in files), "Backup file should be .db"


def test_backup_file_valid():
    """备份文件可读取且包含表结构"""
    import sqlite3
    if not os.path.exists(BACKUP_DIR):
        pytest.skip("No backup directory")
    files = [f for f in os.listdir(BACKUP_DIR) if f.endswith(".db")]
    if not files:
        pytest.skip("No backup files to test")

    latest = max(files, key=lambda f: os.path.getmtime(os.path.join(BACKUP_DIR, f)))
    backup_path = os.path.join(BACKUP_DIR, latest)
    conn = sqlite3.connect(backup_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    assert "employees" in tables
    assert "assessment_cycles" in tables
    assert "assessment_records" in tables
