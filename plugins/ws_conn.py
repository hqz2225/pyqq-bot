"""
共享 WebSocket 连接和锁
避免 recv 并发冲突: 主循环和 API 调用共用同一把锁
"""
import asyncio

ws = None
lock = asyncio.Lock()