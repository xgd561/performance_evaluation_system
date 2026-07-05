#!/usr/bin/env bash
# 后端重启脚本（Windows Git Bash 环境）
# 说明：本机仅用于开发调测，无其他 Python 进程，可直接清理所有残留

PORT=8000
HOST=0.0.0.0
PYTHON="python"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始重启后端服务..."

# 直接清理所有 Python 进程（本机无其他 Python 工具，大胆杀）
taskkill //F //IM python.exe 2>/dev/null &>/dev/null
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 已清理所有 python 进程"

# 等 2 秒让 Windows 回收端口和句柄
sleep 2

# 切换到后端目录
cd "$SCRIPT_DIR" || { echo "目录错误"; exit 1; }

# 启动新服务
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 启动新服务..."
nohup $PYTHON -m uvicorn app.main:app --host "$HOST" --port "$PORT" > uvicorn.log 2>&1 &
NEW_PID=$!
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 新服务已启动 (PID=$NEW_PID)"

# 健康检查（最多 10 秒）
RETRY=0
while [ $RETRY -lt 10 ]; do
    sleep 1
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/api/v1/auth/login 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "405" ] || [ "$HTTP_CODE" = "200" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 服务已就绪 (HTTP $HTTP_CODE)，重启完成"
        exit 0
    fi
    RETRY=$((RETRY+1))
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 等待就绪... ($RETRY/10)"
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 启动超时，请检查 uvicorn.log"
exit 1
