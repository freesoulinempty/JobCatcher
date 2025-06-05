#!/bin/bash
# JobCatcher 服务启动脚本 / JobCatcher Service Startup Script
# 支持代码热重载和开机自启动 / Supports code hot reload and auto-startup

set -e  # 错误时退出 / Exit on error

echo "🚀 JobCatcher 服务启动脚本 / JobCatcher Service Startup Script"
echo "支持代码热重载和后台运行 / Supports code hot reload and background execution"
echo "=============================================================="

# 项目根目录 / Project root directory
PROJECT_ROOT="/home/devbox/project"
BACKEND_DIR="$PROJECT_ROOT/JobCatcher/backend"
FRONTEND_DIR="$PROJECT_ROOT/JobCatcher/frontend"
LOGS_DIR="$PROJECT_ROOT/logs"

# 创建日志目录 / Create logs directory
mkdir -p "$LOGS_DIR"

echo "📁 项目目录 / Project Directory: $PROJECT_ROOT"
echo "📁 后端目录 / Backend Directory: $BACKEND_DIR"
echo "📁 前端目录 / Frontend Directory: $FRONTEND_DIR"
echo "📁 日志目录 / Logs Directory: $LOGS_DIR"

# 检查虚拟环境 / Check virtual environment
if [ ! -f "$PROJECT_ROOT/bin/activate" ]; then
    echo "❌ 虚拟环境不存在 / Virtual environment not found: $PROJECT_ROOT/bin/activate"
    exit 1
fi

# 检查目录是否存在 / Check if directories exist
if [ ! -d "$BACKEND_DIR" ]; then
    echo "❌ 后端目录不存在 / Backend directory not found: $BACKEND_DIR"
    exit 1
fi

if [ ! -d "$FRONTEND_DIR" ]; then
    echo "❌ 前端目录不存在 / Frontend directory not found: $FRONTEND_DIR"
    exit 1
fi

# 检查端口占用 / Check port occupation
check_port() {
    local port=$1
    local service_name=$2
    
    if lsof -i :$port >/dev/null 2>&1; then
        echo "⚠️  端口 $port 被占用，正在清理 / Port $port is occupied, cleaning up..."
        fuser -k $port/tcp >/dev/null 2>&1 || true
        sleep 2
    fi
}

# 设置端口变量（从.env文件获取或使用默认值）/ Set port variables (from .env file or use defaults)
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-7860}

echo "🔍 检查端口占用 / Checking port occupation..."
check_port $BACKEND_PORT "后端服务 / Backend service"
check_port $FRONTEND_PORT "前端服务 / Frontend service"

# 设置环境变量 / Set environment variables
export PYTHONPATH="$BACKEND_DIR:$PYTHONPATH"

# 加载.env环境变量 / Load .env environment variables
ENV_FILE="$BACKEND_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    echo "📋 加载环境变量配置 / Loading environment variables from .env..."
    set -a  # 自动导出所有变量 / Automatically export all variables
    source "$ENV_FILE"
    set +a  # 关闭自动导出 / Turn off automatic export
    echo "✅ 环境变量加载成功 / Environment variables loaded successfully"
else
    echo "⚠️  未找到.env文件 / .env file not found: $ENV_FILE"
    echo "  使用默认配置 / Using default configuration"
fi

# 启动后端服务 / Start backend service
echo "🚀 启动后端服务 / Starting backend service..."
cd "$BACKEND_DIR"

# 激活虚拟环境并启动后端 / Activate virtual environment and start backend
source "$PROJECT_ROOT/bin/activate"

# 检查依赖 / Check dependencies
python -c "import fastapi, uvicorn" 2>/dev/null || {
    echo "❌ 后端依赖缺失 / Backend dependencies missing"
    exit 1
}

# 后台启动后端服务（支持热重载）/ Start backend service in background (with hot reload)
echo "🚀 启动后端服务（支持热重载）/ Starting backend service (with hot reload)"
echo "📝 代码修改后会自动重启 / Service will auto-restart when code changes"

nohup python -m uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT \
    --reload --reload-dir "$BACKEND_DIR/app" \
    > "$LOGS_DIR/backend.log" 2> "$LOGS_DIR/backend-error.log" &

