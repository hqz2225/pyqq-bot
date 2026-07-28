# PyQQ Bot

基于 NapCat (Docker) + OneBot v11 WebSocket 的 QQ 群管理机器人。

## 功能

| 命令 | 说明 | 权限 |
|------|------|------|
| `/sign` | 每日签到，随机获得积分 | 所有人 |
| `/signrank` | 查看签到排行榜 | 所有人 |
| `/myscore` | 查看我的积分 | 所有人 |
| `/help` | 显示帮助菜单 | 所有人 |
| `/ban @用户 [分钟]` | 禁言用户 (默认10分钟) | 管理员 |
| `/unban @用户` | 解除禁言 | 管理员 |
| `/kick @用户` | 踢出群聊 | 管理员 |
| `/recall` | 回复消息并撤回 | 管理员 |
| `/muteall` | 开启全员禁言 | 管理员 |
| `/unmuteall` | 关闭全员禁言 | 管理员 |
| `/setadmin @用户` | 设置管理员 | 群主 |
| `/unsetadmin @用户` | 取消管理员 | 群主 |
| `/groupinfo` | 查看群信息 | 管理员 |

**自动功能:**
- 入群欢迎：新成员加入时自动发送欢迎消息

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

编辑 `config.py` 修改 WebSocket 连接地址：

```python
WS_URL = "ws://61.164.246.131:3001"  # 你的 NapCat WebSocket 地址
SUPER_ADMINS = []  # 超级管理员 QQ 号
```

### 3. 运行

```bash
python main.py
```

## 项目结构

```
pyqq-bot/
├── main.py              # 主入口，WebSocket 连接
├── bot.py               # 核心逻辑，命令路由
├── config.py            # 配置文件
├── plugins/
│   ├── __init__.py
│   ├── group_manage.py  # 群管理 API
│   └── sign_in.py       # 签到系统
└── data/                # 数据存储 (自动创建)
```

## 依赖

- Python >= 3.8
- websockets >= 12.0
- NapCat (Docker) 已配置 OneBot v11 WebSocket 服务端