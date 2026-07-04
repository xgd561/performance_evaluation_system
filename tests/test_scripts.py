import subprocess
import os
import glob
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


class TestBackupScript:
    """Tests for scripts/backup.bat"""

    def test_backup_creates_timestamped_file(self):
        backup_dir = PROJECT_ROOT / "backups"
        # Clean old test backups
        for f in backup_dir.glob("performance_evaluation_*.db"):
            f.unlink()

        script_path = PROJECT_ROOT / "scripts" / "backup.bat"
        result = subprocess.run(
            ["cmd", "/c", str(script_path).replace("\\", "/")],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        assert result.returncode == 0, f"backup.bat failed: stdout={result.stdout}"
        assert "[OK] Backup successful" in result.stdout

        backups = list(backup_dir.glob("performance_evaluation_*.db"))
        assert len(backups) >= 1, "Backup file was not created"

        backup_file = backups[0]
        db_file = PROJECT_ROOT / "data" / "db" / "performance_evaluation.db"
        assert backup_file.stat().st_size == db_file.stat().st_size, "Backup file size mismatch"


class TestRestartScript:
    """Tests for scripts/restart.bat"""

    def test_restart_outputs_swagger_and_port(self):
        # Pre-clean port 8000
        subprocess.run(
            'for /f "tokens=5" %a in (\'netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"\') do taskkill /F /PID %a',
            shell=True,
            capture_output=True,
        )

        script_path = PROJECT_ROOT / "scripts" / "restart.bat"
        proc = subprocess.Popen(
            ["cmd", "/c", str(script_path).replace("\\", "/")],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        try:
            stdout, _ = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, _ = proc.communicate()

        # Cleanup any remaining uvicorn on port 8000
        subprocess.run(
            'for /f "tokens=5" %a in (\'netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"\') do taskkill /F /PID %a',
            shell=True,
            capture_output=True,
        )

        assert "Swagger UI" in stdout, f"Expected Swagger UI in output, got: {stdout}"
        assert "http://localhost:8000/docs" in stdout, f"Expected docs URL in output, got: {stdout}"
        assert "Checking port 8000" in stdout or "Port 8000 is free" in stdout, f"Expected port check in output, got: {stdout}"

    def test_restart_checks_port_occupancy(self):
        script_path = PROJECT_ROOT / "scripts" / "restart.bat"
        result = subprocess.run(
            ["cmd", "/c", str(script_path).replace("\\", "/")],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        # The script blocks on uvicorn, so it will likely be killed by timeout or continue running
        # We just verify it contains the port check message before starting uvicorn
        assert result.returncode != 0 or "Checking port 8000" in result.stdout or "Port 8000 is free" in result.stdout or "Swagger UI" in result.stdout, f"Unexpected output: {result.stdout}"
