"""轮播图（运营位）。

TODO（按文档 6.2 / 9.12）：
- GET /banners  首页轮播（有效时段内，banner:list 缓存）
"""

from fastapi import APIRouter

router = APIRouter(prefix="/banners", tags=["轮播图"])
