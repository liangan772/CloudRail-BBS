"""v1 路由聚合。

所有业务模块在此注册；模块内 TODO 接口按 docs/开发文档.md 第 6 章逐项实现。
注意：静态路径（/posts/hot、/posts/search 等）必须先于动态路径（/posts/{id}）声明。
"""

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    announcements,
    app as app_module,
    audit,
    auth,
    auth_devices,
    auth_oauth,
    auth_sms,
    banners,
    blocks,
    categories,
    comments,
    drafts,
    gamification,
    history,
    notifications,
    polls,
    posts,
    reports,
    site,
    tags,
    topics,
    users,
)
# 管理后台子模块（FastAPI 0.141 嵌套两层 include_router 展开缺陷：平级挂载）
from app.api.v1.admin import audits as admin_audits
from app.api.v1.admin import banners as admin_banners
from app.api.v1.admin import reports as admin_reports

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(auth_sms.router)
api_router.include_router(auth_oauth.router)
api_router.include_router(auth_devices.router)
api_router.include_router(users.router)
api_router.include_router(categories.router)
api_router.include_router(posts.router)
api_router.include_router(comments.router)
api_router.include_router(tags.router)
api_router.include_router(notifications.router)
api_router.include_router(banners.router)
api_router.include_router(topics.router)
api_router.include_router(drafts.router)
api_router.include_router(reports.router)
api_router.include_router(blocks.router)
api_router.include_router(polls.router)
api_router.include_router(history.router)
api_router.include_router(announcements.router)
api_router.include_router(audit.router)
api_router.include_router(site.router)
api_router.include_router(gamification.router)
api_router.include_router(app_module.router)
api_router.include_router(admin.router)
api_router.include_router(admin_audits.router)
api_router.include_router(admin_reports.router)
api_router.include_router(admin_banners.router)
