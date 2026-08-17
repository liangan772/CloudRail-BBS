"""端到端联调：验证码 → 注册(首用户管理员) → 登录 → 发帖 → 列表 → 详情 → 评论 → 后台配置。"""

import asyncio
import sys

from httpx import ASGITransport, AsyncClient

sys.path.insert(0, "backend")

from app.core.db import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services import captcha as cap  # noqa: E402


def get_code(captcha_id: str) -> str:
    return cap._store[captcha_id]["code"]


async def main() -> None:
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # 1. 验证码
        cap1 = cap.create_captcha()
        r = await c.post(
            "/api/v1/auth/register",
            json={
                "username": "admin",
                "password": "secret123",
                "email": "admin@example.com",
                "captcha_id": cap1["captcha_id"],
                "captcha_code": get_code(cap1["captcha_id"]),
            },
        )
        assert r.status_code == 200 and r.json()["code"] == 0, r.text
        data = r.json()["data"]
        assert data["user"]["role"] == 2, "首用户应为管理员"
        token = data["tokens"]["access_token"]
        print("1. 注册(首用户管理员) OK:", data["user"]["username"], "role=", data["user"]["role"])

        # 2. 错误验证码应被拒
        cap2 = cap.create_captcha()
        r = await c.post(
            "/api/v1/auth/register",
            json={
                "username": "user2",
                "password": "secret123",
                "captcha_id": cap2["captcha_id"],
                "captcha_code": "WRONG",
            },
        )
        assert r.json()["code"] == 40001, r.text
        print("2. 错误验证码拦截 OK")

        # 3. 登录
        cap3 = cap.create_captcha()
        r = await c.post(
            "/api/v1/auth/login",
            json={
                "username": "admin",
                "password": "secret123",
                "captcha_id": cap3["captcha_id"],
                "captcha_code": get_code(cap3["captcha_id"]),
            },
        )
        assert r.json()["code"] == 0, r.text
        token = r.json()["data"]["tokens"]["access_token"]
        print("3. 登录 OK")

        # 4. 分类
        r = await c.get("/api/v1/categories")
        cats = r.json()["data"]
        assert len(cats) >= 3
        print("4. 分类种子 OK:", [x["name"] for x in cats])

        # 5. 发帖（带验证码 + token）
        cap4 = cap.create_captcha()
        r = await c.post(
            "/api/v1/posts",
            json={
                "title": "联调测试帖子",
                "content": "这是端到端联调创建的帖子正文。",
                "category_id": cats[0]["id"],
                "captcha_id": cap4["captcha_id"],
                "captcha_code": get_code(cap4["captcha_id"]),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.json()["code"] == 0, r.text
        post_id = r.json()["data"]["id"]
        print("5. 发帖 OK id=", post_id)

        # 6. 未登录发帖应 401
        cap5 = cap.create_captcha()
        r = await c.post(
            "/api/v1/posts",
            json={
                "title": "x",
                "content": "y",
                "category_id": 1,
                "captcha_id": cap5["captcha_id"],
                "captcha_code": get_code(cap5["captcha_id"]),
            },
        )
        assert r.status_code == 401, r.text
        print("6. 未登录发帖拦截 OK")

        # 7. 列表 + 详情
        r = await c.get("/api/v1/posts?sort=latest")
        assert r.json()["data"]["items"][0]["id"] == post_id
        r = await c.get(f"/api/v1/posts/{post_id}")
        assert r.json()["data"]["view_count"] >= 1
        print("7. 列表/详情 OK")

        # 8. 评论（带验证码）
        cap6 = cap.create_captcha()
        r = await c.post(
            f"/api/v1/posts/{post_id}/comments",
            json={
                "content": "联调评论内容",
                "captcha_id": cap6["captcha_id"],
                "captcha_code": get_code(cap6["captcha_id"]),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.json()["code"] == 0, r.text
        r = await c.get(f"/api/v1/posts/{post_id}/comments")
        assert len(r.json()["data"]) == 1
        print("8. 评论 OK")

        # 9. 管理后台配置（管理员 token）
        r = await c.get("/api/v1/admin/config/site", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        r = await c.put(
            "/api/v1/admin/config/site/post_image_enabled",
            json={"value": "false", "description": "帖子图片展示"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.json()["value"] == "false", r.text
        r = await c.get("/api/v1/site-config")
        assert r.json()["post_image_enabled"] is False
        print("9. 后台配置读写 OK（post_image_enabled=false）")

        # 10. 普通用户无后台权限
        cap7 = cap.create_captcha()
        r = await c.post(
            "/api/v1/auth/register",
            json={
                "username": "user2",
                "password": "secret123",
                "captcha_id": cap7["captcha_id"],
                "captcha_code": get_code(cap7["captcha_id"]),
            },
        )
        token2 = r.json()["data"]["tokens"]["access_token"]
        r = await c.get("/api/v1/admin/config/site", headers={"Authorization": f"Bearer {token2}"})
        assert r.status_code == 403, r.text
        print("10. 普通用户后台权限拦截 OK")

    print("\n=== 端到端联调全部通过 ===")


asyncio.run(main())
