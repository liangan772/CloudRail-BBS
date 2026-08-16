"""浏览足迹。

TODO（按文档 6.2）：
- GET    /users/me/history  浏览足迹（分页）
- DELETE /users/me/history  清空足迹
"""

from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["浏览足迹"])
