"""草稿箱。

TODO（按文档 6.2 / 9.14）：
- GET    /drafts       我的草稿列表
- POST   /drafts       保存/更新草稿（upsert）
- DELETE /drafts/{id}  删除草稿
"""

from fastapi import APIRouter

router = APIRouter(prefix="/drafts", tags=["草稿"])