BACKEND_PID=$!
echo "✅ 后端服务已启动 / Backend service started (PID: $BACKEND_PID)"

# 保存后端PID / Save backend PID
echo $BACKEND_PID > "$LOGS_DIR/backend.pid"

# 等待后端启动 / Wait for backend to start
echo "⏳ 等待后端服务启动 / Waiting for backend service to start..."
sleep 5

# 检查后端服务状态 / Check backend service status
if kill -0 $BACKEND_PID 2>/dev/null; then
    echo "✅ 后端服务运行正常 / Backend service running normally"
else
    echo "❌ 后端服务启动失败 / Backend service failed to start"
    cat "$LOGS_DIR/backend-error.log"
    exit 1
fi

# 启动前端服务 / Start frontend service
echo "🌐 启动前端服务 / Starting frontend service..."
cd "$FRONTEND_DIR"

# 检查前端文件 / Check frontend files
if [ ! -f "index.html" ]; then
    echo "❌ 前端文件不存在 / Frontend files not found"
    exit 1
fi

# 后台启动前端服务 / Start frontend service in background
nohup python3 -m http.server $FRONTEND_PORT \
    > "$LOGS_DIR/frontend.log" 2> "$LOGS_DIR/frontend-error.log" &

FRONTEND_PID=$!
echo "✅ 前端服务已启动 / Frontend service started (PID: $FRONTEND_PID)"

# 保存前端PID / Save frontend PID
echo $FRONTEND_PID > "$LOGS_DIR/frontend.pid"

# 等待前端启动 / Wait for frontend to start
echo "⏳ 等待前端服务启动 / Waiting for frontend service to start..."
sleep 3

# 检查前端服务状态 / Check frontend service status
if kill -0 $FRONTEND_PID 2>/dev/null; then
    echo "✅ 前端服务运行正常 / Frontend service running normally"
else
    echo "❌ 前端服务启动失败 / Frontend service failed to start"
    cat "$LOGS_DIR/frontend-error.log"
    exit 1
fi

# 测试服务可用性 / Test service availability
echo "🧪 测试服务可用性 / Testing service availability..."

# 测试后端 / Test backend
if curl -s http://localhost:$BACKEND_PORT/health >/dev/null 2>&1 || curl -s http://localhost:$BACKEND_PORT/ >/dev/null 2>&1; then
    echo "✅ 后端服务可访问 / Backend service accessible"
else
    echo "⚠️  后端服务可能未完全启动 / Backend service may not be fully started"
fi

# 测试前端 / Test frontend
if curl -s http://localhost:$FRONTEND_PORT/ >/dev/null 2>&1; then
    echo "✅ 前端服务可访问 / Frontend service accessible"
else
    echo "⚠️  前端服务可能未完全启动 / Frontend service may not be fully started"
fi

# 显示服务信息 / Show service information
echo ""
echo "🎉 JobCatcher 服务启动完成！ / JobCatcher services started successfully!"
echo "=============================================================="
echo "🌐 服务地址 / Service URLs:"
echo "  - 后端API / Backend API: http://localhost:$BACKEND_PORT"
echo "  - 前端界面 / Frontend UI: http://localhost:$FRONTEND_PORT"
echo ""
echo "📊 进程信息 / Process Information:"
echo "  - 后端PID / Backend PID: $BACKEND_PID"
echo "  - 前端PID / Frontend PID: $FRONTEND_PID"
echo ""
echo "📝 日志文件 / Log Files:"
echo "  - 后端日志 / Backend logs: $LOGS_DIR/backend.log"
echo "  - 后端错误 / Backend errors: $LOGS_DIR/backend-error.log"
echo "  - 前端日志 / Frontend logs: $LOGS_DIR/frontend.log"
echo "  - 前端错误 / Frontend errors: $LOGS_DIR/frontend-error.log"
echo ""
echo "🛑 停止服务 / Stop Services:"
echo "  bash JobCatcher/scripts/stop-services.sh"
echo ""
echo "📊 查看状态 / Check Status:"
echo "  bash JobCatcher/scripts/status.sh" 