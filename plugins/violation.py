"""
违规追踪插件
检测违禁词 → 自动撤回 → 累计违规 → 达到阈值自动禁言1天
"""
import json
import os
from datetime import datetime, timezone, timedelta

from config import (
    BANNED_WORDS, BANNED_WORD_IGNORE_CASE,
    VIOLATION_MUTE_THRESHOLD, VIOLATION_FILE, DATA_DIR,
)

TZ = timezone(timedelta(hours=8))


def _load():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(VIOLATION_FILE):
        with open(VIOLATION_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}
    with open(VIOLATION_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data):
    with open(VIOLATION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _key(group_id, user_id):
    return f"{group_id}_{user_id}"


def check_banned(msg_text):
    """
    检测消息是否包含违禁词
    返回: 匹配到的违禁词列表
    """
    if BANNED_WORD_IGNORE_CASE:
        msg_lower = msg_text.lower()
    else:
        msg_lower = msg_text

    matched = []
    for word in BANNED_WORDS:
        if BANNED_WORD_IGNORE_CASE:
            if word.lower() in msg_lower:
                matched.append(word)
        else:
            if word in msg_text:
                matched.append(word)
    return matched


def record_violation(group_id, user_id, nickname, word, msg_text):
    """
    记录一次违规
    返回: (violation_count, should_mute) 违规次数和是否需要禁言
    """
    data = _load()
    k = _key(group_id, user_id)

    if k not in data:
        data[k] = {
            "user_id": user_id,
            "group_id": group_id,
            "nickname": nickname,
            "count": 0,
            "history": [],
            "last_mute_time": None,
        }

    user = data[k]
    user["nickname"] = nickname
    user["count"] += 1
    user["history"].append({
        "time": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "word": word,
        "msg": msg_text[:100],
    })

    count = user["count"]
    should_mute = count >= VIOLATION_MUTE_THRESHOLD

    if should_mute:
        user["count"] = 0  # 重置计数
        user["last_mute_time"] = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

    _save(data)
    return count, should_mute


def get_violation_info(group_id, user_id):
    """获取用户违规信息"""
    data = _load()
    k = _key(group_id, user_id)
    if k not in data:
        return "该用户暂无违规记录~"
    user = data[k]
    history = "\n".join([
        f"  {h['time']} - 触发词: {h['word']}"
        for h in user["history"][-5:]
    ])
    return (
        f"用户 {user['nickname']} 违规记录:\n"
        f"累计违规: {user['count']} 次\n"
        f"最近记录:\n{history}"
    )