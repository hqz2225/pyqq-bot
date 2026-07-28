"""
群管理插件
禁言 / 解禁 / 踢人 / 撤回 / 全员禁言 / 群信息
"""
import json


async def ban_user(ws, group_id, user_id, duration_minutes=10):
    """禁言用户 (默认10分钟)"""
    duration = duration_minutes * 60  # 转为秒
    payload = {
        "action": "set_group_ban",
        "params": {
            "group_id": group_id,
            "user_id": user_id,
            "duration": duration,
        },
    }
    await ws.send(json.dumps(payload))
    resp = await ws.recv()
    result = json.loads(resp)
    if result.get("status") == "ok":
        return f"已禁言用户 {user_id} {duration_minutes} 分钟"
    return f"禁言失败: {result.get('wording', '未知错误')}"


async def unban_user(ws, group_id, user_id):
    """解除禁言"""
    payload = {
        "action": "set_group_ban",
        "params": {
            "group_id": group_id,
            "user_id": user_id,
            "duration": 0,
        },
    }
    await ws.send(json.dumps(payload))
    resp = await ws.recv()
    result = json.loads(resp)
    if result.get("status") == "ok":
        return f"已解除用户 {user_id} 的禁言"
    return f"解禁失败: {result.get('wording', '未知错误')}"


async def kick_user(ws, group_id, user_id, reject_add=False):
    """踢出用户"""
    payload = {
        "action": "set_group_kick",
        "params": {
            "group_id": group_id,
            "user_id": user_id,
            "reject_add_request": reject_add,
        },
    }
    await ws.send(json.dumps(payload))
    resp = await ws.recv()
    result = json.loads(resp)
    if result.get("status") == "ok":
        return f"已将用户 {user_id} 踢出群聊"
    return f"踢人失败: {result.get('wording', '未知错误')}"


async def delete_msg(ws, message_id):
    """撤回消息"""
    payload = {
        "action": "delete_msg",
        "params": {
            "message_id": message_id,
        },
    }
    await ws.send(json.dumps(payload))
    resp = await ws.recv()
    result = json.loads(resp)
    if result.get("status") == "ok":
        return "消息已撤回"
    return f"撤回失败: {result.get('wording', '未知错误')}"


async def set_whole_ban(ws, group_id, enable=True):
    """全员禁言 / 解除全员禁言"""
    payload = {
        "action": "set_group_whole_ban",
        "params": {
            "group_id": group_id,
            "enable": enable,
        },
    }
    await ws.send(json.dumps(payload))
    resp = await ws.recv()
    result = json.loads(resp)
    action = "开启" if enable else "关闭"
    if result.get("status") == "ok":
        return f"已{action}全员禁言"
    return f"全员禁言{action}失败: {result.get('wording', '未知错误')}"


async def set_group_admin(ws, group_id, user_id, enable=True):
    """设置/取消管理员"""
    payload = {
        "action": "set_group_admin",
        "params": {
            "group_id": group_id,
            "user_id": user_id,
            "enable": enable,
        },
    }
    await ws.send(json.dumps(payload))
    resp = await ws.recv()
    result = json.loads(resp)
    action = "设置" if enable else "取消"
    if result.get("status") == "ok":
        return f"已{action}用户 {user_id} 的管理员权限"
    return f"管理员{action}失败: {result.get('wording', '未知错误')}"


async def get_group_info(ws, group_id):
    """获取群信息"""
    payload = {
        "action": "get_group_info",
        "params": {
            "group_id": group_id,
            "no_cache": False,
        },
    }
    await ws.send(json.dumps(payload))
    resp = await ws.recv()
    result = json.loads(resp)
    if result.get("status") == "ok":
        data = result["data"]
        return (
            f"群名称: {data['group_name']}\n"
            f"群号: {data['group_id']}\n"
            f"成员数: {data['member_count']}/{data['max_member_count']}"
        )
    return f"获取群信息失败: {result.get('wording', '未知错误')}"


async def get_member_info(ws, group_id, user_id):
    """获取群成员信息"""
    payload = {
        "action": "get_group_member_info",
        "params": {
            "group_id": group_id,
            "user_id": user_id,
        },
    }
    await ws.send(json.dumps(payload))
    resp = await ws.recv()
    result = json.loads(resp)
    if result.get("status") == "ok":
        data = result["data"]
        return (
            f"群名片: {data.get('card', '无')}\n"
            f"QQ: {data['user_id']}\n"
            f"昵称: {data['nickname']}\n"
            f"角色: {data['role']}\n"
            f"加群时间: {data.get('join_time', '未知')}\n"
            f"最后发言: {data.get('last_sent_time', '未知')}"
        )
    return f"获取群成员信息失败: {result.get('wording', '未知错误')}"


async def send_group_msg(ws, group_id, message):
    """发送群消息"""
    payload = {
        "action": "send_group_msg",
        "params": {
            "group_id": group_id,
            "message": str(message),
        },
    }
    await ws.send(json.dumps(payload))