"""
PyQQ Bot - 基于 NapCat OneBot v11 WebSocket 的 QQ 群管理机器人
连接方式: WebSocket 客户端 (主动连接 NapCat WebSocket 服务端)
"""
import asyncio
import json
import logging
import signal
import sys

import websockets

from config import WS_URL
from bot import handle_event

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("PyQQBot")

# 重连配置
RECONNECT_DELAY = 5      # 重连间隔(秒)
MAX_RECONNECT_DELAY = 60  # 最大重连间隔(秒)


async def connect_ws():
    """连接 NapCat WebSocket 并处理消息"""
    delay = RECONNECT_DELAY
    logger.info(f"正在连接 NapCat WebSocket: {WS_URL}")

    while True:
        try:
            async with websockets.connect(
                WS_URL,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5,
                max_size=10 * 1024 * 1024,  # 10MB
            ) as ws:
                logger.info("已成功连接到 NapCat WebSocket!")
                delay = RECONNECT_DELAY  # 重置重连延迟

                # 消息循环
                async for raw_message in ws:
                    try:
                        event = json.loads(raw_message)
                        asyncio.create_task(handle_event(ws, event))
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON 解析失败: {e}")
                    except Exception as e:
                        logger.error(f"处理事件异常: {e}")

        except websockets.ConnectionClosed as e:
            logger.warning(f"WebSocket 连接关闭: {e}")
        except (OSError, ConnectionRefusedError, ConnectionResetError) as e:
            logger.error(f"连接失败: {e}")
        except asyncio.CancelledError:
            logger.info("机器人正在关闭...")
            break
        except Exception as e:
            logger.error(f"未知错误: {e}")

        # 重连逻辑
        logger.info(f"{delay} 秒后重连...")
        await asyncio.sleep(delay)
        delay = min(delay * 2, MAX_RECONNECT_DELAY)


async def main():
    """主入口"""
    logger.info("PyQQ Bot 启动中...")
    logger.info(f"WebSocket 地址: {WS_URL}")

    # 捕获退出信号
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def signal_handler():
        logger.info("收到退出信号，准备关闭...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows 不支持 add_signal_handler
            signal.signal(sig, lambda s, f: stop_event.set())

    # 启动 WebSocket 连接任务
    ws_task = asyncio.create_task(connect_ws())

    # 等待退出信号
    await stop_event
    ws_task.cancel()
    try:
        await ws_task
    except asyncio.CancelledError:
        pass

    logger.info("PyQQ Bot 已停止")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("已手动停止")
        sys.exit(0)