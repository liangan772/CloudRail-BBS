"""AI 审核（两级审核：AI 初审 + 人工复审）测试 —— 新测试方式。

测试策略（与实现配套）：
- AI 初审使用 AI_MODE=mock 确定性模式：不发起任何网络请求，
  内容含「违禁词测试」→ reject；含「擦边测试」→ review；其他 → pass；
  图片 URL 含 bad → reject；含 sus → review。
- 管理员账号直接插入数据库（role=2），不依赖「首用户为管理员」的注册顺序；
- 用例间通过唯一用户名隔离，共享 conftest 测试库。
"""

import uuid

import pytest
from httpx import AsyncClient

from app.services import captcha as captcha_service
from app.services.audit import AIAuditService, AuditError, extract_image_urls

# ---------- 服务层单元测试 ----------


def test_extract_image_urls() -> None:
    content = (
        "看这张图 ![风景](https://cdn.example.com/a.jpg) 和 "
        '<img src="https://cdn.example.com/b.png" />，重复的 ![重复](https://cdn.example.com/a.jpg)'
    )
    assert extract_image_urls(content) == [
        "https://cdn.example.com/a.jpg",
        "https://cdn.example.com/b.png",
    ]


def test_extract_image_urls_max() -> None:
    content = "".join(f"![img{i}](https://cdn.example.com/{i}.jpg)\n" for i in range(6))
    assert len(extract_image_urls(content, max_images=4)) == 4


def test_merge_worst() -> None:
    service = AIAuditService.__new__(AIAuditService)
    merged = service._merge(
        [
            {"result": "pass", "score": 10, "categories": [], "reason": "", "model": "m"},
            {"result": "review", "score": 60, "categories": ["擦边"], "reason": "x", "model": "m"},
        ]
    )
    assert merged["result"] == "review"
    assert merged["score"] == 60

    merged = service._merge(
        [
            {"result": "review", "score": 60, "categories": ["擦边"], "reason": "x", "model": "m"},
            {"result": "reject", "score": 95, "categories": ["色情"], "reason": "y", "model": "m"},
        ]
    )
    assert merged["result"] == "reject"
    assert merged["categories"] == ["擦边", "色情"]


def test_parse_lenient() -> None:
    """视觉模型宽容解析：纯 JSON / 带前后缀文本的 JSON 块均可解析。"""
    service = AIAuditService.__new__(AIAuditService)
    service.model = "test-model"

    pure = service._parse_lenient(
        {"choices": [{"message": {"content": '{"result":"reject","score":90,"categories":["色情"],"reason":"x"}'}}]}
    )
    assert pure["result"] == "reject" and pure["score"] == 90.0

    wrapped = service._parse_lenient(
        {
            "choices": [
                {
                    "message": {
                        "content": '好的，以下是审核结果：\n```json\n{"result":"review","score":60,"categories":["擦边"],"reason":"y"}\n```\n'
                    }
                }
            ]
        }
    )
    assert wrapped["result"] == "review" and wrapped["categories"] == ["擦边"]

    with pytest.raises(AuditError):
        service._parse_lenient({"choices": [{"message": {"content": "没有 JSON 的回复"}}]})


def test_mock_mode_deterministic() -> None:
    """mock 模式：确定性结论，不依赖网络与 Key。"""
    from app.core.config import settings

    settings.ai_enabled = True
    settings.ai_mode = "mock"
    try:
        service = AIAuditService()
        assert service.enabled is True
        assert service.is_mock is True

        assert service.audit_text_sync("这是一篇普通内容")["result"] == "pass"
        assert service.audit_text_sync("这篇内容有点擦边测试")["result"] == "review"
        assert service.audit_text_sync("包含违禁词测试的内容")["result"] == "reject"

        assert service.audit_image_sync("https://cdn.example.com/bad.jpg")["result"] == "reject"
        assert service.audit_image_sync("https://cdn.example.com/sus.png")["result"] == "review"
        assert service.audit_image_sync("https://cdn.example.com/ok.jpg")["result"] == "pass"
    finally:
        settings.ai_enabled = False
        settings.ai_mode = "llm"


def test_audit_text_requires_enabled() -> None:
    """未启用 AI 时抛 AuditError（接口层收敛为 502）。"""
    from app.core.config import settings

    settings.ai_enabled = False
    settings.ai_mode = "llm"
    service = AIAuditService()
    with pytest.raises(AuditError):
        service.audit_text_sync("内容")


# ---------- 端到端：两级审核全链路 ----------


@pytest.fixture
def enable_mock_ai():
    """启用 mock AI（sync 模式）：测试结束自动恢复。"""
    from app.core.config import settings

    old = (settings.ai_enabled, settings.ai_mode, settings.ai_audit_mode)
    settings.ai_enabled = True
    settings.ai_mode = "mock"
    settings.ai_audit_mode = "sync"
    yield
    settings.ai_enabled, settings.ai_mode, settings.ai_audit_mode = old


async def _captcha(client: AsyncClient) -> tuple[str, str]:
    resp = await client.get("/api/v1/auth/captcha")
    assert resp.status_code == 200
    data = resp.json()
    data = data.get("data") if isinstance(data.get("data"), dict) else data
    code = captcha_service.get_code_for_test(data["captcha_id"])
    assert code is not None
    return data["captcha_id"], code


