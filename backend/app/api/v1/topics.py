"""话题广场。

TODO（按文档 6.2）：
- GET  /topics/hot        热门话题（topic:hot 热度榜）
- GET  /topics/{id}/posts 话题下帖子（热门/最新）
- POST /topics/{id}/follow 关注/取关话题
"""

from fastapi import APIRouter

router = APIRouter(prefix="/topics", tags=["话题"])
