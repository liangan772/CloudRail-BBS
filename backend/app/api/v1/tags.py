"""标签 / 话题。

TODO（按文档 6.2）：
- GET /tags            热门标签
- GET /tags/{id}/posts 标签下帖子
"""

from fastapi import APIRouter

router = APIRouter(prefix="/tags", tags=["标签"])
