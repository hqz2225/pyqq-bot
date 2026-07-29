"""
共享 WebSocket 连接和锁
避免 recv 并发冲突: 主循环和 API 调用共用同一把锁
锁在每次连接成功后由 connect_ws() 创建, 避免事件循环绑定错误
"""
import asyncio

ws = None
lock = None  # 由 connect_ws() 在连接成功后创建