"""pytest 公共夹具。

- 测试使用独立 SQLite 测试库（test_forum.db），避免污染开发库
- 需在导入 app 前设置 DATABASE_URL（settings 为模块级缓存）
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_forum.db")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.db import init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
async def client() -> AsyncClient:
    # pytest 不触发 FastAPI lifespan，手动建表 + 种子数据
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
