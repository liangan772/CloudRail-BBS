"""分类。

TODO（按文档 6.2）：
- GET /categories  分类列表
"""

from fastapi import APIRouter

router = APIRouter(prefix="/categories", tags=["分类"])
