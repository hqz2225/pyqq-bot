"""
PyQQ Bot 核心逻辑
中文命令路由 (必须以 / 开头) + 违禁词自动检测 + 入群欢迎 + 积分兑换
"""
import asyncio
import json
import os
import re
import subprocess
import sys

import config
from config import VIOLATION_MUTE_THRESHOLD, WELCOME_MSG, WELCOME_FILE, DATA_DIR, GIT_MIRROR
from plugins import sign_in, group_manage, violation, exchange


def extract_plain_text(event):
    """提取纯文本, 兼容 字符串格式 和 数组格式"""
    message = event.get("message", "")
    raw_message = event.get("raw_message", "")

    if isinstance(message, str) and message:
        return re.sub(r"\[CQ:[^\]]+\]", "", message).strip()
    if raw_message and isinstance(raw_message, str):
        return re.sub(r"\[CQ:[^\]]+\]", "", raw_message).strip()

    if isinstance(message, list):
        texts = []
        for seg in message:
            if isinstance(seg, dict) and seg.get("type") == "text":
                data = seg.get("data", {})
                texts.append(data.get("text", ""))
        return "".join(texts).strip()

    return ""


def extract_at_target(event):
    """提取 @ 目标的 QQ 号, 兼容两种格式"""
    raw_message = event.get("raw_message", "")
    if isinstance(raw_message, str):
        match = re.search(r"\[CQ:at,qq=(\d+)\]", raw_message)
        if match:
            return int(match.group(1))

    message = event.get("message", "")
    if isinstance(message, list):
        for seg in message:
            if isinstance(seg, dict) and seg.get("type") == "at":
                data = seg.get("data", {})
                qq = data.get("qq", "")
                if qq and qq != "all":
                    return int(qq)
    return None


# ========== 入群欢迎消息管理 ==========

