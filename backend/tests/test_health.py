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
    # 分类接口已实现（种子数据），应返回 200 且含默认分类
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 3
    assert data[0]["name"] == "技术交流"
