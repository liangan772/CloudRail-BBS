"""投票。

TODO（按文档 6.2 / 9.14）：
- GET  /posts/{id}/poll  投票详情与结果
- POST /posts/{id}/vote  投票（poll_votes 唯一索引一人一票）
"""

from fastapi import APIRouter

router = APIRouter(prefix="/posts", tags=["投票"])
