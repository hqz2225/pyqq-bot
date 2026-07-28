"""
签到系统插件
支持每日签到、积分排行、查看积分
"""
import json
import os
import random
from datetime import datetime, timezone, timedelta

from config import SIGN_IN_MIN, SIGN_IN_MAX, DATA_DIR, SIGN_IN_FILE

# 北京时间时区
TZ = timezone(timedelta(hours=8))


def _load_data():
    """加载签到数据"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(SIGN_IN_FILE):
        with open(SIGN_IN_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}
    with open(SIGN_IN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_data(data):
    """保存签到数据"""
    with open(SIGN_IN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _get_today_key():
    """获取今天的日期字符串 (北京时间)"""
    return datetime.now(TZ).strftime("%Y-%m-%d")


def _get_user_key(group_id, user_id):
    """构建用户唯一key"""
    return f"{group_id}_{user_id}"


def do_sign_in(group_id, user_id, nickname):
    """执行签到, 返回结果消息"""
    data = _load_data()
    today = _get_today_key()
    user_key = _get_user_key(group_id, user_id)

    if user_key not in data:
        data[user_key] = {
            "user_id": user_id,
            "nickname": nickname,
            "total_score": 0,
            "last_sign_date": "",
            "sign_count": 0,
            "group_id": group_id,
        }

    user = data[user_key]
    user["nickname"] = nickname  # 每次更新昵称

    if user["last_sign_date"] == today:
        return f"{nickname} 今天已经签到过了哦~ 当前积分: {user['total_score']}"

    # 随机积分
    score = random.randint(SIGN_IN_MIN, SIGN_IN_MAX)
    user["total_score"] += score
    user["last_sign_date"] = today
    user["sign_count"] += 1

    _save_data(data)
    return (
        f"签到成功！{nickname} 获得 {score} 积分\n"
        f"累计积分: {user['total_score']} | 累计签到: {user['sign_count']} 天"
    )


def get_sign_rank(group_id, limit=10):
    """获取本群签到排行"""
    data = _load_data()
    members = [
        v for v in data.values()
        if v.get("group_id") == group_id
    ]
    members.sort(key=lambda x: x["total_score"], reverse=True)
    members = members[:limit]

    if not members:
        return "本群暂无签到记录~"

    lines = ["签到排行榜:"]
    for i, m in enumerate(members, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        lines.append(f"{medal} {m['nickname']} - {m['total_score']}分 (签到{m['sign_count']}天)")
    return "\n".join(lines)


def get_my_score(group_id, user_id):
    """查看我的积分"""
    data = _load_data()
    user_key = _get_user_key(group_id, user_id)
    if user_key not in data:
        return "你还没有签到过哦~ 发送 签到 开始签到吧！"
    user = data[user_key]
    return (
        f"{user['nickname']} 的签到信息:\n"
        f"累计积分: {user['total_score']}\n"
        f"累计签到: {user['sign_count']} 天\n"
        f"上次签到: {user['last_sign_date']}"
    )


def get_score(group_id, user_id):
    """获取用户积分 (供兑换系统使用)"""
    data = _load_data()
    user_key = _get_user_key(group_id, user_id)
    if user_key not in data:
        return 0
    return data[user_key]["total_score"]


def deduct_score(group_id, user_id, amount):
    """扣除积分, 返回剩余积分"""
    data = _load_data()
    user_key = _get_user_key(group_id, user_id)
    if user_key not in data:
        return 0
    user = data[user_key]
    user["total_score"] = max(0, user["total_score"] - amount)
    _save_data(data)
    return user["total_score"]


def add_score(group_id, user_id, nickname, amount):
    """增加积分, 返回新积分"""
    data = _load_data()
    user_key = _get_user_key(group_id, user_id)
    if user_key not in data:
        data[user_key] = {
            "user_id": user_id,
            "nickname": nickname,
            "total_score": 0,
            "last_sign_date": "",
            "sign_count": 0,
            "group_id": group_id,
        }
    user = data[user_key]
    user["nickname"] = nickname
    user["total_score"] = max(0, user["total_score"] + amount)
    _save_data(data)
    return user["total_score"]