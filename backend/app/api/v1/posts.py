"""帖子：列表 / 热门 / 详情 / 发帖（登录 + 验证码 + 内容安全）。

安全加固（v0.1.0）：
- 发帖/评论强制图形验证码（await 校验，Redis/内存存储）
- 敏感词过滤（DFA，命中即拦截，见 services.sensitive）
- AI 审核接入：AI_ENABLED 时 sync 模式先审后发（reject 拦截），async 模式投递 Celery（见 9.16）

注意：静态路径（/posts/hot、/posts/search 等）必须先于动态路径（/posts/{id}）声明（文档 6.1）。
TODO：点赞/收藏/搜索/投票/推荐流（文档 6.2）。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.schemas.auth import CaptchaField
from app.services import captcha as captcha_service
from app.services import content as content_service
from app.services import sensitive as sensitive_service
from app.services.audit import AIAuditService, AuditError

logger = logging.getLogger(__name__)

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
    """内容安全检查：敏感词拦截 + AI 审核（sync 模式）。"""
    # 1. 敏感词过滤（DFA）
    if sensitive_service.sensitive_filter.contains(content) or (
        title and sensitive_service.sensitive_filter.contains(title)
    ):
        raise HTTPException(status_code=400, detail="内容包含违规词，请修改后重新发布")

    # 2. AI 审核（仅 sync 模式在发布链路同步拦截；async 由 Celery 后置处理）
    if settings.ai_enabled and settings.ai_audit_mode == "sync":
        service = AIAuditService()
        try:
            result = await service.audit_text(content, title=title)
            if result["result"] == "reject":
                raise HTTPException(status_code=400, detail=f"内容审核未通过：{result['reason']}")
            if result["result"] == "review":
                logger.info("AI 审核转人工: %s", result["reason"])
        except AuditError:
            # AI 未配置/调用异常：熔断降级放行（见文档 9.16），不阻塞发帖
            logger.warning("AI 审核跳过（sync）: 服务不可用")
        except Exception as exc:  # noqa: BLE001
            logger.warning("AI 审核调用失败（sync 降级放行）: %s", exc)


def _dispatch_async_audit(title: str | None, content: str, target_id: int) -> None:
    """async 模式：发布后投递 AI 审核任务（失败静默，由人工审核兜底）。"""
    if not settings.ai_enabled or settings.ai_audit_mode != "async":
        return
    try:
        from app.tasks.audit_tasks import audit_content

        audit_content.delay(content, target_type="post", target_id=target_id, title=title)
    except Exception as exc:  # noqa: BLE001
        logger.warning("AI 审核任务投递失败（async）: %s", exc)


@router.get("", summary="帖子列表（最新/热门/精华，游标分页）")
async def list_posts(
    sort: str = Query("latest", pattern="^(latest|hot|essence)$"),
    category_id: int | None = Query(None, ge=1),
    cursor: int | None = Query(None, ge=1),
    limit: int = Query(20, ge=1, le=50),
    session: AsyncSession = Depends(get_db),
) -> dict:
    items = await content_service.list_posts(
        session, sort=sort, category_id=category_id, cursor=cursor, limit=limit
    )
    next_cursor = items[-1]["id"] if len(items) == limit and items else None
    return _ok({"items": items, "next_cursor": next_cursor})


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
        return {"code": 40001, "message": "验证码错误或已过期", "data": None}
    await _check_content_security(payload.title, payload.content)
    data = await content_service.create_post(
        session,
        user_id=user.id,
        title=payload.title,
        content=payload.content,
        category_id=payload.category_id,
        is_anonymous=payload.is_anonymous,
    )
    _dispatch_async_audit(payload.title, payload.content, data["id"])
    return _ok(data, "发帖成功")


@router.get("/{post_id}/comments", summary="帖子评论列表")
async def post_comments(post_id: int, session: AsyncSession = Depends(get_db)) -> dict:
    return _ok(await content_service.list_comments(session, post_id))


@router.post("/{post_id}/comments", summary="发表评论（登录 + 验证码 + 内容安全）")
async def create_comment(
    post_id: int,
    payload: CommentCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    if not await captcha_service.verify_captcha(payload.captcha_id, payload.captcha_code):
        return {"code": 40001, "message": "验证码错误或已过期", "data": None}
    await _check_content_security(None, payload.content)
    data = await content_service.create_comment(
        session, post_id=post_id, user_id=user.id, content=payload.content
    )
    _dispatch_async_audit(None, payload.content, data["id"])
    return _ok(data, "评论成功")
