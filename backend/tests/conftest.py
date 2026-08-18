"""pytest 公共夹具。

- 每个测试使用独立的临时 SQLite 数据库（tmp_path），避免用例间数据污染；
- 放宽限流阈值（测试环境），避免登录/验证码共享窗口触发 429；
- 需在导入 app 前设置环境变量（settings 为模块级缓存）。
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_forum.db")
os.environ.setdefault("AUTH_RATE_LIMIT", "100000")
os.environ.setdefault("API_RATE_LIMIT", "1000000")
os.environ.setdefault("AUTH_RATE_WINDOW", "60")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.db import init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
async def client(tmp_path, monkeypatch) -> AsyncClient:
    """每用例独立临时数据库的测试客户端（app 共享，get_db 使用重建后的 session factory）。"""
    import app.core.db as db_module
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    db_path = tmp_path / "test_forum.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", db_url)

    # 重建模块级 engine/session factory（app.get_db 引用模块级变量，自动生效）
    await db_module.engine.dispose()
    db_module.engine = create_async_engine(db_url, echo=False)
    db_module.async_session_factory = async_sessionmaker(db_module.engine, expire_on_commit=False)

    # pytest 不触发 FastAPI lifespan，手动建表 + 种子数据（含敏感词库）
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