async def _make_admin(client: AsyncClient) -> str:
    """直接插入管理员（role=2）并登录，避免依赖注册顺序。"""
    from app.core.db import async_session_factory
    from app.models.user import User
    from app.services.auth import hash_password

    username = f"admin_{uuid.uuid4().hex[:8]}"
    async with async_session_factory() as session:
        session.add(
            User(username=username, password_hash=hash_password("test1234"), role=2)
        )
        await session.commit()
    captcha_id, code = await _captcha(client)
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": "test1234",
            "captcha_id": captcha_id,
            "captcha_code": code,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["tokens"]["access_token"]


async def _create_post(client: AsyncClient, token: str, title: str, content: str) -> int:
    captcha_id, code = await _captcha(client)
    resp = await client.post(
        "/api/v1/posts",
        json={
            "title": title,
            "content": content,
            "category_id": 1,
            "captcha_id": captcha_id,
            "captcha_code": code,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["id"]


@pytest.mark.asyncio
async def test_audit_api_requires_login(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/audit/text", json={"content": "测试"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_audit_api_mock(client: AsyncClient, enable_mock_ai) -> None:
    """登录后调用三个同步审核接口（mock 模式）。"""
    token = await _make_admin(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/audit/text", json={"content": "擦边测试内容"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == "review"

    resp = await client.post(
        "/api/v1/audit/image",
        json={"media_url": "https://cdn.example.com/bad.jpg"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == "reject"
    assert data["media_url"] == "https://cdn.example.com/bad.jpg"

    resp = await client.post(
        "/api/v1/audit/post",
        json={
            "title": "带图帖子",
            "content": "正文 ![图](https://cdn.example.com/sus.png) 有点擦边测试",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # 图片 review + 文本 review → 整体 review，且返回图片独立结果
    assert data["result"] == "review"
    assert data["image_results"] and data["image_results"][0]["result"] == "review"


@pytest.mark.asyncio
async def test_review_flow_full_chain(client: AsyncClient, enable_mock_ai) -> None:
    """两级审核全链路：发帖 → AI 初审落库（待复审）→ 人工驳回下架 → 人工通过恢复。"""
    from sqlalchemy import select

    from app.core.db import async_session_factory
    from app.models.audit import AuditRecord
    from app.models.post import Post

    token = await _make_admin(client)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. 发「擦边」帖：先发后审，AI 初审 review → 落库 pending，帖子保持可见
    post_id = await _create_post(client, token, "疑似擦边帖", "这个内容有点擦边测试")
    detail = await client.get(f"/api/v1/posts/{post_id}")
    assert detail.status_code == 200  # 先发后审：内容立即可见

    async with async_session_factory() as session:
        record = (
            await session.execute(
                select(AuditRecord).where(AuditRecord.target_type == "post", AuditRecord.target_id == post_id)
            )
        ).scalar_one()
        assert record.result == "review"
        assert record.human_status == "pending"
        record_id = record.id

    # 2. 复审队列可见该记录
    resp = await client.get("/api/v1/admin/audits?human_status=pending", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    item = next(i for i in data["items"] if i["id"] == record_id)
    assert item["result"] == "review" and item["human_status"] == "pending"

    # 3. 人工驳回 → 帖子下架（详情 404），记录复审信息
    resp = await client.put(
        f"/api/v1/admin/audits/{record_id}/review",
        json={"action": "rejected", "note": "人工确认擦边，驳回"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["human_status"] == "rejected"
    assert (await client.get(f"/api/v1/posts/{post_id}")).status_code == 404
    async with async_session_factory() as session:
        post = await session.get(Post, post_id)
        assert post is not None and post.status == 1

    # 4. 重复复审被拒绝
    resp = await client.put(
        f"/api/v1/admin/audits/{record_id}/review", json={"action": "approved"}, headers=headers
    )
    assert resp.status_code == 400

    # 5. 发「违禁词」帖：AI 初审 reject → 自动下架（等待人工终审）
    post2_id = await _create_post(client, token, "违规帖", "包含违禁词测试的内容")
    assert (await client.get(f"/api/v1/posts/{post2_id}")).status_code == 404

    # 6. 管理员人工通过 → 帖子恢复可见
    async with async_session_factory() as session:
        record2 = (
            await session.execute(
                select(AuditRecord).where(AuditRecord.target_type == "post", AuditRecord.target_id == post2_id)
            )
        ).scalar_one()
        record2_id = record2.id
    resp = await client.put(
        f"/api/v1/admin/audits/{record2_id}/review",
        json={"action": "approved", "note": "人工确认无问题，放行"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert (await client.get(f"/api/v1/posts/{post2_id}")).status_code == 200

    # 7. 状态过滤：已驳回 / 已通过 / 全部可见
    resp = await client.get("/api/v1/admin/audits?human_status=rejected", headers=headers)
    assert resp.json()["total"] >= 1
    resp = await client.get("/api/v1/admin/audits?human_status=all", headers=headers)
    assert resp.json()["total"] >= 2


@pytest.mark.asyncio
async def test_review_requires_admin(client: AsyncClient) -> None:
    """普通用户无法访问复审队列（403）。"""
    from app.core.db import async_session_factory
    from app.models.user import User
    from app.services.auth import hash_password

    username = f"user_{uuid.uuid4().hex[:8]}"
    async with async_session_factory() as session:
        session.add(User(username=username, password_hash=hash_password("test1234"), role=0))
        await session.commit()
    captcha_id, code = await _captcha(client)
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": "test1234",
            "captcha_id": captcha_id,
            "captcha_code": code,
        },
    )
    assert resp.status_code == 200
    user_token = resp.json()["data"]["tokens"]["access_token"]

    resp = await client.get("/api/v1/admin/audits", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 403

    admin_token = await _make_admin(client)
    resp = await client.get("/api/v1/admin/audits", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
