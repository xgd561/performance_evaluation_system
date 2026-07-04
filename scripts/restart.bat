@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set PORT=8000
set BACKEND_DIR=%~dp0..\backend

echo ==========================================
echo  Backend Restart Script
echo ==========================================
echo.

REM 1. Check port and kill process
echo [1/4] Checking port %PORT% ...
set FOUND=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT%" ^| findstr "LISTENING"') do (
    set FOUND=1
    echo        Found PID: %%a, stopping...
    taskkill /F /PID %%a >nul 2>&1
    if errorlevel 1 (
        echo        Failed to stop PID %%a
    ) else (
        echo        Stopped PID %%a
    )
)
if %FOUND%==0 (
    echo        Port %PORT% is free
)

echo.
echo [2/4] Waiting for port release...
timeout /t 2 /nobreak >nul

echo [3/4] Verifying port status...
netstat -ano | findstr ":%PORT%" | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo Warning: port %PORT% is still occupied
) else (
    echo Port %PORT% is free
)

echo.
echo [4/4] Starting backend server...
echo   Swagger UI: http://localhost:%PORT%/docs
echo   API URL:    http://localhost:%PORT%
echo.

cd /d %BACKEND_DIR%
python -m uvicorn app.main:app --port %PORT% --host 0.0.0.0

if errorlevel 1 (
    echo.
    echo Startup failed
    pause
)

endlocal
