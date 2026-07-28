"""
PyQQ Bot 核心逻辑
命令路由 & 事件处理
"""
import json
import re
import asyncio

from config import CMD_PREFIX, SUPER_ADMINS, WELCOME_MSG
from plugins import sign_in, group_manage


def parse_at_user_id(raw_message):
    """
    从消息中提取 @ 的 QQ 号
    支持 [CQ:at,qq=123456] 格式
    """
    match = re.search(r"\[CQ:at,qq=(\d+)\]", raw_message)
    if match:
        return int(match.group(1))
    return None


def parse_command(raw_message):
    """
    从文本消息中提取命令和参数
    返回 (command, args_string)
    """
    text = re.sub(r"\[CQ:at,qq=\d+\]", "", raw_message).strip()
    text = re.sub(r"\[CQ:[^\]]+\]", "", text).strip()

    if not text.startswith(CMD_PREFIX):
        return None, None

    parts = text[len(CMD_PREFIX):].split(maxsplit=1)
    cmd = parts[0].lower().strip()
    args = parts[1].strip() if len(parts) > 1 else ""
    return cmd, args


def is_admin(sender_role, user_id):
    """判断用户是否有管理权限"""
    if sender_role in ("owner", "admin"):
        return True
    if user_id in SUPER_ADMINS:
        return True
    return False


HELP_TEXT = """
PyQQ Bot 群管理机器人 帮助菜单

  群管理命令 (需要群主/管理员权限):
  /ban @用户 [分钟]    - 禁言用户 (默认10分钟)
  /unban @用户         - 解除禁言
  /kick @用户          - 踢出群聊
  /recall              - 回复一条消息并发送此命令撤回它
  /muteall             - 开启全员禁言
  /unmuteall           - 关闭全员禁言
  /setadmin @用户      - 设置管理员
  /unsetadmin @用户    - 取消管理员
  /groupinfo           - 查看群信息

  签到系统:
  /sign                - 每日签到
  /signrank            - 签到排行榜
  /myscore             - 查看我的积分

  其他:
  /help                - 显示此帮助菜单
""".strip()


async def handle_command(ws, event):
    """处理群消息命令"""
    raw_message = event.get("raw_message", event.get("message", ""))
    group_id = event.get("group_id")
    user_id = event.get("user_id")
    sender = event.get("sender", {})
    sender_role = sender.get("role", "member")
    sender_nickname = sender.get("nickname", str(user_id))
    message_id = event.get("message_id")

    cmd, args = parse_command(raw_message)
    if not cmd:
        return

    # ========== 无需权限的命令 ==========
    if cmd == "sign":
        result = sign_in.do_sign_in(group_id, user_id, sender_nickname)
        await group_manage.send_group_msg(ws, group_id, result)
        return

    if cmd == "signrank":
        result = sign_in.get_sign_rank(group_id)
        await group_manage.send_group_msg(ws, group_id, result)
        return

    if cmd == "myscore":
        result = sign_in.get_my_score(group_id, user_id)
        await group_manage.send_group_msg(ws, group_id, result)
        return

    if cmd == "help":
        await group_manage.send_group_msg(ws, group_id, HELP_TEXT)
        return

    # ========== 需要管理权限的命令 ==========
    if not is_admin(sender_role, user_id):
        await group_manage.send_group_msg(ws, group_id, "权限不足，需要群主或管理员权限~")
        return

    if cmd == "ban":
        target_uid = parse_at_user_id(raw_message)
        if not target_uid:
            await group_manage.send_group_msg(ws, group_id, "请 @ 要禁言的用户，例如: /ban @用户 5")
            return
        try:
            minutes = int(args) if args else 10
        except ValueError:
            minutes = 10
        minutes = max(1, min(minutes, 43200))  # 限制 1分钟 ~ 30天
        result = await group_manage.ban_user(ws, group_id, target_uid, minutes)
        await group_manage.send_group_msg(ws, group_id, result)
        return

    if cmd == "unban":
        target_uid = parse_at_user_id(raw_message)
        if not target_uid:
            await group_manage.send_group_msg(ws, group_id, "请 @ 要解除禁言的用户")
            return
        result = await group_manage.unban_user(ws, group_id, target_uid)
        await group_manage.send_group_msg(ws, group_id, result)
        return

    if cmd == "kick":
        target_uid = parse_at_user_id(raw_message)
        if not target_uid:
            await group_manage.send_group_msg(ws, group_id, "请 @ 要踢出的用户")
            return
        result = await group_manage.kick_user(ws, group_id, target_uid)
        await group_manage.send_group_msg(ws, group_id, result)
        return

    if cmd == "recall":
        # 检查是否是回复消息
        reply_match = re.search(r"\[CQ:reply,id=(-?\d+)\]", raw_message)
        if reply_match:
            target_msg_id = int(reply_match.group(1))
        else:
            await group_manage.send_group_msg(ws, group_id, "请回复要撤回的消息再发送 /recall")
            return
        result = await group_manage.delete_msg(ws, target_msg_id)
        await group_manage.send_group_msg(ws, group_id, result)
        return

    if cmd == "muteall":
        result = await group_manage.set_whole_ban(ws, group_id, enable=True)
        await group_manage.send_group_msg(ws, group_id, result)
        return

    if cmd == "unmuteall":
        result = await group_manage.set_whole_ban(ws, group_id, enable=False)
        await group_manage.send_group_msg(ws, group_id, result)
        return

    if cmd == "setadmin":
        target_uid = parse_at_user_id(raw_message)
        if not target_uid:
            await group_manage.send_group_msg(ws, group_id, "请 @ 要设置管理员的用户")
            return
        result = await group_manage.set_group_admin(ws, group_id, target_uid, enable=True)
        await group_manage.send_group_msg(ws, group_id, result)
        return

    if cmd == "unsetadmin":
        target_uid = parse_at_user_id(raw_message)
        if not target_uid:
            await group_manage.send_group_msg(ws, group_id, "请 @ 要取消管理员的用户")
            return
        result = await group_manage.set_group_admin(ws, group_id, target_uid, enable=False)
        await group_manage.send_group_msg(ws, group_id, result)
        return

    if cmd == "groupinfo":
        result = await group_manage.get_group_info(ws, group_id)
        await group_manage.send_group_msg(ws, group_id, result)
        return


async def handle_event(ws, event):
    """处理收到的 OneBot 事件"""
    post_type = event.get("post_type")

    if post_type == "message":
        message_type = event.get("message_type")
        if message_type == "group":
            await handle_command(ws, event)

    elif post_type == "notice":
        notice_type = event.get("notice_type")
        if notice_type == "group_increase":
            # 入群欢迎
            group_id = event.get("group_id")
            user_id = event.get("user_id")
            welcome_msg = WELCOME_MSG.replace(
                "{nickname}", f"[CQ:at,qq={user_id}]"
            )
            await group_manage.send_group_msg(ws, group_id, welcome_msg)

        elif notice_type == "group_decrease":
            # 有人退群/被踢
            pass