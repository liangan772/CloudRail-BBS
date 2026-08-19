"""管理后台（角色 >= 2 管理员）。

安全加固（v0.1.0）：
- 管理写操作统一记录审计日志（admin_logs 表，见文档 5.2）
- 数据库异常不对外泄露（详情入日志，对外返回通用提示）

TODO（按文档 6.2）：
- GET    /admin/stats/overview            运营看板
- GET    /admin/users                      用户管理
- PUT    /admin/users/{id}/status          禁言/封禁/解封
- GET    /admin/posts                      审核列表
- PUT    /admin/posts/{id}/review          审核
- PUT    /admin/posts/{id}/pin|essence     置顶/加精
- POST   /admin/categories                 分类管理
- GET/POST/DELETE /admin/sensitive-words   敏感词管理
- GET/PUT /admin/config/gamification       激励配置
- GET/POST/PUT/DELETE /admin/banners       轮播图管理
- GET    /admin/reports                    举报队列
- PUT    /admin/reports/{id}               处理举报
- GET/PUT /admin/topics                    话题运营

已实现（v1.4）：
- GET    /admin/audits                     审核记录（复审队列）
- PUT    /admin/audits/{id}/review         人工复审（approved 通过 / rejected 驳回）
  （audits 子路由在 api/v1/__init__.py 聚合处直接挂载：FastAPI 0.141 嵌套两层
    include_router 的惰性展开存在缺陷，嵌套在 admin.router 下会导致 404）
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, require_role
from app.models.admin_log import AdminLog
from app.models.audit import AuditRecord
from app.models.category import Category
from app.models.comment import Comment
from app.models.post import Post
from app.models.sensitive_word import SensitiveWord
from app.models.user import User
from app.services import auth as auth_service
from app.services import site_config as site_config_service
from app.services import stats as stats_service
from app.services import sensitive as sensitive_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["管理后台"])


class SiteConfigUpdate(BaseModel):
    value: str = Field(min_length=0, max_length=255)
    description: str = Field(default="", max_length=255)


async def _log_admin(
    session: AsyncSession, admin: CurrentUser, action: str, target_type: str = "", target_id: str = "", detail: str = ""
) -> None:
    """管理操作审计留痕（写失败仅告警，不阻断主流程）。"""
    try:
        session.add(
            AdminLog(admin_id=admin.id, action=action, target_type=target_type, target_id=target_id, detail=detail)
        )
        await session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("审计日志写入失败: %s", exc)
        await session.rollback()


@router.get("/config/site", summary="站点配置列表（含描述）")
async def list_site_config(
    session: AsyncSession = Depends(get_db),
    _admin=Depends(require_role(2)),
) -> dict:
    return await site_config_service.get_all_config(session)


@router.put("/config/site/{key}", summary="更新站点配置")
async def update_site_config(
    payload: SiteConfigUpdate,
    key: str = Path(min_length=1, max_length=64),
    session: AsyncSession = Depends(get_db),
    admin: CurrentUser = Depends(require_role(2)),
) -> dict:
    try:
        result = await site_config_service.set_config(session, key, payload.value, payload.description)
    except Exception as exc:  # noqa: BLE001
        logger.exception("站点配置更新失败 key=%s: %s", key, exc)
        raise HTTPException(status_code=503, detail="数据库不可用，请稍后重试") from exc
    await _log_admin(
        session, admin, action="config.update", target_type="site_config", target_id=key, detail=f"{key}={payload.value}"
    )
    return result


# ---------- 运营看板 ----------


@router.get("/stats/overview", summary="运营看板统计")
async def stats_overview(
    session: AsyncSession = Depends(get_db),
    _admin: CurrentUser = Depends(require_role(2)),
) -> dict:
    return await stats_service.get_overview(session)


# ---------- 用户管理 ----------


class UserStatusUpdate(BaseModel):
    status: int = Field(ge=0, le=2, description="0 正常 / 1 禁言 / 2 封禁")


@router.get("/posts", summary="帖子列表（分页/状态/分类过滤）")
async def list_admin_posts(
    status: int | None = Query(None, ge=0, le=3, description="状态过滤"),
    category_id: int | None = Query(None, ge=1),
    keyword: str | None = Query(None, max_length=64, description="标题搜索"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    _admin: CurrentUser = Depends(require_role(2)),
) -> dict:
    stmt = select(Post)
    if status is not None:
        stmt = stmt.where(Post.status == status)
    if category_id:
        stmt = stmt.where(Post.category_id == category_id)
    if keyword:
        stmt = stmt.where(Post.title.contains(keyword))
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (
        (
            await session.execute(
                stmt.order_by(Post.id.desc()).offset((page - 1) * limit).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    user_ids = {p.user_id for p in rows}
    cat_ids = {p.category_id for p in rows}
    
    # 判空保护，防止空集合进入 SQL in_()
    users = {
        u.id: u.username
        for u in (await session.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
    } if user_ids else {}
    cats = {
        c.id: c.name
        for c in (await session.execute(select(Category).where(Category.id.in_(cat_ids)))).scalars().all()
    } if cat_ids else {}
    
    items = [
        {
            "id": p.id,
            "title": p.title,
            "content": p.content[:200],
            "author_id": p.user_id,
            "author": users.get(p.user_id),
            "category": cats.get(p.category_id),
            "status": p.status,
            "is_pinned": p.is_pinned,
            "is_essence": p.is_essence,
            "view_count": p.view_count,
            "comment_count": p.comment_count,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in rows
    ]
    return {"total": total or 0, "page": page, "limit": limit, "items": items}


@router.put("/users/{user_id}/status", summary="禁言/封禁/解封用户")
async def update_user_status(
    payload: UserStatusUpdate,
    user_id: int = Path(ge=1),
    session: AsyncSession = Depends(get_db),
    admin: CurrentUser = Depends(require_role(2)),
) -> dict:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能操作自己的账号")
    
    user.status = payload.status
    await session.commit()
    
    # 🌟 若操作为封禁，立即吊销该用户的全部有效 Session
    if payload.status == 2:
        await auth_service.revoke_user_refresh_tokens(user_id)

    await _log_admin(
        session, admin, action="user.status", target_type="user", target_id=str(user_id),
        detail=f"status={payload.status}",
    )
    return {"id": user.id, "status": user.status}


# ---------- 内容管理 ----------


class PostReviewRequest(BaseModel):
    status: int = Field(ge=0, le=3, description="0 正常（通过）/ 1 待审核（下架）/ 2 锁定 / 3 删除")


class PostFlagRequest(BaseModel):
    value: bool


@router.get("/posts", summary="帖子列表（分页/状态/分类过滤）")
async def list_admin_posts(
    status: int | None = Query(None, ge=0, le=3, description="状态过滤"),
    category_id: int | None = Query(None, ge=1),
    keyword: str | None = Query(None, max_length=64, description="标题搜索"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    _admin: CurrentUser = Depends(require_role(2)),
) -> dict:
    stmt = select(Post)
    if status is not None:
        stmt = stmt.where(Post.status == status)
    if category_id:
        stmt = stmt.where(Post.category_id == category_id)
    if keyword:
        stmt = stmt.where(Post.title.contains(keyword))
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (
        (
            await session.execute(
                stmt.order_by(Post.id.desc()).offset((page - 1) * limit).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    user_ids = {p.user_id for p in rows}
    cat_ids = {p.category_id for p in rows}
    users = {
        u.id: u.username
        for u in (await session.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
    }
    cats = {
        c.id: c.name
        for c in (await session.execute(select(Category).where(Category.id.in_(cat_ids)))).scalars().all()
    }
    items = [
        {
            "id": p.id,
            "title": p.title,
            "content": p.content[:200],
            "author_id": p.user_id,
            "author": users.get(p.user_id),
            "category": cats.get(p.category_id),
            "status": p.status,
            "is_pinned": p.is_pinned,
            "is_essence": p.is_essence,
            "view_count": p.view_count,
            "comment_count": p.comment_count,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in rows
    ]
    return {"total": total or 0, "page": page, "limit": limit, "items": items}


@router.put("/posts/{post_id}/review", summary="审核帖子（通过/下架）")
async def review_post(
    payload: PostReviewRequest,
    post_id: int = Path(ge=1),
    session: AsyncSession = Depends(get_db),
    admin: CurrentUser = Depends(require_role(2)),
) -> dict:
    post = await session.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="帖子不存在")
    post.status = payload.status
    await session.commit()
    await _log_admin(
        session, admin, action="post.review", target_type="post", target_id=str(post_id),
        detail=f"status={payload.status}",
    )
    return {"id": post.id, "status": post.status}


@router.put("/posts/{post_id}/pin", summary="置顶/取消置顶")
async def toggle_pin(
    payload: PostFlagRequest,
    post_id: int = Path(ge=1),
    session: AsyncSession = Depends(get_db),
    admin: CurrentUser = Depends(require_role(2)),
) -> dict:
    post = await session.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="帖子不存在")
    post.is_pinned = payload.value
    await session.commit()
    await _log_admin(
        session, admin, action="post.pin", target_type="post", target_id=str(post_id),
        detail=f"is_pinned={payload.value}",
    )
    return {"id": post.id, "is_pinned": post.is_pinned}


@router.put("/posts/{post_id}/essence", summary="加精/取消加精")
async def toggle_essence(
    payload: PostFlagRequest,
    post_id: int = Path(ge=1),
    session: AsyncSession = Depends(get_db),
    admin: CurrentUser = Depends(require_role(2)),
) -> dict:
    post = await session.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="帖子不存在")
    post.is_essence = payload.value
    await session.commit()
    await _log_admin(
        session, admin, action="post.essence", target_type="post", target_id=str(post_id),
        detail=f"is_essence={payload.value}",
    )
    return {"id": post.id, "is_essence": post.is_essence}


# ---------- 敏感词管理 ----------


class SensitiveWordCreate(BaseModel):
    word: str = Field(min_length=1, max_length=64)


@router.get("/sensitive-words", summary="敏感词列表")
async def list_sensitive_words(
    session: AsyncSession = Depends(get_db),
    _admin: CurrentUser = Depends(require_role(2)),
) -> dict:
    rows = (
        (await session.execute(select(SensitiveWord).order_by(SensitiveWord.id))).scalars().all()
    )
    return {
        "total": len(rows),
        "items": [
            {"id": w.id, "word": w.word, "created_at": w.created_at.isoformat() if w.created_at else None}
            for w in rows
        ],
    }


@router.post("/sensitive-words", summary="新增敏感词")
async def create_sensitive_word(
    payload: SensitiveWordCreate,
    session: AsyncSession = Depends(get_db),
    admin: CurrentUser = Depends(require_role(2)),
) -> dict:
    word = payload.word.strip()
    exists = await session.scalar(
        select(func.count()).select_from(SensitiveWord).where(SensitiveWord.word == word)
    )
    if exists:
        raise HTTPException(status_code=400, detail="敏感词已存在")
    row = SensitiveWord(word=word)
    session.add(row)
    await session.commit()
    await _rebuild_sensitive(session)
    await _log_admin(session, admin, action="sensitive.create", target_type="sensitive_word", detail=word)
    return {"id": row.id, "word": row.word}


@router.delete("/sensitive-words/{word_id}", summary="删除敏感词")
async def delete_sensitive_word(
    word_id: int = Path(ge=1),
    session: AsyncSession = Depends(get_db),
    admin: CurrentUser = Depends(require_role(2)),
) -> dict:
    row = await session.get(SensitiveWord, word_id)
    if row is None:
        raise HTTPException(status_code=404, detail="敏感词不存在")
    word = row.word
    await session.delete(row)
    await session.commit()
    await _rebuild_sensitive(session)
    await _log_admin(session, admin, action="sensitive.delete", target_type="sensitive_word", detail=word)
    return {"deleted": True, "word": word}


async def _rebuild_sensitive(session: AsyncSession) -> None:
    """从 DB 全量重建 DFA 过滤器（增删后调用，严格同步数据库实际词集）。"""
    words = (await session.execute(select(SensitiveWord.word))).scalars().all()
    # 严格根据 DB 中的实际词集重建，避免删除所有词后被 DEFAULT_WORDS 覆盖
    sensitive_service.sensitive_filter.rebuild([str(w) for w in words])


@router.get("/users", summary="用户列表（分页/搜索/状态过滤）")
async def list_users(
    keyword: str | None = Query(None, max_length=32, description="用户名模糊搜索"),
    status: int | None = Query(None, ge=0, le=2, description="状态过滤：0 正常 / 1 禁言 / 2 封禁"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    _admin: CurrentUser = Depends(require_role(2)),
) -> dict:
    """用户列表（管理后台用户管理页对接；v0.1.3 已实现，本地重构时被误删，此处恢复）。"""
    stmt = select(User)
    if keyword:
        stmt = stmt.where(User.username.contains(keyword))
    if status is not None:
        stmt = stmt.where(User.status == status)
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (
        (
            await session.execute(
                stmt.order_by(User.id.desc()).offset((page - 1) * limit).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    items = [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "status": u.status,
            "points": u.points,
            "level": u.level,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in rows
    ]
    return {"total": total or 0, "page": page, "limit": limit, "items": items}