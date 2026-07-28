"""
PyQQ Bot - 基于 NapCat OneBot v11 WebSocket 的 QQ 群管理机器人
连接方式: WebSocket 客户端 (主动连接 NapCat WebSocket 服务端)
"""
import asyncio
import json
import logging
import os
import signal
import subprocess
import sys

import websockets

from config import WS_URL, AUTO_GROUP_ID, UPDATE_CHECK_MINUTES, DATA_DIR, GIT_MIRROR
from bot import handle_event
from plugins.group_manage import send_group_msg

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("PyQQBot")

# 重连配置
RECONNECT_DELAY = 5
MAX_RECONNECT_DELAY = 60

# 共享 WebSocket 引用 (供更新检查器使用)
_ws_ref = [None]

# 记录上次 commit 的文件
_LAST_COMMIT_FILE = os.path.join(DATA_DIR, "last_commit.txt")


def _get_last_commit():
    """获取本地记录的 commit hash"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(_LAST_COMMIT_FILE):
        with open(_LAST_COMMIT_FILE, "r") as f:
            return f.read().strip()
    return None


def _save_last_commit(hash_val):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(_LAST_COMMIT_FILE, "w") as f:
        f.write(hash_val)


def _get_remote_hash():
    """获取 origin/master 最新 commit hash, 失败返回 None"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # 获取 origin URL
        url_result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=10,
            cwd=base_dir,
        )
        remote_url = url_result.stdout.strip()
        if GIT_MIRROR and remote_url:
            mirror_url = GIT_MIRROR + remote_url
        else:
            mirror_url = remote_url
        # 通过镜像 fetch
        subprocess.run(
            ["git", "fetch", mirror_url, "master"],
            capture_output=True, timeout=30,
            cwd=base_dir,
        )
        # 获取 FETCH_HEAD 的 hash
        result = subprocess.run(
            ["git", "rev-parse", "FETCH_HEAD"],
            capture_output=True, text=True, timeout=10,
            cwd=base_dir,
        )
        return result.stdout.strip()
    except Exception:
        return None


def _get_commit_summary():
    """获取本地落后于 remote 的 commit 摘要"""
    try:
        result = subprocess.run(
            ["git", "log", "HEAD..FETCH_HEAD", "--oneline", "-n", "5"],
            capture_output=True, text=True, timeout=10,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        return result.stdout.strip()
    except Exception:
        return ""


async def check_updates():
    """后台任务: 定期检查 GitHub 更新并通知"""
    # 首次启动记录当前 commit, 不通知
    current = _get_remote_hash()
    if current and not _get_last_commit():
        _save_last_commit(current)
        logger.info(f"更新检查器已就绪, 当前版本: {current[:8]}")

    while True:
        await asyncio.sleep(UPDATE_CHECK_MINUTES * 60)

        gid = AUTO_GROUP_ID
        if gid is None:
            continue

        remote_hash = _get_remote_hash()
        if not remote_hash:
            continue

        last_hash = _get_last_commit()
        if last_hash and remote_hash != last_hash:
            summary = _get_commit_summary()
            msg = f"检测到新版本更新!\n\n更新内容:\n{summary}\n\n发送 /更新 即可升级"
            try:
                await send_group_msg(gid, msg)
            except Exception as e:
                logger.error(f"发送更新通知到群 {gid} 失败: {e}")
            _save_last_commit(remote_hash)
            logger.info(f"已发送更新通知, 新版本: {remote_hash[:8]}")


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
                max_size=10 * 1024 * 1024,
            ) as ws:
                logger.info("已成功连接到 NapCat WebSocket!")
                delay = RECONNECT_DELAY
                _ws_ref[0] = ws  # 更新共享引用

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
        finally:
            _ws_ref[0] = None

        logger.info(f"{delay} 秒后重连...")
        await asyncio.sleep(delay)
        delay = min(delay * 2, MAX_RECONNECT_DELAY)


async def main():
    """主入口"""
    logger.info("PyQQ Bot 启动中...")
    logger.info(f"WebSocket 地址: {WS_URL}")

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def signal_handler():
        logger.info("收到退出信号，准备关闭...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            signal.signal(sig, lambda s, f: stop_event.set())

    # 启动 WebSocket 连接
    ws_task = asyncio.create_task(connect_ws())

    # 启动更新检查器
    update_task = asyncio.create_task(check_updates())

    await stop_event.wait()
    ws_task.cancel()
    update_task.cancel()
    try:
        await ws_task
    except asyncio.CancelledError:
        pass
    try:
        await update_task
    except asyncio.CancelledError:
        pass

    logger.info("PyQQ Bot 已停止")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("已手动停止")
        sys.exit(0)