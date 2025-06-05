# JobCatcher 服务使用说明 / JobCatcher Service Usage Guide

## 🚀 快速开始 / Quick Start

### 启动服务 / Start Services
```bash
bash JobCatcher/scripts/startup.sh
```

### 停止服务 / Stop Services  
```bash
bash JobCatcher/scripts/stop-services.sh
```

### 查看状态 / Check Status
```bash
bash JobCatcher/scripts/status.sh
```

## ✨ 核心特性 / Core Features

- ✅ **代码热重载** / Code Hot Reload：代码修改后自动重启生效
- ✅ **后台运行** / Background Execution：不阻塞终端，适合长期运行
- ✅ **开机自启动** / Auto Startup：支持系统重启后自动启动服务
- ✅ **智能端口管理** / Smart Port Management：自动检查和清理端口占用
- ✅ **环境变量自动加载** / Auto Environment Loading：自动加载.env配置文件

## 🔧 服务管理 / Service Management

### 基本操作 / Basic Operations
```bash
# 启动服务（支持热重载）/ Start services (with hot reload)
bash JobCatcher/scripts/startup.sh

# 停止所有服务 / Stop all services
bash JobCatcher/scripts/stop-services.sh

# 检查服务状态 / Check service status
bash JobCatcher/scripts/status.sh
```

### 开机自启动配置 / Auto-startup Configuration
```bash
# 配置开机自启动 / Configure auto-startup
bash JobCatcher/scripts/auto-startup.sh

# 启用自启动 / Enable auto-startup
bash JobCatcher/scripts/enable-auto-startup.sh

# 禁用自启动 / Disable auto-startup
bash JobCatcher/scripts/disable-auto-startup.sh
```

## 🌐 服务访问 / Service Access

- **后端API** / Backend API: http://localhost:8000
- **前端界面** / Frontend UI: http://localhost:7860

## 📝 日志查看 / Log Viewing

```bash
# 查看后端实时日志 / View backend real-time logs
tail -f logs/backend.log

# 查看后端错误日志 / View backend error logs  
tail -f logs/backend-error.log

# 查看前端日志 / View frontend logs
tail -f logs/frontend.log
```

## 🔄 代码热重载说明 / Code Hot Reload

- **监控范围** / Monitor Scope：`JobCatcher/backend/app/` 目录下的所有Python文件
- **生效时间** / Effect Time：文件保存后1-2秒内自动重启
- **支持文件类型** / Supported File Types：`.py` Python源代码文件
- **重启方式** / Restart Method：仅重启后端服务进程，前端保持运行

## ⚠️ 注意事项 / Important Notes

1. **环境变量配置** / Environment Configuration
   - 确保 `JobCatcher/backend/.env` 文件存在且配置正确
   - 所有API密钥和配置都从该文件自动加载

2. **端口管理** / Port Management
   - 默认端口：后端8000，前端7860
   - 可通过.env文件中的 `BACKEND_PORT` 和 `FRONTEND_PORT` 修改

3. **虚拟环境** / Virtual Environment
   - 确保虚拟环境已激活：`source bin/activate`
   - 所有依赖已安装：`pip install -r JobCatcher/backend/requirements.txt`

4. **开机自启动** / Auto Startup
   - 通过修改 `~/.bashrc` 实现
   - 仅在交互式终端登录时生效
   - 服务在后台自动启动，不阻塞终端

## 🛠️ 故障排除 / Troubleshooting

### 端口被占用 / Port Already in Use
```bash
# 检查端口占用 / Check port usage
netstat -tulpn | grep :8000

# 强制停止所有相关进程 / Force stop all related processes
bash JobCatcher/scripts/stop-services.sh
```

### 服务启动失败 / Service Start Failed
```bash
# 检查错误日志 / Check error logs
cat logs/backend-error.log

# 检查虚拟环境和依赖 / Check virtual environment and dependencies
which python
pip list | grep fastapi
```

### 热重载不生效 / Hot Reload Not Working
```bash
# 重启服务 / Restart services
bash JobCatcher/scripts/stop-services.sh
bash JobCatcher/scripts/startup.sh

# 检查文件权限 / Check file permissions
ls -la JobCatcher/backend/app/
```

---

**简单记住** / **Simple Remember**: 
- 启动：`bash JobCatcher/scripts/startup.sh`
- 停止：`bash JobCatcher/scripts/stop-services.sh`
- 状态：`bash JobCatcher/scripts/status.sh` 