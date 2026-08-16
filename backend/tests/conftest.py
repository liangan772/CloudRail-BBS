"""pytest 公共夹具。

骨架阶段：仅提供 app 客户端；数据库 / Redis 夹具在接入 ORM 后补充
（测试库 + alembic 迁移，见文档 11.3）。
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
