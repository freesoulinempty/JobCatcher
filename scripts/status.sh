#!/bin/bash
# JobCatcher 服务状态检查脚本 / JobCatcher Service Status Check Script

echo "📊 JobCatcher 服务状态检查 / JobCatcher Service Status Check"
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

# 检查服务状态 / Check service status
check_service_status() {
    local service_name=$1
    local port=$2
    local pid_file="$LOGS_DIR/${service_name}.pid"
    
    echo "🔍 检查 $service_name 服务状态 / Checking $service_name service status"
    
    # 检查PID文件 / Check PID file
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        echo "  📋 PID文件存在 / PID file exists: $pid"
        
        # 检查进程是否运行 / Check if process is running
        if kill -0 "$pid" 2>/dev/null; then
            echo "  ✅ 进程运行中 / Process running (PID: $pid)"
            
            # 检查端口是否监听 / Check if port is listening
            if netstat -tulpn | grep ":$port " >/dev/null 2>&1; then
                echo "  ✅ 端口监听中 / Port listening ($port)"
                
                # 测试服务可访问性 / Test service accessibility
                if [ "$service_name" = "backend" ]; then
                    if curl -s http://localhost:$port/ >/dev/null 2>&1 || curl -s http://localhost:$port/health >/dev/null 2>&1; then
                        echo "  ✅ 服务可访问 / Service accessible"
                        return 0
                    else
                        echo "  ⚠️  服务无法访问 / Service not accessible"
                        return 1
                    fi
                elif [ "$service_name" = "frontend" ]; then
                    if curl -s http://localhost:$port/ >/dev/null 2>&1; then
                        echo "  ✅ 服务可访问 / Service accessible"
                        return 0
                    else
                        echo "  ⚠️  服务无法访问 / Service not accessible"
                        return 1
                    fi
                fi
            else
                echo "  ❌ 端口未监听 / Port not listening ($port)"
                return 1
            fi
        else
            echo "  ❌ 进程未运行 / Process not running"
            # 清理无效PID文件 / Clean up invalid PID file
            rm -f "$pid_file"
            return 1
        fi
    else
        echo "  ❌ PID文件不存在 / PID file not found"
        
        # 检查端口是否被其他进程占用 / Check if port is occupied by other processes
        if netstat -tulpn | grep ":$port " >/dev/null 2>&1; then
            echo "  ⚠️  端口被其他进程占用 / Port occupied by other process"
            netstat -tulpn | grep ":$port "
        fi
        return 1
    fi
}

# 检查后端服务 / Check backend service
echo ""
if check_service_status "backend" "$BACKEND_PORT"; then
    BACKEND_STATUS="✅ 运行中 / Running"
else
    BACKEND_STATUS="❌ 未运行 / Not Running"
fi

echo ""
# 检查前端服务 / Check frontend service
if check_service_status "frontend" "$FRONTEND_PORT"; then
    FRONTEND_STATUS="✅ 运行中 / Running"
else
    FRONTEND_STATUS="❌ 未运行 / Not Running"
fi

# 显示汇总状态 / Show summary status
echo ""
echo "📋 服务状态汇总 / Service Status Summary"
echo "=============================================================="
echo "🔧 后端服务 / Backend Service:  $BACKEND_STATUS"
echo "🌐 前端服务 / Frontend Service: $FRONTEND_STATUS"

# 显示服务地址 / Show service URLs
echo ""
echo "🌐 服务地址 / Service URLs:"
echo "  - 后端API / Backend API: http://localhost:$BACKEND_PORT"
echo "  - 前端界面 / Frontend UI: http://localhost:$FRONTEND_PORT"

# 显示日志文件信息 / Show log file information
echo ""
echo "📝 日志文件 / Log Files:"
if [ -d "$LOGS_DIR" ]; then
    echo "  - 日志目录 / Logs directory: $LOGS_DIR"
    
    for log_file in backend.log backend-error.log frontend.log frontend-error.log; do
        if [ -f "$LOGS_DIR/$log_file" ]; then
            size=$(du -h "$LOGS_DIR/$log_file" | cut -f1)
            echo "  - $log_file: $size"
        fi
    done
else
    echo "  ⚠️  日志目录不存在 / Logs directory not found"
fi

# 显示最近的错误日志 / Show recent error logs
echo ""
echo "🔍 最近错误检查 / Recent Error Check:"

if [ -f "$LOGS_DIR/backend-error.log" ] && [ -s "$LOGS_DIR/backend-error.log" ]; then
    echo "⚠️  后端有错误日志 / Backend has error logs:"
    tail -3 "$LOGS_DIR/backend-error.log" | sed 's/^/  /'
fi

if [ -f "$LOGS_DIR/frontend-error.log" ] && [ -s "$LOGS_DIR/frontend-error.log" ]; then
    echo "⚠️  前端有错误日志 / Frontend has error logs:"
    tail -3 "$LOGS_DIR/frontend-error.log" | sed 's/^/  /'
fi

# 显示系统资源使用情况 / Show system resource usage
echo ""
echo "💻 系统资源 / System Resources:"
echo "  - 内存使用 / Memory usage: $(free -h | awk 'NR==2{print $3"/"$2" ("$3/$2*100"%)"}')"
echo "  - 磁盘使用 / Disk usage: $(df -h / | awk 'NR==2{print $3"/"$2" ("$5")"}')"

# 提供操作建议 / Provide operation suggestions
echo ""
echo "🛠️  操作建议 / Operation Suggestions:"
if [[ "$BACKEND_STATUS" == *"未运行"* ]] || [[ "$FRONTEND_STATUS" == *"未运行"* ]]; then
    echo "  启动服务 / Start services: bash JobCatcher/scripts/startup.sh"
fi
echo "  停止服务 / Stop services: bash JobCatcher/scripts/stop-services.sh"
echo "  查看日志 / View logs: tail -f logs/backend.log" 