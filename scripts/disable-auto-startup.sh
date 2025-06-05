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
