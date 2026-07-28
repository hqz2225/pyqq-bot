"""
OneBot v11 HTTP API 调用模块
通过 HTTP 调用 NapCat API, 避免 WebSocket 响应与事件消息串扰
"""
import json
import urllib.request
import asyncio
import logging

from config import HTTP_URL, ACCESS_TOKEN

_logger = logging.getLogger("PyQQBot")


async def call_api(action, params):
    """调用 OneBot HTTP API, 返回完整响应 JSON"""
    url = f"{HTTP_URL}/{action}"
    data = json.dumps(params).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    def _do():
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            _logger.error(f"HTTP API 调用失败 [{action}]: {e}")
            return {"status": "failed", "retcode": -1, "error": str(e)}

    return await asyncio.to_thread(_do)