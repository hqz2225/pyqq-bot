"""
群管理插件 (精简版)
撤回 / 禁言 / 发消息
通过 asyncio.Lock 保证 WebSocket 操作串行化, 避免并发 recv 错乱
"""
import asyncio
import json
import logging

_logger = logging.getLogger("PyQQBot")

# WebSocket 操作锁 (全局, 确保同一时间只有一个 send/recv 操作)
_ws_lock = asyncio.Lock()


async def delete_msg(ws, message_id):
    """撤回消息"""
    async with _ws_lock:
        payload = {
            "action": "delete_msg",
            "params": {"message_id": message_id},
        }
        await ws.send(json.dumps(payload))
        resp = await ws.recv()
        result = json.loads(resp)
        ok = result.get("status") == "ok"
        if not ok:
            _logger.warning(f"撤回消息失败: {result}")
        return ok


async def ban_user(ws, group_id, user_id, duration_seconds):
    """禁言用户 duration_seconds 秒, 0 表示解禁"""
    async with _ws_lock:
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
        ok = result.get("status") == "ok"
        if not ok:
            _logger.warning(f"禁言失败: {result}")
        return ok


async def get_group_info(ws, group_id):
    """获取群信息"""
    async with _ws_lock:
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
    async with _ws_lock:
        payload = {
            "action": "send_group_msg",
            "params": {
                "group_id": group_id,
                "message": str(message),
            },
        }
        await ws.send(json.dumps(payload))
        resp = await ws.recv()
        result = json.loads(resp)
        ok = result.get("status") == "ok"
        if not ok:
            _logger.warning(f"发送群消息失败: {result}")
        return ok