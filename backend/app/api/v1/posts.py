"""帖子：列表 / 热门 / 详情 / 发帖（登录 + 验证码 + 内容安全）。

安全加固（v0.1.0）：
- 发帖/评论强制图形验证码（await 校验，Redis/内存存储）
- 敏感词过滤（DFA，命中即拦截，见 services.sensitive）
- AI 审核（v1.4 两级审核）：先发后审——内容发布后统一投递审核工作流（audit_flow），
  AI 初审结论全部落库进入人工复审队列；AI reject 自动下架，人工复审为最终裁决（见 9.16）

注意：静态路径（/posts/hot、/posts/search 等）必须先于动态路径（/posts/{id}）声明（文档 6.1）。
TODO：点赞/收藏/搜索/投票/推荐流（文档 6.2）。
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.schemas.auth import CaptchaField
from app.services import audit_flow
from app.services import captcha as captcha_service
from app.services import content as content_service
from app.services import sensitive as sensitive_service

logger = logging.getLogger(__name__)

# 后台审核任务句柄（避免被 GC；进程退出时未完成的任务自动丢弃）
_background_tasks: set[asyncio.Task] = set()

router = APIRouter(prefix="/posts", tags=["帖子"])


class PostCreateRequest(CaptchaField):
    title: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1, max_length=50000)
    category_id: int = Field(ge=1)
    is_anonymous: bool = False


class CommentCreateRequest(CaptchaField):
    content: str = Field(min_length=1, max_length=2000)


def _ok(data, message: str = "ok") -> dict:
    return {"code": 0, "message": message, "data": data}


async def _check_content_security(title: str | None, content: str) -> None:
    """内容安全检查：敏感词过滤（DFA，命中即拦截）。

    注：AI 审核为「先发后审」，在内容创建后由 _dispatch_audit 统一投递（见 9.16）。
    """
    if sensitive_service.sensitive_filter.contains(content) or (
        title and sensitive_service.sensitive_filter.contains(title)
    ):
        raise HTTPException(status_code=400, detail="内容包含违规词，请修改后重新发布")


async def _dispatch_audit(
    session: AsyncSession,
    *,
    target_type: str,
    target_id: int,
    content: str,
    title: str | None = None,
) -> None:
    """两级审核 AI 初审投递（先发后审）：sync 请求内执行；async 进程内后台任务。

    单容器部署无 Celery worker：async 模式使用 asyncio 后台任务（独立会话）执行，
    结论同样落库进入人工复审队列；Celery 任务（app/tasks）保留供外部扩展部署使用。
    """
    if not settings.ai_enabled or settings.ai_audit_mode == "off":
        return
    if settings.ai_audit_mode == "sync":
        await audit_flow.queue_ai_audit(
            session,
            target_type=target_type,
            target_id=target_id,
            content=content,
            title=title,
        )
        return

    async def _run() -> None:
        from app.core.db import async_session_factory

        try:
            async with async_session_factory() as bg_session:
                await audit_flow.queue_ai_audit(
                    bg_session,
                    target_type=target_type,
                    target_id=target_id,
                    content=content,
                    title=title,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("后台 AI 审核失败 target=%s:%s: %s", target_type, target_id, exc)

    try:
        task = asyncio.get_running_loop().create_task(_run())
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
    except RuntimeError as exc:
        logger.warning("无事件循环，AI 审核跳过（async）: %s", exc)


@router.get("", summary="帖子列表（最新/热门/精华，游标/页码分页）")
async def list_posts(
    sort: str = Query("latest", pattern="^(latest|hot|essence)$"),
    category_id: int | None = Query(None, ge=1),
    cursor: int | None = Query(None, ge=1, description="游标 ID（用于 latest 和 essence）"),
    page: int = Query(1, ge=1, description="页码（用于 hot 热门排序）"),
    limit: int = Query(20, ge=1, le=50),
    session: AsyncSession = Depends(get_db),
) -> dict:
    items = await content_service.list_posts(
        session, sort=sort, category_id=category_id, cursor=cursor, page=page, limit=limit
    )
    # 仅在非热门排序时返回 next_cursor，热门排序返回当前 page
    next_cursor = items[-1]["id"] if len(items) == limit and items and sort != "hot" else None
    return _ok({
        "items": items,
        "next_cursor": next_cursor,
        "page": page if sort == "hot" else None,
    })


@router.get("/hot", summary="热门帖子")
async def hot_posts(
    limit: int = Query(10, ge=1, le=30),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return _ok(await content_service.list_hot_posts(session, limit=limit))


@router.get("/{post_id}", summary="帖子详情（浏览 +1）")
async def post_detail(post_id: int, session: AsyncSession = Depends(get_db)) -> dict:
    return _ok(await content_service.get_post(session, post_id))


@router.post("", summary="发帖（登录 + 验证码 + 内容安全）")
async def create_post(
    payload: PostCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    if not await captcha_service.verify_captcha(payload.captcha_id, payload.captcha_code):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")
    await _check_content_security(payload.title, payload.content)
    data = await content_service.create_post(
        session,
        user_id=user.id,
        title=payload.title,
        content=payload.content,
        category_id=payload.category_id,
        is_anonymous=payload.is_anonymous,
    )
    await _dispatch_audit(
        session, target_type="post", target_id=data["id"], content=payload.content, title=payload.title
    )
    return _ok(data, "发帖成功")


@router.post("/{post_id}/comments", summary="发表评论（登录 + 验证码 + 内容安全）")
async def create_comment(
    post_id: int,
    payload: CommentCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    if not await captcha_service.verify_captcha(payload.captcha_id, payload.captcha_code):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")
    await _check_content_security(None, payload.content)
    data = await content_service.create_comment(
        session, post_id=post_id, user_id=user.id, content=payload.content
    )
    await _dispatch_audit(
        session, target_type="comment", target_id=data["id"], content=payload.content
    )
    return _ok(data, "评论成功")
