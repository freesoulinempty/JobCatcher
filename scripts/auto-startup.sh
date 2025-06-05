#!/bin/bash
# JobCatcher 开机自启动配置脚本 / JobCatcher Auto-startup Configuration Script
# 适用于容器化环境 / For containerized environments

echo "🔧 JobCatcher 开机自启动配置脚本 / JobCatcher Auto-startup Configuration Script"
echo "=============================================================="

# 项目根目录 / Project root directory
PROJECT_ROOT="/home/devbox/project"
PROFILE_FILE="/home/devbox/.profile"
BASHRC_FILE="/home/devbox/.bashrc"
STARTUP_SCRIPT="$PROJECT_ROOT/JobCatcher/scripts/startup.sh"

echo "📁 项目根目录 / Project root directory: $PROJECT_ROOT"
echo "📋 配置文件 / Profile file: $PROFILE_FILE"
echo "📋 Bashrc文件 / Bashrc file: $BASHRC_FILE"

# 检查启动脚本是否存在 / Check if startup script exists
if [ ! -f "$STARTUP_SCRIPT" ]; then
    echo "❌ 启动脚本不存在 / Startup script not found: $STARTUP_SCRIPT"
    exit 1
fi

# 创建自启动标记 / Create auto-startup marker
AUTO_START_MARKER="# JobCatcher Auto-startup"
AUTO_START_COMMAND="# Auto-start JobCatcher services on login
if [ -f \"$STARTUP_SCRIPT\" ] && [ -t 0 ]; then
    echo \"🚀 自动启动JobCatcher服务... / Auto-starting JobCatcher services...\"
    bash \"$STARTUP_SCRIPT\" >/dev/null 2>&1 &
    echo \"✅ JobCatcher服务已在后台启动 / JobCatcher services started in background\"
fi"

# 检查是否已经配置了自启动 / Check if auto-startup is already configured
if grep -q "$AUTO_START_MARKER" "$BASHRC_FILE" 2>/dev/null; then
    echo "⚠️  开机自启动已配置 / Auto-startup already configured"
    read -p "是否重新配置？(y/N) / Reconfigure? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 已取消 / Cancelled"
        exit 0
    fi
    
    # 移除现有配置 / Remove existing configuration
    echo "🗑️  移除现有配置 / Removing existing configuration..."
    sed -i "/$AUTO_START_MARKER/,/^$/d" "$BASHRC_FILE" 2>/dev/null || true
fi

# 添加自启动配置到 .bashrc / Add auto-startup configuration to .bashrc
echo "➕ 添加自启动配置到 .bashrc / Adding auto-startup configuration to .bashrc..."

echo "" >> "$BASHRC_FILE"
echo "$AUTO_START_MARKER" >> "$BASHRC_FILE"
echo "$AUTO_START_COMMAND" >> "$BASHRC_FILE"

echo "✅ 开机自启动配置完成 / Auto-startup configuration completed"

# 创建手动控制脚本 / Create manual control scripts
echo "🔧 创建手动控制选项 / Creating manual control options..."

# 创建启用自启动脚本 / Create enable auto-startup script
cat > "$PROJECT_ROOT/JobCatcher/scripts/enable-auto-startup.sh" << 'EOF'
#!/bin/bash
# 启用JobCatcher开机自启动 / Enable JobCatcher Auto-startup

BASHRC_FILE="/home/devbox/.bashrc"
AUTO_START_MARKER="# JobCatcher Auto-startup"

if grep -q "$AUTO_START_MARKER" "$BASHRC_FILE" 2>/dev/null; then
    # 启用配置（移除注释） / Enable configuration (remove comments)
    sed -i "/$AUTO_START_MARKER/,/^$/ { s/^# *//; }" "$BASHRC_FILE"
    echo "✅ JobCatcher开机自启动已启用 / JobCatcher auto-startup enabled"
else
    echo "❌ 未找到自启动配置，请先运行 auto-startup.sh / Auto-startup configuration not found, please run auto-startup.sh first"
    exit 1
fi
EOF

# 创建禁用自启动脚本 / Create disable auto-startup script
cat > "$PROJECT_ROOT/JobCatcher/scripts/disable-auto-startup.sh" << 'EOF'
#!/bin/bash
# 禁用JobCatcher开机自启动 / Disable JobCatcher Auto-startup

BASHRC_FILE="/home/devbox/.bashrc"
AUTO_START_MARKER="# JobCatcher Auto-startup"

if grep -q "$AUTO_START_MARKER" "$BASHRC_FILE" 2>/dev/null; then
    # 禁用配置（添加注释） / Disable configuration (add comments)
    sed -i "/$AUTO_START_MARKER/,/^$/ { /^[^#]/ s/^/# /; }" "$BASHRC_FILE"
    echo "✅ JobCatcher开机自启动已禁用 / JobCatcher auto-startup disabled"
else
    echo "❌ 未找到自启动配置 / Auto-startup configuration not found"
    exit 1
fi
EOF

# 给控制脚本添加可执行权限 / Add executable permissions to control scripts
chmod +x "$PROJECT_ROOT/JobCatcher/scripts/enable-auto-startup.sh"
chmod +x "$PROJECT_ROOT/JobCatcher/scripts/disable-auto-startup.sh"

echo "✅ 手动控制脚本创建完成 / Manual control scripts created"

# 显示使用说明 / Show usage instructions
echo ""
echo "📋 使用说明 / Usage Instructions:"
echo "=============================================================="
echo "🚀 当前状态 / Current Status: 开机自启动已启用 / Auto-startup enabled"
echo ""
echo "🛠️  管理命令 / Management Commands:"
echo "  启用自启动 / Enable auto-startup:   bash JobCatcher/scripts/enable-auto-startup.sh"
echo "  禁用自启动 / Disable auto-startup:  bash JobCatcher/scripts/disable-auto-startup.sh"
echo "  手动启动服务 / Manual start:         bash JobCatcher/scripts/startup.sh"
echo "  停止服务 / Stop services:           bash JobCatcher/scripts/stop-services.sh"
echo "  查看状态 / Check status:            bash JobCatcher/scripts/status.sh"
echo ""
echo "🔄 测试自启动 / Test Auto-startup:"
echo "  重新登录shell或执行 / Re-login to shell or execute:"
echo "  source ~/.bashrc"
echo ""
echo "⚠️  注意事项 / Important Notes:"
echo "  - 自启动仅在交互式终端中生效 / Auto-startup only works in interactive terminals"
echo "  - 服务将在后台启动，不会阻塞终端 / Services start in background, won't block terminal"
echo "  - 日志文件位置: $PROJECT_ROOT/logs/ / Log files location: $PROJECT_ROOT/logs/" 