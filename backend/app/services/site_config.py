"""站点配置服务：默认值、读取（DB 不可用时降级）、更新。"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.site_config import SiteConfig

logger = logging.getLogger(__name__)

# 默认配置（数据库不可用或未配置时使用）
DEFAULT_CONFIG: dict[str, str] = {
    "post_image_enabled": "true",
    "site_name": "CloudRail 论坛",
}

# 前端公开配置项（仅暴露需要的字段）
PUBLIC_KEYS: set[str] = {"post_image_enabled", "site_name"}


async def get_all_config(session: AsyncSession) -> dict[str, dict[str, str]]:
    """返回全部配置（key -> {value, description}），数据库不可用时仅返回默认值。"""
    result: dict[str, dict[str, str]] = {
        key: {"value": value, "description": _DEFAULT_DESC.get(key, "")}
        for key, value in DEFAULT_CONFIG.items()
    }
    try:
        rows = (await session.execute(select(SiteConfig))).scalars().all()
    except Exception as exc:  # noqa: BLE001
        logger.warning("读取站点配置失败，使用默认值: %s", exc)
        return result
    for row in rows:
        result[row.key] = {"value": row.value, "description": row.description}
    return result


async def get_public_config(session: AsyncSession) -> dict[str, Any]:
    """返回前端公开配置（布尔值已转换）。"""
    raw = await get_all_config(session)
    out: dict[str, Any] = {}
    for key in PUBLIC_KEYS:
        item = raw.get(key)
        if item is None:
            continue
        value: Any = item["value"]
        if value.lower() in ("true", "false"):
            value = value.lower() == "true"
        out[key] = value
    return out


async def set_config(session: AsyncSession, key: str, value: str, description: str = "") -> dict[str, str]:
    """更新配置（不存在则创建）。"""
    config = await session.get(SiteConfig, key)
    if config is None:
        config = SiteConfig(key=key, value=value, description=description)
        session.add(config)
    else:
        config.value = value
        if description:
            config.description = description
    await session.commit()
    return {"key": key, "value": value, "description": config.description}


_DEFAULT_DESC: dict[str, str] = {
    "post_image_enabled": "帖子是否允许展示图片（帖子卡片封面与详情图片）",
    "site_name": "站点名称（展示于页头与标题）",
}
