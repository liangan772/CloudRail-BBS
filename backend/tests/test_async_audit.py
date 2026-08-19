"""异步 AI 审核（单容器后台任务模式）测试。

验证 AI_AUDIT_MODE=async 时：发帖 → 进程内后台任务执行 AI 初审
→ 结论落库（pending 人工复审队列）→ reject 自动下架。
"""

import asyncio
import uuid

import pytest
from httpx import AsyncClient

from app.services import captcha as captcha_service


@pytest.fixture
def enable_mock_async_ai():
    """启用 mock AI + async 审核模式（后台任务）。"""
    from app.core.config import settings

    old = (settings.ai_enabled, settings.ai_mode, settings.ai_audit_mode)
    settings.ai_enabled = True
    settings.ai_mode = "mock"
    settings.ai_audit_mode = "async"
    yield
    settings.ai_enabled, settings.ai_mode, settings.ai_audit_mode = old


async def _captcha(client: AsyncClient) -> tuple[str, str]:
    resp = await client.get("/api/v1/auth/captcha")
    data = resp.json()
    data = data.get("data") if isinstance(data.get("data"), dict) else data
    code = captcha_service.get_code_for_test(data["captcha_id"])
    assert code is not None
    return data["captcha_id"], code


async def _make_admin(client: AsyncClient) -> str:
    from app.core.db import async_session_factory
    from app.models.user import User
    from app.services.auth import hash_password

    username = f"a_{uuid.uuid4().hex[:8]}"
    async with async_session_factory() as session:
        session.add(User(username=username, password_hash=hash_password("test1234"), role=2))
        await session.commit()
    captcha_id, code = await _captcha(client)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "test1234", "captcha_id": captcha_id, "captcha_code": code},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["tokens"]["access_token"]


@pytest.mark.asyncio
async def test_async_audit_background_task(client: AsyncClient, enable_mock_async_ai) -> None:
    """async 模式：后台任务完成初审落库 + reject 自动下架（单容器无 Celery）。"""
    from sqlalchemy import select

    from app.core.db import async_session_factory
    from app.models.audit import AuditRecord
    from app.models.post import Post

    token = await _make_admin(client)
    captcha_id, code = await _captcha(client)
    resp = await client.post(
        "/api/v1/posts",
        json={
            "title": "async 审核测试",
            "content": "包含违禁词测试的内容",
            "category_id": 1,
            "captcha_id": captcha_id,
            "captcha_code": code,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    post_id = resp.json()["data"]["id"]

    # 后台任务异步执行：轮询等待落库（mock 模式毫秒级完成）
    for _ in range(20):
        await asyncio.sleep(0.05)
        async with async_session_factory() as session:
            recs = (
                (await session.execute(select(AuditRecord).where(AuditRecord.target_id == post_id)))
                .scalars()
                .all()
            )
            if recs:
                break
    assert recs, "后台审核任务未落库"
    record = recs[0]
    assert record.result == "reject" and record.human_status == "pending"

    # reject 自动下架
    async with async_session_factory() as session:
        post = await session.get(Post, post_id)
        assert post is not None and post.status == 1
    assert (await client.get(f"/api/v1/posts/{post_id}")).status_code == 404
