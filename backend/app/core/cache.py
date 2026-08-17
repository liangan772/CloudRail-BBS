"""缓存/存储层：Redis 优先，不可用时降级内存（开发/单实例）。

统一入口供验证码、限流、Refresh Token 吊销等使用：
- get_redis()：惰性创建 redis.asyncio 客户端并主动 ping 探测；
  探测失败后**永久降级内存**（避免每次请求重复尝试连接造成延迟），进程重启后重新探测
- MemoryStore：带 TTL 的进程内 dict（单实例降级用）
"""

import asyncio
import logging
import threading
import time
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis = None
_redis_failed = False


async def get_redis():
    """返回 redis.asyncio 客户端（主动探测；不可用返回 None 并永久降级内存）。"""
    global _redis, _redis_failed
    if _redis is not None:
        return _redis
    if _redis_failed:
        return None
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        # 主动探测：避免无 Redis 时每次调用都尝试连接造成延迟
        await asyncio.wait_for(client.ping(), timeout=1.5)
        _redis = client
        return _redis
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis 不可用，本次运行降级内存存储: %s", exc)
        _redis_failed = True
        return None


class MemoryStore:
    """带 TTL 的进程内键值存储（单实例降级）。"""

    def __init__(self) -> None:
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def _purge(self) -> None:
        now = time.time()
        expired = [k for k, (exp, _) in self._data.items() if exp < now]
        for k in expired:
            self._data.pop(k, None)

    def set(self, key: str, value: Any, ttl: int) -> None:
        with self._lock:
            self._purge()
            self._data[key] = (time.time() + ttl, value)

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            exp, value = item
            if exp < time.time():
                self._data.pop(key, None)
                return None
            return value

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def incr(self, key: str, ttl: int = 60) -> int:
        """原子自增（近似）；超过 TTL 重置。"""
        with self._lock:
            self._purge()
            item = self._data.get(key)
            if item is None or item[0] < time.time():
                self._data[key] = (time.time() + ttl, 1)
                return 1
            value = int(item[1]) + 1
            self._data[key] = (item[0], value)
            return value


memory_store = MemoryStore()
