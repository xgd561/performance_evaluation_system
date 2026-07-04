@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set DB_FILE=%~dp0..\data\db\performance_evaluation.db
set BACKUP_DIR=%~dp0..\backups

for /f "usebackq delims=" %%a in (`powershell -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"`) do set TIMESTAMP=%%a
set BACKUP_FILE=%BACKUP_DIR%\performance_evaluation_%TIMESTAMP%.db

echo ==========================================
echo  Database Backup Script
echo ==========================================
echo.

if not exist "%DB_FILE%" (
    echo [FAIL] Database file not found: %DB_FILE%
    exit /b 1
)

if not exist "%BACKUP_DIR%" (
    echo [INFO] Creating backup directory: %BACKUP_DIR%
    mkdir "%BACKUP_DIR%"
)

echo [1/2] Source: %DB_FILE%
echo [2/2] Backup: %BACKUP_FILE%

copy "%DB_FILE%" "%BACKUP_FILE%" >nul
if errorlevel 1 (
    echo [FAIL] Backup failed
    exit /b 1
)

echo [OK] Backup successful
for %%F in ("%BACKUP_FILE%") do echo        Size: %%~zF bytes

endlocal
exit /b 0
