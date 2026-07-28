"""
群管理插件
撤回 / 禁言 / 发消息 / 群信息
通过 HTTP API 调用, 不依赖 WebSocket, 无响应串扰问题
"""
import logging

from plugins.api import call_api

_logger = logging.getLogger("PyQQBot")


async def delete_msg(message_id):
    """撤回消息"""
    result = await call_api("delete_msg", {"message_id": message_id})
    ok = result.get("status") == "ok"
    if not ok:
        _logger.warning(f"撤回消息失败: {result}")
    return ok


async def ban_user(group_id, user_id, duration_seconds):
    """禁言用户 duration_seconds 秒, 0 表示解禁"""
    result = await call_api("set_group_ban", {
        "group_id": group_id,
        "user_id": user_id,
        "duration": duration_seconds,
    })
    ok = result.get("status") == "ok"
    if not ok:
        _logger.warning(f"禁言失败: {result}")
    return ok


async def get_group_info(group_id):
    """获取群信息"""
    result = await call_api("get_group_info", {
        "group_id": group_id, "no_cache": False,
    })
    if result.get("status") == "ok":
        data = result["data"]
        return (
            f"群名称: {data['group_name']}\n"
            f"群号: {data['group_id']}\n"
            f"成员数: {data['member_count']}/{data['max_member_count']}"
        )
    return "获取群信息失败"


async def send_group_msg(group_id, message):
    """发送群消息"""
    result = await call_api("send_group_msg", {
        "group_id": group_id,
        "message": str(message),
    })
    ok = result.get("status") == "ok"
    if not ok:
        _logger.warning(f"发送群消息失败: {result}")
    return ok