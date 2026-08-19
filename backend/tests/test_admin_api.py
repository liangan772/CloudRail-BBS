"""管理后台接口对接测试（用户/内容/举报/敏感词/轮播图/统计）。

测试策略（与 AI 审核测试一致）：
- 管理员直接插入数据库（role=2），不依赖注册顺序；
- 用例间通过唯一用户名/内容隔离，共享 conftest 测试库；
- 覆盖：统计概览、用户状态变更、帖子审核/置顶/加精、举报全流程（举报→队列→处理）、
  敏感词 CRUD 即时生效、轮播图 CRUD 与公开列表。
"""

import uuid

import pytest
from httpx import AsyncClient

from app.services import captcha as captcha_service


async def _captcha(client: AsyncClient) -> tuple[str, str]:
    resp = await client.get("/api/v1/auth/captcha")
    assert resp.status_code == 200
    data = resp.json()
    data = data.get("data") if isinstance(data.get("data"), dict) else data
    code = captcha_service.get_code_for_test(data["captcha_id"])
    assert code is not None
    return data["captcha_id"], code


async def _make_user(client: AsyncClient, *, role: int = 0) -> tuple[str, str]:
    """直接插库创建用户并登录，返回 (token, username)。"""
    from app.core.db import async_session_factory
    from app.models.user import User
    from app.services.auth import hash_password

    username = f"u_{uuid.uuid4().hex[:8]}"
    async with async_session_factory() as session:
        session.add(User(username=username, password_hash=hash_password("test1234"), role=role))
        await session.commit()
    captcha_id, code = await _captcha(client)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "test1234", "captcha_id": captcha_id, "captcha_code": code},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["tokens"]["access_token"], username


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
async def test_stats_overview(client: AsyncClient) -> None:
    """运营看板统计：结构完整、计数一致。"""
    admin_token, _ = await _make_user(client, role=2)
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await client.get("/api/v1/admin/stats/overview", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"users", "posts", "comments", "pending_audits", "pending_reports"}
    assert data["users"]["total"] >= 1
    assert data["posts"]["total"] >= 0


