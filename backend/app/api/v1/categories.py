"""分类。

- GET /categories  分类列表（文档 6.2）
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.services import content as content_service

router = APIRouter(prefix="/categories", tags=["分类"])


@router.get("", summary="分类列表")
async def list_categories(session: AsyncSession = Depends(get_db)) -> dict:
    return {"code": 0, "message": "ok", "data": await content_service.list_categories(session)}