def _load_welcome():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(WELCOME_FILE):
        with open(WELCOME_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}
    with open(WELCOME_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_welcome(data):
    with open(WELCOME_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_welcome_msg(group_id):
    """获取自定义欢迎消息, 没有则返回默认"""
    data = _load_welcome()
    return data.get(str(group_id), WELCOME_MSG)


def set_welcome_msg(group_id, text):
    """设置自定义欢迎消息"""
    data = _load_welcome()
    data[str(group_id)] = text
    _save_welcome(data)
    return f"入群欢迎消息已更新为:\n{text}"


def format_welcome(msg_template, user_id):
    """
    格式化欢迎消息: 替换 /用户 和 {nickname} 为 @mention
    例如: "欢迎/用户进群" → "欢迎[CQ:at,qq=xxx]进群"
    """
    at = f"[CQ:at,qq={user_id}]"
    msg = msg_template.replace("{nickname}", at)
    msg = msg.replace("/用户", at)
    return msg


HELP_TEXT = """
  群管机器人 帮助菜单 (所有命令必须以 / 开头)

  签到系统:
  /签到      - 每日签到
  /排行      - 签到排行榜
  /积分      - 查看我的积分

  积分兑换:
  /兑换      - 查看兑换列表
  /兑换 编号 - 兑换指定物品

  管理 (仅群主/管理员):
  /群信息    - 查看群信息
  /查违规 @用户 - 查看用户违规记录
  /设置欢迎 消息 - 修改入群欢迎消息 (支持 /用户 占位符, 如: /设置欢迎 欢迎/用户进群)
  /查看欢迎  - 查看当前入群欢迎消息

  兑换管理 (仅群主/管理员):
  /添加兑换 名称 积分 - 添加兑换物品
  /删除兑换 编号    - 删除兑换物品
  /加积分 @用户 数量 - 给用户加积分
  /扣积分 @用户 数量 - 扣用户积分
  /更新      - 从 GitHub 拉取最新代码并重启

  /帮助      - 显示此菜单

  自动功能:
  违禁词检测 → 自动撤回 → 累计3次违规 → 禁言1天
  新人入群 → 自动欢迎
""".strip()


async def on_group_message(event):
    """处理群消息"""
    group_id = event.get("group_id")
    user_id = event.get("user_id")

    # 自动记录群号 (用于更新通知)
    if config.AUTO_GROUP_ID is None:
        config.AUTO_GROUP_ID = group_id

    sender = event.get("sender", {})
    sender_role = sender.get("role", "member")
    sender_nickname = sender.get("nickname", str(user_id))
    message_id = event.get("message_id")

    plain_text = extract_plain_text(event)

    # ========== 1. 违禁词检测 (自动, 不需要前缀) ==========
    if sender_role not in ("owner", "admin") and plain_text:
        matched = violation.check_banned(plain_text)
        if matched:
            # 先记录违规 (无论撤回是否成功)
            count, should_mute = violation.record_violation(
                group_id, user_id, sender_nickname, matched[0], plain_text
            )
            # 尝试撤回
            await group_manage.delete_msg(message_id)
            if should_mute:
                banned = await group_manage.ban_user(group_id, user_id, 86400)
                if banned:
                    await group_manage.send_group_msg(
                        group_id,
                        f"[CQ:at,qq={user_id}] 累计违规 {count} 次，已被禁言 1 天！\n"
                        f"触发词: {matched[0]}"
                    )
                else:
                    await group_manage.send_group_msg(
                        group_id,
                        f"[CQ:at,qq={user_id}] 累计违规 {count} 次，禁言失败 (可能机器人权限不足)"
                    )
            else:
                await group_manage.send_group_msg(
                    group_id,
                    f"[CQ:at,qq={user_id}] 消息已撤回！检测到违禁词: {matched[0]}\n"
                    f"累计违规 {count} 次 (满 {VIOLATION_MUTE_THRESHOLD} 次将禁言 1 天)"
                )
            return

    # ========== 2. 命令路由 (必须以 / 开头) ==========
    if not plain_text:
        return

    raw = plain_text.strip()
    if not raw.startswith("/"):
        return  # 不是命令, 忽略
    cmd = raw[1:].strip()

    # --- 签到 ---
    if cmd == "签到":
        result = sign_in.do_sign_in(group_id, user_id, sender_nickname)
        await group_manage.send_group_msg(group_id, result)
        return

    # --- 排行 ---
    if cmd == "排行":
        result = sign_in.get_sign_rank(group_id)
        await group_manage.send_group_msg(group_id, result)
        return

    # --- 积分 ---
    if cmd == "积分":
        result = sign_in.get_my_score(group_id, user_id)
        await group_manage.send_group_msg(group_id, result)
        return

    # --- 帮助 ---
    if cmd == "帮助":
        await group_manage.send_group_msg(group_id, HELP_TEXT)
        return

    # --- 兑换列表 ---
    if cmd == "兑换":
        result = exchange.list_items(group_id)
        await group_manage.send_group_msg(group_id, result)
        return

    # --- 兑换 编号 ---
    if cmd.startswith("兑换 ") and len(cmd) > 3:
        try:
            idx = int(cmd[3:].strip())
            result = exchange.redeem_item(
                group_id, user_id, sender_nickname, idx,
                sign_in.get_score, sign_in.deduct_score
            )
        except ValueError:
            result = "请输入正确的编号，例如: /兑换 1"
        await group_manage.send_group_msg(group_id, result)
        return

    # ========== 需要管理权限 ==========
    if sender_role not in ("owner", "admin"):
        return

    # --- 群信息 ---
    if cmd == "群信息":
        result = await group_manage.get_group_info(group_id)
        await group_manage.send_group_msg(group_id, result)
        return

    # --- 查违规 @用户 ---
    if cmd.startswith("查违规"):
        target_id = extract_at_target(event)
        if target_id:
            result = violation.get_violation_info(group_id, target_id)
        else:
            result = "请 @ 要查询的用户，例如: /查违规 @用户"
        await group_manage.send_group_msg(group_id, result)
        return

    # --- 设置欢迎 ---
    if cmd.startswith("设置欢迎 "):
        new_msg = cmd[5:].strip()
        result = set_welcome_msg(group_id, new_msg)
        await group_manage.send_group_msg(group_id, result)
        return

    # --- 查看欢迎 ---
    if cmd == "查看欢迎":
        msg = get_welcome_msg(group_id)
        await group_manage.send_group_msg(group_id, f"当前入群欢迎消息:\n{msg}")
        return

    # --- 添加兑换 名称 积分 ---
    if cmd.startswith("添加兑换 "):
        parts = cmd[5:].strip().rsplit(" ", 1)
        if len(parts) == 2:
            name, price_str = parts
            try:
                price = int(price_str)
                if price < 1:
                    result = "积分必须大于 0"
                else:
                    result = exchange.add_item(group_id, name, price)
            except ValueError:
                result = "格式: /添加兑换 名称 积分  例如: /添加兑换 管理员唱歌 100"
        else:
            result = "格式: /添加兑换 名称 积分  例如: /添加兑换 管理员唱歌 100"
        await group_manage.send_group_msg(group_id, result)
        return

    # --- 删除兑换 编号 ---
    if cmd.startswith("删除兑换 "):
        try:
            idx = int(cmd[5:].strip())
            result = exchange.remove_item(group_id, idx)
        except ValueError:
            result = "请输入正确的编号，例如: /删除兑换 1"
        await group_manage.send_group_msg(group_id, result)
        return

    # --- 加积分 @用户 数量 ---
    if cmd.startswith("加积分"):
        target_id = extract_at_target(event)
        parts = cmd[3:].strip().split()
        if target_id and len(parts) >= 2:
            try:
                amount = int(parts[-1])
                new_score = sign_in.add_score(group_id, target_id, "", amount)
                result = f"已为用户 {target_id} 增加 {amount} 积分，当前积分: {new_score}"
            except ValueError:
                result = "格式: /加积分 @用户 数量"
        else:
            result = "格式: /加积分 @用户 数量"
        await group_manage.send_group_msg(group_id, result)
        return

    # --- 扣积分 @用户 数量 ---
    if cmd.startswith("扣积分"):
        target_id = extract_at_target(event)
        parts = cmd[3:].strip().split()
        if target_id and len(parts) >= 2:
            try:
                amount = int(parts[-1])
                new_score = sign_in.deduct_score(group_id, target_id, amount)
                result = f"已为用户 {target_id} 扣除 {amount} 积分，当前积分: {new_score}"
            except ValueError:
                result = "格式: /扣积分 @用户 数量"
        else:
            result = "格式: /扣积分 @用户 数量"
        await group_manage.send_group_msg(group_id, result)
        return

    # --- 更新 ---
    if cmd == "更新":
        await group_manage.send_group_msg(group_id, "正在拉取最新代码...")
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            url_result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=base_dir, capture_output=True, text=True, timeout=10
            )
            remote_url = url_result.stdout.strip()
            if GIT_MIRROR and remote_url:
                mirror_url = GIT_MIRROR + remote_url
            else:
                mirror_url = remote_url
            subprocess.run(
                ["git", "fetch", mirror_url, "master"],
                cwd=base_dir, capture_output=True, text=True, timeout=60
            )
            merge_result = subprocess.run(
                ["git", "merge", "FETCH_HEAD", "--ff-only"],
                cwd=base_dir, capture_output=True, text=True, timeout=30
            )
            output = merge_result.stdout.strip() or merge_result.stderr.strip()
            await group_manage.send_group_msg(group_id, f"更新结果:\n{output}\n\n正在重启...")
            await asyncio.sleep(0.5)
        except Exception as e:
            await group_manage.send_group_msg(group_id, f"更新失败: {e}")
            return
        os.execv(sys.executable, [sys.executable] + sys.argv)
        return


async def handle_event(ws, event):
    """处理收到的 OneBot 事件"""
    post_type = event.get("post_type")

    if post_type == "message":
        message_type = event.get("message_type")
        if message_type == "group":
            await on_group_message(event)

    elif post_type == "notice":
        notice_type = event.get("notice_type")
        if notice_type == "group_increase":
            group_id = event.get("group_id")
            user_id = event.get("user_id")
            msg = format_welcome(get_welcome_msg(group_id), user_id)
            await group_manage.send_group_msg(group_id, msg)