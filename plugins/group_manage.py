"""
群管理插件 (精简版)
撤回 / 禁言 / 发消息
"""
import json


async def delete_msg(ws, message_id):
    """撤回消息"""
    payload = {
        "action": "delete_msg",
        "params": {"message_id": message_id},
    }
    await ws.send(json.dumps(payload))
    resp = await ws.recv()
    result = json.loads(resp)
    return result.get("status") == "ok"


async def ban_user(ws, group_id, user_id, duration_seconds):
    """禁言用户 duration_seconds 秒, 0 表示解禁"""
    payload = {
        "action": "set_group_ban",
        "params": {
            "group_id": group_id,
            "user_id": user_id,
            "duration": duration_seconds,
        },
    }
    await ws.send(json.dumps(payload))
    resp = await ws.recv()
    result = json.loads(resp)
    return result.get("status") == "ok"


async def get_group_info(ws, group_id):
    """获取群信息"""
    payload = {
        "action": "get_group_info",
        "params": {"group_id": group_id, "no_cache": False},
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
    return "获取群信息失败"


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