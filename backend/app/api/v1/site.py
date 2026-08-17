"""站点配置公开接口。

- GET /site-config  前端启动配置（帖子图片开关等；数据库不可用时返回默认值）
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.services import site_config as site_config_service

router = APIRouter(prefix="/site-config", tags=["站点配置"])


@router.get("", summary="获取前端公开站点配置")
async def get_site_config(session: AsyncSession = Depends(get_db)) -> dict:
    return await site_config_service.get_public_config(session)
