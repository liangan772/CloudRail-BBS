"""异步数据库会话基础设施。

- engine：基于配置的异步 SQLAlchemy engine（生产 asyncpg / 开发 sqlite+aiosqlite）
- get_db：FastAPI 依赖，每个请求一个会话
- init_db：应用启动时建表 + 种子数据（DB 不可用时优雅降级，不阻塞启动）
"""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import Base, Category

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    """FastAPI 依赖：提供请求级异步会话。"""
    async with async_session_factory() as session:
        yield session


DEFAULT_CATEGORIES = [
    ("技术交流", "编程、架构与开发经验分享"),
    ("生活闲聊", "生活琐事、树洞与日常交流"),
    ("站务公告", "社区公告与站务通知"),
]


async def _seed_categories() -> None:
    """初始化默认分类（仅首次）。"""
    async with async_session_factory() as session:
        count = await session.scalar(select(func.count()).select_from(Category))
        if count:
            return
        for i, (name, desc) in enumerate(DEFAULT_CATEGORIES):
            session.add(Category(name=name, description=desc, sort_order=i))
        await session.commit()
        logger.info("已初始化默认分类: %s", [c[0] for c in DEFAULT_CATEGORIES])


async def init_db() -> None:
    """启动时建表 + 种子数据（开发阶段用 create_all；正式迁移请使用 Alembic）。"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("数据库表结构检查/创建完成")
        await _seed_categories()
    except Exception as exc:  # noqa: BLE001
        logger.warning("数据库不可用，跳过建表（%s）；请启动 PostgreSQL 后重试", exc)
