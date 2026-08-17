"""管理后台（角色 >= 2 管理员）。

安全加固（v0.1.0）：
- 管理写操作统一记录审计日志（admin_logs 表，见文档 5.2）
- 数据库异常不对外泄露（详情入日志，对外返回通用提示）

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

import logging

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, require_role
from app.models.admin_log import AdminLog
from app.services import site_config as site_config_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["管理后台"])


class SiteConfigUpdate(BaseModel):
    value: str = Field(min_length=0, max_length=255)
    description: str = Field(default="", max_length=255)


async def _log_admin(
    session: AsyncSession, admin: CurrentUser, action: str, target_type: str = "", target_id: str = "", detail: str = ""
) -> None:
    """管理操作审计留痕（写失败仅告警，不阻断主流程）。"""
    try:
        session.add(
            AdminLog(admin_id=admin.id, action=action, target_type=target_type, target_id=target_id, detail=detail)
        )
        await session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("审计日志写入失败: %s", exc)
        await session.rollback()


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
    admin: CurrentUser = Depends(require_role(2)),
) -> dict:
    try:
        result = await site_config_service.set_config(session, key, payload.value, payload.description)
    except Exception as exc:  # noqa: BLE001
        logger.exception("站点配置更新失败 key=%s: %s", key, exc)
        raise HTTPException(status_code=503, detail="数据库不可用，请稍后重试") from exc
    await _log_admin(
        session, admin, action="config.update", target_type="site_config", target_id=key, detail=f"{key}={payload.value}"
    )
    return result
