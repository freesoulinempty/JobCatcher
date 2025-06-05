#!/bin/bash
# JobCatcher 服务停止脚本 / JobCatcher Service Stop Script

echo "🛑 JobCatcher 服务停止脚本 / JobCatcher Service Stop Script"
echo "=============================================================="

# 项目根目录 / Project root directory
PROJECT_ROOT="/home/devbox/project"
LOGS_DIR="$PROJECT_ROOT/logs"

# 加载.env环境变量 / Load .env environment variables
ENV_FILE="$PROJECT_ROOT/JobCatcher/backend/.env"
if [ -f "$ENV_FILE" ]; then
    set -a  # 自动导出所有变量 / Automatically export all variables
    source "$ENV_FILE"
    set +a  # 关闭自动导出 / Turn off automatic export
fi

# 设置端口变量（从.env文件获取或使用默认值）/ Set port variables (from .env file or use defaults)
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-7860}

# 检查PID文件并停止服务 / Check PID files and stop services
stop_service() {
    local service_name=$1
    local pid_file="$LOGS_DIR/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        echo "🔍 检查 $service_name 服务 (PID: $pid) / Checking $service_name service (PID: $pid)"
        
        if kill -0 "$pid" 2>/dev/null; then
            echo "  - 正在停止 $service_name 服务 / Stopping $service_name service..."
            kill "$pid"
            sleep 2
            
            # 如果还在运行，强制杀死 / If still running, force kill
            if kill -0 "$pid" 2>/dev/null; then
                echo "  - 强制停止 $service_name 服务 / Force stopping $service_name service..."
                kill -9 "$pid"
            fi
            
            echo "  ✅ $service_name 服务已停止 / $service_name service stopped"
        else
            echo "  ⚠️  $service_name 服务未运行 / $service_name service not running"
        fi
        
        # 删除PID文件 / Remove PID file
        rm -f "$pid_file"
    else
        echo "⚠️  未找到 $service_name PID文件 / $service_name PID file not found"
    fi
}

# 停止后端服务 / Stop backend service
stop_service "backend"

# 停止前端服务 / Stop frontend service
stop_service "frontend"

# 清理端口 / Clean up ports
echo "🧹 清理端口占用 / Cleaning up port occupation..."

# 杀死可能占用后端端口的进程 / Kill processes that might occupy backend port
if lsof -i :$BACKEND_PORT >/dev/null 2>&1; then
    echo "  - 清理端口$BACKEND_PORT / Cleaning up port $BACKEND_PORT..."
    fuser -k $BACKEND_PORT/tcp >/dev/null 2>&1 || true
fi

# 杀死可能占用前端端口的进程 / Kill processes that might occupy frontend port
if lsof -i :$FRONTEND_PORT >/dev/null 2>&1; then
    echo "  - 清理端口$FRONTEND_PORT / Cleaning up port $FRONTEND_PORT..."
    fuser -k $FRONTEND_PORT/tcp >/dev/null 2>&1 || true
fi

# 杀死可能残留的uvicorn和http.server进程 / Kill possible remaining uvicorn and http.server processes
echo "🧹 清理残留进程 / Cleaning up remaining processes..."
pkill -f "uvicorn.*app.main:app" 2>/dev/null || true
pkill -f "http.server.*$FRONTEND_PORT" 2>/dev/null || true

echo ""
echo "✅ JobCatcher 服务已全部停止 / All JobCatcher services stopped"
echo "📝 日志文件保留在 $LOGS_DIR / Log files retained in $LOGS_DIR" 