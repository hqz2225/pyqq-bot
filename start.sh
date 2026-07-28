#!/bin/bash
# PyQQ Bot 启动脚本 (崩溃自动重启)
# 用法: bash start.sh
# 按 Ctrl+C 两次退出 (第一次结束当前进程，第二次在5秒内再按一次退出)

cd /opt/bots/bot1/pyqq-bot-master

RESTART_DELAY=2

while true; do
    echo "========================================"
    echo "  PyQQ Bot 启动中..."
    echo "  $(date)"
    echo "========================================"
    python3 main.py
    EXIT_CODE=$?
    echo "机器人已退出 (exit code: $EXIT_CODE)"
    echo "将在 ${RESTART_DELAY} 秒后重启... (按 Ctrl+C 退出)"
    sleep $RESTART_DELAY
done