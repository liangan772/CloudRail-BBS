"""拉黑 / 屏蔽。

TODO（按文档 6.2 / 9.13）：
- POST /users/{id}/block  拉黑/取消拉黑（blocks 唯一索引 + block:set 缓存）
"""

from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["拉黑"])
