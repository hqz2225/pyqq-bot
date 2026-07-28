"""
PyQQ Bot 配置文件
连接 NapCat (Docker) 的 OneBot v11 WebSocket
"""

# WebSocket 连接地址
WS_URL = "ws://61.164.246.131:3001"

# 机器人超级管理员 QQ 号 (可执行所有命令)
SUPER_ADMINS = []

# 签到配置
SIGN_IN_MIN = 1       # 签到最低积分
SIGN_IN_MAX = 10      # 签到最高积分
SIGN_IN_RESET_HOUR = 0  # 每日签到重置时间 (UTC+8)

# 数据文件路径
DATA_DIR = "data"
SIGN_IN_FILE = "data/sign_in.json"

# 入群欢迎模板 (可用 {nickname} 替换昵称)
WELCOME_MSG = "欢迎 {nickname} 加入本群！请遵守群规，文明交流~"

# 命令前缀
CMD_PREFIX = "/"