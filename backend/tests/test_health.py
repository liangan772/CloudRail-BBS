"""健康检查与基础元信息测试。"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_root(client: AsyncClient) -> None:
    resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.json()["name"] == "CloudRail Forum API"


@pytest.mark.asyncio
async def test_api_router_mounted(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/categories")
    # 骨架阶段业务模块为空路由，应返回 404（路由已挂载）；非 500 即说明聚合正常
    assert resp.status_code == 404