@pytest.mark.asyncio
async def test_user_status_management(client: AsyncClient) -> None:
    """用户管理：列表/搜索 + 禁言/封禁/解封；不能操作自己。"""
    admin_token, _ = await _make_user(client, role=2)
    user_token, username = await _make_user(client, role=0)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 列表包含新用户
    resp = await client.get(f"/api/v1/admin/users?keyword={username}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    target_id = data["items"][0]["id"]

    # 禁言 → 封禁 → 解封
    resp = await client.put(f"/api/v1/admin/users/{target_id}/status", json={"status": 1}, headers=headers)
    assert resp.status_code == 200 and resp.json()["status"] == 1
    resp = await client.put(f"/api/v1/admin/users/{target_id}/status", json={"status": 2}, headers=headers)
    assert resp.status_code == 200 and resp.json()["status"] == 2
    resp = await client.put(f"/api/v1/admin/users/{target_id}/status", json={"status": 0}, headers=headers)
    assert resp.status_code == 200 and resp.json()["status"] == 0

    # 普通用户无权限
    resp = await client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 403

    # 管理员不能操作自己（查自己 id 后尝试）
    me = (await client.get(f"/api/v1/admin/users?keyword={admin_token and ''}", headers=headers)).json()
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_post_management(client: AsyncClient) -> None:
    """内容管理：列表 + 下架/通过 + 置顶 + 加精。"""
    admin_token, _ = await _make_user(client, role=2)
    user_token, _ = await _make_user(client, role=0)
    headers = {"Authorization": f"Bearer {admin_token}"}

    post_id = await _create_post(client, user_token, "待管理帖子", "这是一篇普通内容")
    resp = await client.get(f"/api/v1/admin/posts?keyword=待管理", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1
    item = next(i for i in resp.json()["items"] if i["id"] == post_id)
    assert item["status"] == 0 and item["author"] is not None

    # 下架 → 前台 404
    resp = await client.put(f"/api/v1/admin/posts/{post_id}/review", json={"status": 1}, headers=headers)
    assert resp.status_code == 200 and resp.json()["status"] == 1
    assert (await client.get(f"/api/v1/posts/{post_id}")).status_code == 404

    # 通过 → 恢复可见
    resp = await client.put(f"/api/v1/admin/posts/{post_id}/review", json={"status": 0}, headers=headers)
    assert resp.status_code == 200 and resp.json()["status"] == 0
    assert (await client.get(f"/api/v1/posts/{post_id}")).status_code == 200

    # 置顶 + 加精
    resp = await client.put(f"/api/v1/admin/posts/{post_id}/pin", json={"value": True}, headers=headers)
    assert resp.status_code == 200 and resp.json()["is_pinned"] is True
    resp = await client.put(f"/api/v1/admin/posts/{post_id}/essence", json={"value": True}, headers=headers)
    assert resp.status_code == 200 and resp.json()["is_essence"] is True


@pytest.mark.asyncio
async def test_report_flow(client: AsyncClient) -> None:
    """举报全流程：用户举报 → 管理队列 → 删内容/封用户处理。"""
    admin_token, _ = await _make_user(client, role=2)
    user_a_token, _ = await _make_user(client, role=0)
    user_b_token, user_b_name = await _make_user(client, role=0)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    post_id = await _create_post(client, user_a_token, "被举报的帖子", "这是要被举报的内容")

    # 用户 B 举报帖子
    resp = await client.post(
        "/api/v1/reports",
        json={"target_type": "post", "target_id": post_id, "reason": "广告刷屏"},
        headers={"Authorization": f"Bearer {user_b_token}"},
    )
    assert resp.status_code == 200
    report_id = resp.json()["id"]

    # 重复举报被限流（24h 内同目标一次）
    resp = await client.post(
        "/api/v1/reports",
        json={"target_type": "post", "target_id": post_id, "reason": "再次举报"},
        headers={"Authorization": f"Bearer {user_b_token}"},
    )
    assert resp.status_code == 429

    # 管理队列可见
    resp = await client.get("/api/v1/admin/reports?status=0", headers=admin_headers)
    assert resp.status_code == 200
    item = next(i for i in resp.json()["items"] if i["id"] == report_id)
    assert item["target_summary"] == "被举报的帖子"

    # 处理：删除内容 → 帖子前台 404
    resp = await client.put(f"/api/v1/admin/reports/{report_id}", json={"action": "remove"}, headers=admin_headers)
    assert resp.status_code == 200 and resp.json()["status"] == 1
    assert (await client.get(f"/api/v1/posts/{post_id}")).status_code == 404

    # 再举报一个用户 → 目标不存在（404）
    resp = await client.post(
        "/api/v1/reports",
        json={"target_type": "user", "target_id": 99999999, "reason": "恶意行为"},
        headers={"Authorization": f"Bearer {user_a_token}"},
    )
    assert resp.status_code == 404  # 目标不存在

    # 举报用户 B 并封禁
    from app.core.db import async_session_factory
    from app.models.user import User
    from sqlalchemy import select

    async with async_session_factory() as session:
        target_user = (
            await session.execute(select(User).where(User.username == user_b_name))
        ).scalar_one()
        target_user_id = target_user.id
    resp = await client.post(
        "/api/v1/reports",
        json={"target_type": "user", "target_id": target_user_id, "reason": "辱骂"},
        headers={"Authorization": f"Bearer {user_a_token}"},
    )
    assert resp.status_code == 200
    report2_id = resp.json()["id"]
    resp = await client.put(
        f"/api/v1/admin/reports/{report2_id}", json={"action": "ban_user"}, headers=admin_headers
    )
    assert resp.status_code == 200
    async with async_session_factory() as session:
        user_b = await session.get(User, target_user_id)
        assert user_b is not None and user_b.status == 2
        
@pytest.mark.asyncio
async def test_user_status_management(client: AsyncClient) -> None:
    """用户管理：列表/搜索 + 禁言/封禁/解封；不能操作自己。"""
    admin_token, admin_name = await _make_user(client, role=2)
    user_token, username = await _make_user(client, role=0)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 列表包含新用户
    resp = await client.get(f"/api/v1/admin/users?keyword={username}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    target_id = data["items"][0]["id"]

    # 禁言 → 封禁 → 解封
    resp = await client.put(f"/api/v1/admin/users/{target_id}/status", json={"status": 1}, headers=headers)
    assert resp.status_code == 200 and resp.json()["status"] == 1
    resp = await client.put(f"/api/v1/admin/users/{target_id}/status", json={"status": 2}, headers=headers)
    assert resp.status_code == 200 and resp.json()["status"] == 2
    resp = await client.put(f"/api/v1/admin/users/{target_id}/status", json={"status": 0}, headers=headers)
    assert resp.status_code == 200 and resp.json()["status"] == 0

    # 普通用户无权限
    resp = await client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 403

    # 管理员不能操作自己
    me = (await client.get(f"/api/v1/admin/users?keyword={admin_name}", headers=headers)).json()
    my_id = me["items"][0]["id"]
    resp = await client.put(f"/api/v1/admin/users/{my_id}/status", json={"status": 1}, headers=headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_sensitive_words_crud(client: AsyncClient) -> None:
    """敏感词管理：列表 → 新增即时拦截 → 删除恢复。"""
    from app.services import sensitive as sensitive_service

    admin_token, _ = await _make_user(client, role=2)
    headers = {"Authorization": f"Bearer {admin_token}"}

    word = f"测试敏感词{uuid.uuid4().hex[:4]}"
    resp = await client.post("/api/v1/admin/sensitive-words", json={"word": word}, headers=headers)
    assert resp.status_code == 200
    word_id = resp.json()["id"]

    # DFA 即时生效
    assert sensitive_service.sensitive_filter.contains(f"这是{word}内容") is True

    resp = await client.get("/api/v1/admin/sensitive-words", headers=headers)
    assert resp.status_code == 200
    assert any(w["id"] == word_id for w in resp.json()["items"])

    # 重复添加 400
    resp = await client.post("/api/v1/admin/sensitive-words", json={"word": word}, headers=headers)
    assert resp.status_code == 400

    # 删除后不再拦截
    resp = await client.delete(f"/api/v1/admin/sensitive-words/{word_id}", headers=headers)
    assert resp.status_code == 200
    assert sensitive_service.sensitive_filter.contains(f"这是{word}内容") is False


@pytest.mark.asyncio
async def test_banner_crud_and_public(client: AsyncClient) -> None:
    """轮播图管理：CRUD + 公开列表只返回启用项。"""
    admin_token, _ = await _make_user(client, role=2)
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = await client.post(
        "/api/v1/admin/banners",
        json={"title": "活动横幅", "image_url": "https://cdn.example.com/banner.jpg", "link_url": "/topic/1", "sort_order": 1},
        headers=headers,
    )
    assert resp.status_code == 200
    banner_id = resp.json()["id"]

    # 公开列表可见
    resp = await client.get("/api/v1/banners")
    assert resp.status_code == 200
    assert any(b["id"] == banner_id for b in resp.json()["items"])

    # 停用后公开列表不可见，管理列表仍可见
    resp = await client.put(
        f"/api/v1/admin/banners/{banner_id}",
        json={"title": "活动横幅", "image_url": "https://cdn.example.com/banner.jpg", "link_url": "", "sort_order": 1, "is_active": False},
        headers=headers,
    )
    assert resp.status_code == 200 and resp.json()["is_active"] is False
    resp = await client.get("/api/v1/banners")
    assert all(b["id"] != banner_id for b in resp.json()["items"])
    resp = await client.get("/api/v1/admin/banners", headers=headers)
    assert any(b["id"] == banner_id for b in resp.json()["items"])

    # 删除
    resp = await client.delete(f"/api/v1/admin/banners/{banner_id}", headers=headers)
    assert resp.status_code == 200
    resp = await client.get("/api/v1/admin/banners", headers=headers)
    assert all(b["id"] != banner_id for b in resp.json()["items"])
