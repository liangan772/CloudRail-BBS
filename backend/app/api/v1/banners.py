"""轮播图（首页运营位）。

- GET /banners  首页轮播（启用且处于展示时段，按 sort_order 排序）
管理端 CRUD 见 api/v1/admin/banners.py。
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.banner import Banner

router = APIRouter(prefix="/banners", tags=["轮播图"])


@router.get("", summary="首页轮播图（启用且在展示时段内）")
async def list_active_banners(session: AsyncSession = Depends(get_db)) -> dict:
    now = datetime.now(timezone.utc)
    rows = (
        (
            await session.execute(
                select(Banner)
                .where(Banner.is_active.is_(True))
                .where(Banner.start_at.is_(None) | (Banner.start_at <= now))
                .where(Banner.end_at.is_(None) | (Banner.end_at >= now))
                .order_by(Banner.sort_order, Banner.id.desc())
            )
        )
        .scalars()
        .all()
    )
    return {
        "items": [
            {"id": b.id, "title": b.title, "image_url": b.image_url, "link_url": b.link_url}
            for b in rows
        ]
    }
