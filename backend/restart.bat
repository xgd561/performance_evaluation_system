@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set PORT=8000

echo ==========================================
echo  绩效考核系统后端重启脚本
echo ==========================================
echo.

REM 查找并停止占用端口的进程
echo [1/3] 正在查找占用端口 %PORT% 的进程...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT%" ^| findstr "LISTENING"') do (
    echo        发现进程 PID: %%a，正在停止...
    taskkill /F /PID %%a >nul 2>&1
    if errorlevel 1 (
        echo        ⚠ 无法停止 PID %%a（可能权限不足或进程已退出）
    ) else (
        echo        ✓ 已停止 PID %%a
    )
)

echo.
echo [2/3] 等待端口释放...
timeout /t 2 /nobreak >nul

REM 检查端口是否仍被占用
netstat -ano | findstr ":%PORT%" | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo ⚠ 警告：端口 %PORT% 仍被占用，可能存在僵尸进程
    echo   建议：打开任务管理器手动结束 python.exe 进程
    echo.
)

echo [3/3] 启动后端服务...
echo   命令: python -m uvicorn app.main:app --port %PORT% --host 0.0.0.0
echo.
echo ==========================================
python -m uvicorn app.main:app --port %PORT% --host 0.0.0.0

REM 如果 python 命令失败，暂停显示错误
if errorlevel 1 (
    echo.
    echo ❌ 启动失败，请检查错误信息
    pause
)

endlocal
