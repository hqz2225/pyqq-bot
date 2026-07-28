"""
PyQQ Bot 配置文件
连接 NapCat (Docker) 的 OneBot v11 WebSocket
"""

# WebSocket 连接地址
WS_URL = "ws://127.0.0.1:3001/?access_token=123456"

# 签到配置
SIGN_IN_MIN = 1       # 签到最低积分
SIGN_IN_MAX = 10      # 签到最高积分

# 数据文件路径
DATA_DIR = "data"
SIGN_IN_FILE = "data/sign_in.json"
VIOLATION_FILE = "data/violation.json"
WELCOME_FILE = "data/welcome.json"
EXCHANGE_FILE = "data/exchange.json"

# 入群欢迎模板 ({nickname} 会被替换为 @用户)
WELCOME_MSG = "欢迎 {nickname} 加入本群！请遵守群规，文明交流~"

# ========== 违禁词检测 ==========
# 违禁词列表 (包含这些词的消息会被自动撤回)
BANNED_WORDS = [
    # 广告类
    "广告", "加群", "兼职", "刷单", "代理",
    "赌博", "彩票", "贷款", "信用卡", "套现", "办证", "刻章",
    # 色情类
    "色情", "黄片", "约炮", "裸聊", "成人",
    # 脏话类
    "傻逼", "sb", "草泥马", "cnm", "操你妈", "操你",
    "你妈死了", "nmsl", "傻狗", "废物", "垃圾玩意",
    "日你妈", "rnm", "他妈", "你妈的", "你大爷",
    "脑残", "智障", "弱智", "白痴",
    "fuck", "shit", "bitch", "asshole",
    "死全家", "狗日的", "王八蛋", "龟儿子",
    "艹", "滚蛋", "滚犊子", "去死",
]

# 违规阈值: 累计违规 N 次后自动禁言 1 天
VIOLATION_MUTE_THRESHOLD = 3

# 违禁词检测时是否忽略大小写
BANNED_WORD_IGNORE_CASE = True