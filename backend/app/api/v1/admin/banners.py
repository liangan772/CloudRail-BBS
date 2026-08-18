"""管理后台：轮播图管理（banners CRUD）。

- GET    /admin/banners        全量列表（含未启用）
- POST   /admin/banners        新增
- PUT    /admin/banners/{id}   更新
- DELETE /admin/banners/{id}   删除
公开列表见 api/v1/banners.py（GET /banners，仅有效时段且启用）。
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, require_role
from app.models.admin_log import AdminLog
from app.models.banner import Banner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/banners", tags=["管理后台"])


class BannerPayload(BaseModel):
    title: str = Field(min_length=1, max_length=64)
    image_url: str = Field(min_length=1, max_length=512)
    link_url: str = Field(default="", max_length=512)
    sort_order: int = Field(default=0)
    is_active: bool = True
    start_at: datetime | None = None
    end_at: datetime | None = None


def _banner_out(banner: Banner) -> dict:
    return {
        "id": banner.id,
        "title": banner.title,
        "image_url": banner.image_url,
        "link_url": banner.link_url,
        "sort_order": banner.sort_order,
        "is_active": banner.is_active,
        "start_at": banner.start_at.isoformat() if banner.start_at else None,
        "end_at": banner.end_at.isoformat() if banner.end_at else None,
        "created_at": banner.created_at.isoformat() if banner.created_at else None,
    }


@router.get("", summary="轮播图列表（管理端全量）")
async def list_banners(
    session: AsyncSession = Depends(get_db),
    _admin: CurrentUser = Depends(require_role(2)),
) -> dict:
    rows = (
        (await session.execute(select(Banner).order_by(Banner.sort_order, Banner.id.desc()))).scalars().all()
    )
    return {"total": len(rows), "items": [_banner_out(b) for b in rows]}


@router.post("", summary="新增轮播图")
async def create_banner(
    payload: BannerPayload,
    session: AsyncSession = Depends(get_db),
    admin: CurrentUser = Depends(require_role(2)),
) -> dict:
    banner = Banner(**payload.model_dump())
    session.add(banner)
    await session.commit()
    await session.refresh(banner)
    await _log(session, admin, "banner.create", str(banner.id), banner.title)
    return _banner_out(banner)


@router.put("/{banner_id}", summary="更新轮播图")
async def update_banner(
    payload: BannerPayload,
    banner_id: int = Path(ge=1),
    session: AsyncSession = Depends(get_db),
    admin: CurrentUser = Depends(require_role(2)),
) -> dict:
    banner = await session.get(Banner, banner_id)
    if banner is None:
        raise HTTPException(status_code=404, detail="轮播图不存在")
    for key, value in payload.model_dump().items():
        setattr(banner, key, value)
    await session.commit()
    await _log(session, admin, "banner.update", str(banner_id), banner.title)
    return _banner_out(banner)


@router.delete("/{banner_id}", summary="删除轮播图")
async def delete_banner(
    banner_id: int = Path(ge=1),
    session: AsyncSession = Depends(get_db),
    admin: CurrentUser = Depends(require_role(2)),
) -> dict:
    banner = await session.get(Banner, banner_id)
    if banner is None:
        raise HTTPException(status_code=404, detail="轮播图不存在")
    title = banner.title
    await session.delete(banner)
    await session.commit()
    await _log(session, admin, "banner.delete", str(banner_id), title)
    return {"deleted": True, "id": banner_id}


async def _log(session: AsyncSession, admin: CurrentUser, action: str, target_id: str, detail: str) -> None:
    try:
        session.add(
            AdminLog(admin_id=admin.id, action=action, target_type="banner", target_id=target_id, detail=detail)
        )
        await session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("审计日志写入失败: %s", exc)
        await session.rollback()
