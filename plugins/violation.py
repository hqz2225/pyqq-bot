"""
违规追踪插件
检测违禁词 → 自动撤回 → 累计违规 → 达到阈值自动禁言1天
短词(≤3字符)独立匹配, 避免 "你妈吃饭了吗" 误判
"""
import json
import os
import re
from datetime import datetime, timezone, timedelta

from config import (
    BANNED_WORDS, BANNED_WORD_IGNORE_CASE,
    VIOLATION_MUTE_THRESHOLD, VIOLATION_FILE, DATA_DIR,
    AD_DETECT_ENABLED, AD_DETECT_URL, AD_DETECT_QQ,
    AD_DETECT_WECHAT, AD_DETECT_PHONE,
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
    短词(≤3字符)需独立匹配, 不被中英文/数字包裹
    例如: "你妈" 在 "你妈吃饭了吗" 中不触发, 在 "你妈!" 中触发
    返回: 匹配到的违禁词列表
    """
    if BANNED_WORD_IGNORE_CASE:
        msg_lower = msg_text.lower()
    else:
        msg_lower = msg_text

    matched = []
    for word in BANNED_WORDS:
        if BANNED_WORD_IGNORE_CASE:
            word_lower = word.lower()
        else:
            word_lower = word

        # 短词独立匹配: 前后不能是中英文或数字
        if len(word) <= 3:
            pattern = re.escape(word_lower)
            if re.search(
                r'(?<![a-zA-Z0-9\u4e00-\u9fff])' + pattern +
                r'(?![a-zA-Z0-9\u4e00-\u9fff])',
                msg_lower,
            ):
                matched.append(word)
        else:
            if word_lower in msg_lower:
                matched.append(word)
    return matched


def check_ad(msg_text):
    """
    检测消息是否包含广告特征
    返回: 匹配到的广告类型描述, 无广告返回 None
    """
    if not AD_DETECT_ENABLED:
        return None

    # 链接检测: http/https/ftp
    if AD_DETECT_URL:
        if re.search(r'https?://\S+|ftp://\S+', msg_text, re.IGNORECASE):
            return "广告链接"

    # QQ号检测: 5-11位数字, 前后非数字, 且不在URL中
    if AD_DETECT_QQ:
        qq_match = re.search(r'(?<!\d)\d{5,11}(?!\d)', msg_text)
        if qq_match:
            qq = qq_match.group()
            # 排除: 纯数字日期(20260729)、价格(10000)、短id在URL中
            if not re.search(r'https?://.*' + qq, msg_text, re.IGNORECASE):
                return f"广告QQ号({qq})"

    # 微信号检测: wx / wxid / VX / vx / 微信 等 + 字母数字组合
    if AD_DETECT_WECHAT:
        if re.search(r'(?i)(wx|wxid|vx|微信)\s*[:：]?\s*[a-z0-9_-]{5,}', msg_text):
            return "广告微信号"

    # 手机号检测: 1开头11位数字
    if AD_DETECT_PHONE:
        if re.search(r'(?<!\d)1[3-9]\d{9}(?!\d)', msg_text):
            return "广告手机号"

    return None


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