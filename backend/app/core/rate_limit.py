"""限流器：Redis 优先（固定窗口），不可用时降级进程内计数。

使用方式：
    limiter = RateLimiter(limit=5, window=60)
    if not await limiter.allow("login:1.2.3.4"):
        raise HTTPException(429, ...)
"""

import logging

from app.core.cache import get_redis, memory_store

logger = logging.getLogger(__name__)


class RateLimiter:
    """固定窗口限流（窗口内允许 limit 次）。"""

    def __init__(self, limit: int, window: int = 60) -> None:
        self.limit = limit
        self.window = window

    async def allow(self, key: str) -> bool:
        """返回 True 放行；False 表示超限。"""
        redis = await get_redis()
        if redis is not None:
            try:
                rkey = f"rate:{key}"
                count = await redis.incr(rkey)
                if count == 1:
                    await redis.expire(rkey, self.window)
                return int(count) <= self.limit
            except Exception as exc:  # noqa: BLE001
                logger.warning("Redis 限流失败，降级内存: %s", exc)
        count = memory_store.incr(f"rate:{key}", ttl=self.window)
        return count <= self.limit
