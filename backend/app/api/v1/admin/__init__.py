"""管理后台（角色 >= 2 管理员）。

TODO（按文档 6.2）：
- GET    /admin/stats/overview            运营看板
- GET    /admin/users                      用户管理
- PUT    /admin/users/{id}/status          禁言/封禁/解封
- GET    /admin/posts                      审核列表
- PUT    /admin/posts/{id}/review          审核
- PUT    /admin/posts/{id}/pin|essence     置顶/加精
- POST   /admin/categories                 分类管理
- GET/POST/DELETE /admin/sensitive-words   敏感词管理
- GET/PUT /admin/config/gamification       激励配置
- GET/POST/PUT/DELETE /admin/banners       轮播图管理
- GET    /admin/reports                    举报队列
- PUT    /admin/reports/{id}               处理举报
- GET/PUT /admin/topics                    话题运营
"""

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_role
from app.services import site_config as site_config_service

router = APIRouter(prefix="/admin", tags=["管理后台"])


class SiteConfigUpdate(BaseModel):
    value: str = Field(min_length=0, max_length=255)
    description: str = Field(default="", max_length=255)


@router.get("/config/site", summary="站点配置列表（含描述）")
async def list_site_config(
    session: AsyncSession = Depends(get_db),
    _admin=Depends(require_role(2)),
) -> dict:
    return await site_config_service.get_all_config(session)


@router.put("/config/site/{key}", summary="更新站点配置")
async def update_site_config(
    payload: SiteConfigUpdate,
    key: str = Path(min_length=1, max_length=64),
    session: AsyncSession = Depends(get_db),
    _admin=Depends(require_role(2)),
) -> dict:
    try:
        return await site_config_service.set_config(session, key, payload.value, payload.description)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"数据库不可用：{exc}") from exc
