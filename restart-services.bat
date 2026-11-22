@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 配置
set BACKEND_PORT=8000
set FRONTEND_PORT=3000
set BACKEND_DIR=D:\cc_project\performance_evaluation_system\backend
set FRONTEND_DIR=D:\cc_project\performance_evaluation_system\frontend

echo ========================================
echo  绩效考核系统 - 服务启动脚本
echo ========================================

:: 1. 清理后端端口占用
echo [1/4] 检查后端端口 %BACKEND_PORT% ...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%BACKEND_PORT% ^| findstr LISTENING') do (
    echo         发现进程 PID: %%a 占用端口 %BACKEND_PORT%
    taskkill /F /PID %%a >nul 2>&1
    if !errorlevel! equ 0 (
        echo         已终止进程 %%a
    ) else (
        echo         无法终止进程 %%a (可能需要管理员权限)
    )
)

:: 2. 清理前端端口占用
echo [2/4] 检查前端端口 %FRONTEND_PORT% ...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%FRONTEND_PORT% ^| findstr LISTENING') do (
    echo         发现进程 PID: %%a 占用端口 %FRONTEND_PORT%
    taskkill /F /PID %%a >nul 2>&1
    if !errorlevel! equ 0 (
        echo         已终止进程 %%a
    ) else (
        echo         无法终止进程 %%a (可能需要管理员权限)
    )
)

:: 3. 启动后端
echo [3/4] 启动后端服务 (端口 %BACKEND_PORT%) ...
cd /d %BACKEND_DIR%
start "Backend Server" cmd /k "python -m uvicorn app.main:app --reload --host 0.0.0.0 --port %BACKEND_PORT%"
timeout /t 3 /nobreak >nul

:: 4. 启动前端
echo [4/4] 启动前端服务 (端口 %FRONTEND_PORT%) ...
cd /d %FRONTEND_DIR%
start "Frontend Server" cmd /k "npm run dev"
timeout /t 3 /nobreak >nul

echo ========================================
echo  启动完成!
echo  后端地址: http://localhost:%BACKEND_PORT%
echo  前端地址: http://localhost:%FRONTEND_PORT%
echo ========================================

pause
