"""端到端联调（含安全加固验证，v0.1.0）。

覆盖：验证码 → 注册(首用户管理员) → 登录 → 发帖 → 列表 → 详情 → 评论 → 后台配置 →
权限 → 弱密码拦截 → 敏感词拦截 → Refresh 轮换/吊销 → 登录限流。
"""

import asyncio
import os
import sys

# 使用独立测试库（避免污染开发库 forum.db 与既有数据冲突）
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./e2e_forum.db"
if os.path.exists("e2e_forum.db"):
    os.remove("e2e_forum.db")

from httpx import ASGITransport, AsyncClient

sys.path.insert(0, "backend")

from app.core.db import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services import captcha as cap  # noqa: E402


async def new_captcha(c: AsyncClient) -> dict:
    data = await c.get("/api/v1/auth/captcha")
    body = data.json()
    return body


async def main() -> None:
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # 1. 验证码 + 注册（首用户管理员）
        cap1 = await new_captcha(c)
        r = await c.post(
            "/api/v1/auth/register",
            json={
                "username": "admin",
                "password": "secret123",
                "email": "admin@example.com",
                "captcha_id": cap1["captcha_id"],
                "captcha_code": cap.get_code_for_test(cap1["captcha_id"]),
            },
        )
        assert r.status_code == 200 and r.json()["code"] == 0, r.text
        data = r.json()["data"]
        assert data["user"]["role"] == 2, "首用户应为管理员"
        refresh1 = data["tokens"]["refresh_token"]
        print("1. 注册(首用户管理员) OK:", data["user"]["username"], "role=", data["user"]["role"])

        # 2. 弱密码拦截（纯数字，需字母+数字）
        cap2 = await new_captcha(c)
        r = await c.post(
            "/api/v1/auth/register",
            json={
                "username": "weakpass",
                "password": "123456",
                "captcha_id": cap2["captcha_id"],
                "captcha_code": cap.get_code_for_test(cap2["captcha_id"]),
            },
        )
        assert r.status_code == 400 and "字母" in r.json()["detail"], r.text
        print("2. 弱密码拦截 OK")

        # 3. 错误验证码拦截
        cap3 = await new_captcha(c)
        r = await c.post(
            "/api/v1/auth/register",
            json={
                "username": "user2",
                "password": "secret123",
                "captcha_id": cap3["captcha_id"],
                "captcha_code": "WRONG",
            },
        )
        assert r.json()["code"] == 40001, r.text
        print("3. 错误验证码拦截 OK")

        # 4. 登录
        cap4 = await new_captcha(c)
        r = await c.post(
            "/api/v1/auth/login",
            json={
                "username": "admin",
                "password": "secret123",
                "captcha_id": cap4["captcha_id"],
                "captcha_code": cap.get_code_for_test(cap4["captcha_id"]),
            },
        )
        assert r.json()["code"] == 0, r.text
        token = r.json()["data"]["tokens"]["access_token"]
        refresh2 = r.json()["data"]["tokens"]["refresh_token"]
        print("4. 登录 OK")

        # 5. Refresh 轮换：旧 token 立即失效
        r = await c.post("/api/v1/auth/refresh", json={"refresh_token": refresh2})
        assert r.json()["code"] == 0, r.text
        refresh3 = r.json()["data"]["tokens"]["refresh_token"]
        r = await c.post("/api/v1/auth/refresh", json={"refresh_token": refresh2})
        assert r.status_code == 401, "轮换后旧 Refresh Token 应失效"
        print("5. Refresh 轮换 OK（旧 token 已作废）")

        # 6. 分类种子
        r = await c.get("/api/v1/categories")
        cats = r.json()["data"]
        assert len(cats) >= 3
        print("6. 分类种子 OK:", [x["name"] for x in cats])

        # 7. 发帖（带验证码 + token）
        cap5 = await new_captcha(c)
        r = await c.post(
            "/api/v1/posts",
            json={
                "title": "联调测试帖子",
                "content": "这是端到端联调创建的帖子正文。",
                "category_id": cats[0]["id"],
                "captcha_id": cap5["captcha_id"],
                "captcha_code": cap.get_code_for_test(cap5["captcha_id"]),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.json()["code"] == 0, r.text
        post_id = r.json()["data"]["id"]
        print("7. 发帖 OK id=", post_id)

        # 8. 敏感词拦截
        cap6 = await new_captcha(c)
        r = await c.post(
            "/api/v1/posts",
            json={
                "title": "测试",
                "content": "这里有违规词傻逼内容",
                "category_id": cats[0]["id"],
                "captcha_id": cap6["captcha_id"],
                "captcha_code": cap.get_code_for_test(cap6["captcha_id"]),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 400 and "违规词" in r.json()["detail"], r.text
        print("8. 敏感词拦截 OK")

        # 9. 未登录发帖 401
        cap7 = await new_captcha(c)
        r = await c.post(
            "/api/v1/posts",
            json={
                "title": "x",
                "content": "y",
                "category_id": 1,
                "captcha_id": cap7["captcha_id"],
                "captcha_code": cap.get_code_for_test(cap7["captcha_id"]),
            },
        )
        assert r.status_code == 401, r.text
        print("9. 未登录发帖拦截 OK")

        # 10. 列表 + 详情
        r = await c.get("/api/v1/posts?sort=latest")
        assert r.json()["data"]["items"][0]["id"] == post_id
        r = await c.get(f"/api/v1/posts/{post_id}")
        assert r.json()["data"]["view_count"] >= 1
        print("10. 列表/详情 OK")

        # 11. 评论（带验证码）+ 敏感词拦截评论
        cap8 = await new_captcha(c)
        r = await c.post(
            f"/api/v1/posts/{post_id}/comments",
            json={
                "content": "联调评论内容",
                "captcha_id": cap8["captcha_id"],
                "captcha_code": cap.get_code_for_test(cap8["captcha_id"]),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.json()["code"] == 0, r.text
        r = await c.get(f"/api/v1/posts/{post_id}/comments")
        assert len(r.json()["data"]) == 1
        print("11. 评论 OK")

        # 12. 后台配置读写（管理员 token）+ 审计日志落库
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
        print("12. 后台配置读写 OK（post_image_enabled=false，已写审计日志）")

        # 13. 普通用户无后台权限
        cap9 = await new_captcha(c)
        r = await c.post(
            "/api/v1/auth/register",
            json={
                "username": "user2",
                "password": "secret123",
                "captcha_id": cap9["captcha_id"],
                "captcha_code": cap.get_code_for_test(cap9["captcha_id"]),
            },
        )
        token2 = r.json()["data"]["tokens"]["access_token"]
        r = await c.get("/api/v1/admin/config/site", headers={"Authorization": f"Bearer {token2}"})
        assert r.status_code == 403, r.text
        print("13. 普通用户后台权限拦截 OK")

        # 14. 登出吊销 Refresh Token
        r = await c.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh3},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.json()["code"] == 0, r.text
        r = await c.post("/api/v1/auth/refresh", json={"refresh_token": refresh3})
        assert r.status_code == 401, "登出后 Refresh Token 应被吊销"
        print("14. 登出吊销 Refresh Token OK")

        # 15. 登录限流：连续 6 次错误登录 → 429
        limited = False
        for i in range(6):
            capx = await new_captcha(c)
            r = await c.post(
                "/api/v1/auth/login",
                json={
                    "username": "admin",
                    "password": "wrongpass1",
                    "captcha_id": capx["captcha_id"],
                    "captcha_code": cap.get_code_for_test(capx["captcha_id"]),
                },
            )
            if r.status_code == 429:
                limited = True
                break
        assert limited, "登录限流应触发 429"
        print("15. 登录限流 OK（429 已触发）")

    print("\n=== 端到端联调（含安全加固）全部通过 ===")


asyncio.run(main())
