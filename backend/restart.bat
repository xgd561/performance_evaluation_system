@echo off
chcp 65001 >/dev/null
setlocal

set PORT=8000
set PYTHON="D:\Program Files\Python311\python.exe"
set UVICORN_ARGS=app.main:app --host 0.0.0.0 --port %PORT%

echo [%date% %time%] 开始重启后端服务...

:: 查找并终止占用端口的 Python 进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT%') do (
    echo [%date% %time%] 发现占用端口 %PORT% 的进程 PID: %%a
    taskkill /F /PID %%a >/dev/null 2>&1
    if errorlevel 1 (
        echo [%date% %time%] 终止进程 %%a 失败
    ) else (
        echo [%date% %time%] 已终止进程 %%a
    )
)

:: 额外清理可能残留的 uvicorn/python 进程
taskkill /F /IM python.exe >/dev/null 2>&1
echo [%date% %time%] 已清理残留 python 进程

:: 等待端口释放
echo [%date% %time%] 等待端口释放...
:wait_loop
netstat -ano | findstr :%PORT% >/dev/null
if not errorlevel 1 (
    timeout /t 1 /nobreak >/dev/null
    goto wait_loop
)
echo [%date% %time%] 端口 %PORT% 已释放

:: 启动新服务
start /b %PYTHON% -m uvicorn %UVICORN_ARGS%
echo [%date% %time%] 新服务已启动

:: 等待服务就绪
set RETRY=0
:health_check
timeout /t 1 /nobreak >/dev/null
%PYTHON% -c "import urllib.request; urllib.request.urlopen('http://localhost:%PORT%/api/v1/auth/login', timeout=2)" >/dev/null 2>&1
if errorlevel 1 (
    set /a RETRY+=1
    if %RETRY% lss 10 (
        echo [%date% %time%] 等待服务就绪... (%RETRY%/10)
        goto health_check
    ) else (
        echo [%date% %time%] 服务启动超时，请检查日志
        exit /b 1
    )
)

echo [%date% %time%] 服务已就绪，重启完成
endlocal
