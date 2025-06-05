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
