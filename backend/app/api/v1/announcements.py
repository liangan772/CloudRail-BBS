"""公告中心。

TODO（按文档 6.2）：
- GET /announcements  公告列表（置顶优先）
"""

from fastapi import APIRouter

router = APIRouter(prefix="/announcements", tags=["公告"])
