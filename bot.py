"""
PyQQ Bot 核心逻辑
中文命令路由 + 违禁词自动检测 + 入群欢迎
"""
import re

from config import VIOLATION_MUTE_THRESHOLD, WELCOME_MSG
from plugins import sign_in, group_manage, violation


def extract_plain_text(raw_message):
    """提取纯文本 (去掉 CQ 码)"""
    text = re.sub(r"\[CQ:[^\]]+\]", "", raw_message).strip()
    return text


HELP_TEXT = """
  群管机器人 帮助菜单

  签到系统:
  签到      - 每日签到
  排行      - 签到排行榜
  积分      - 查看我的积分

  管理:
  群信息    - 查看群信息 (仅群主/管理员)
  查违规 @用户 - 查看用户违规记录 (仅群主/管理员)

  帮助      - 显示此菜单

  自动功能:
  违禁词检测 → 自动撤回 → 累计3次违规 → 禁言1天
  新人入群 → 自动欢迎
""".strip()


async def on_group_message(ws, event):
    """处理群消息"""
    raw_message = event.get("raw_message", event.get("message", ""))
    group_id = event.get("group_id")
    user_id = event.get("user_id")
    sender = event.get("sender", {})
    sender_role = sender.get("role", "member")
    sender_nickname = sender.get("nickname", str(user_id))
    message_id = event.get("message_id")

    plain_text = extract_plain_text(raw_message)

    # ========== 1. 违禁词检测 (自动) ==========
    # 管理员和群主不受检测
    if sender_role not in ("owner", "admin") and plain_text:
        matched = violation.check_banned(plain_text)
        if matched:
            # 撤回消息
            ok = await group_manage.delete_msg(ws, message_id)
            if ok:
                # 记录违规
                count, should_mute = violation.record_violation(
                    group_id, user_id, sender_nickname, matched[0], plain_text
                )

                if should_mute:
                    # 达到阈值，禁言 1 天
                    await group_manage.ban_user(ws, group_id, user_id, 86400)
                    await group_manage.send_group_msg(
                        ws, group_id,
                        f"[CQ:at,qq={user_id}] 累计违规 {count} 次，已被禁言 1 天！\n"
                        f"触发词: {matched[0]}"
                    )
                else:
                    await group_manage.send_group_msg(
                        ws, group_id,
                        f"[CQ:at,qq={user_id}] 消息已撤回！检测到违禁词: {matched[0]}\n"
                        f"累计违规 {count} 次 (满 {VIOLATION_MUTE_THRESHOLD} 次将禁言 1 天)"
                    )
            return  # 违禁词消息不再处理命令

    # ========== 2. 命令路由 ==========
    if not plain_text:
        return

    cmd = plain_text.strip()

    # --- 签到 ---
    if cmd == "签到":
        result = sign_in.do_sign_in(group_id, user_id, sender_nickname)
        await group_manage.send_group_msg(ws, group_id, result)
        return

    # --- 排行 ---
    if cmd == "排行":
        result = sign_in.get_sign_rank(group_id)
        await group_manage.send_group_msg(ws, group_id, result)
        return

    # --- 积分 ---
    if cmd == "积分":
        result = sign_in.get_my_score(group_id, user_id)
        await group_manage.send_group_msg(ws, group_id, result)
        return

    # --- 帮助 ---
    if cmd == "帮助":
        await group_manage.send_group_msg(ws, group_id, HELP_TEXT)
        return

    # ========== 需要管理权限 ==========
    if sender_role not in ("owner", "admin"):
        return  # 非管理员发其他内容不做处理

    # --- 群信息 ---
    if cmd == "群信息":
        result = await group_manage.get_group_info(ws, group_id)
        await group_manage.send_group_msg(ws, group_id, result)
        return

    # --- 查违规 @用户 ---
    if cmd.startswith("查违规"):
        # 提取 @ 的用户
        match = re.search(r"\[CQ:at,qq=(\d+)\]", raw_message)
        if match:
            target_id = int(match.group(1))
            result = violation.get_violation_info(group_id, target_id)
        else:
            result = "请 @ 要查询的用户，例如: 查违规 @用户"
        await group_manage.send_group_msg(ws, group_id, result)
        return


async def handle_event(ws, event):
    """处理收到的 OneBot 事件"""
    post_type = event.get("post_type")

    if post_type == "message":
        message_type = event.get("message_type")
        if message_type == "group":
            await on_group_message(ws, event)

    elif post_type == "notice":
        notice_type = event.get("notice_type")
        if notice_type == "group_increase":
            group_id = event.get("group_id")
            user_id = event.get("user_id")
            welcome_msg = WELCOME_MSG.replace(
                "{nickname}", f"[CQ:at,qq={user_id}]"
            )
            await group_manage.send_group_msg(ws, group_id, welcome_msg)