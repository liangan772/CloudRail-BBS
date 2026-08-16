"""评论。

TODO（按文档 6.2）：
- POST   /posts/{post_id}/comments  发表评论
- POST   /comments/{id}/reply       楼中楼回复
- DELETE /comments/{id}             删除评论
- POST   /comments/{id}/like        评论点赞
"""

from fastapi import APIRouter

router = APIRouter(prefix="/comments", tags=["评论"])
