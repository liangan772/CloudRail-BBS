"""举报。

TODO（按文档 6.2 / 9.13）：
- POST /reports  举报帖子/评论/用户（24h 内同目标限一次）
"""

from fastapi import APIRouter

router = APIRouter(prefix="/reports", tags=["举报"])
