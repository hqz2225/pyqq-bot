#!/bin/bash
# PyQQ Bot 一键更新 + 重启
# 用法: bash update.sh

set -e

cd /opt/bots/bot1/pyqq-bot-master

echo "正在拉取最新代码..."
git pull

echo "更新完成！重启机器人..."
python3 main.py