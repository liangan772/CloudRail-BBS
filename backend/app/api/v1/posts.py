"""帖子：列表 / 热门 / 详情 / 发帖（登录 + 验证码）。

注意：静态路径（/posts/hot、/posts/search 等）必须先于动态路径（/posts/{id}）声明（文档 6.1）。
TODO：点赞/收藏/搜索/投票/推荐流（文档 6.2）。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.schemas.auth import CaptchaField
from app.services import captcha as captcha_service
from app.services import content as content_service

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


@router.post("", summary="发帖（登录 + 验证码）")
async def create_post(
    payload: PostCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    if not captcha_service.verify_captcha(payload.captcha_id, payload.captcha_code):
        return {"code": 40001, "message": "验证码错误或已过期", "data": None}
    data = await content_service.create_post(
        session,
        user_id=user.id,
        title=payload.title,
        content=payload.content,
        category_id=payload.category_id,
        is_anonymous=payload.is_anonymous,
    )
    return _ok(data, "发帖成功")


@router.get("/{post_id}/comments", summary="帖子评论列表")
async def post_comments(post_id: int, session: AsyncSession = Depends(get_db)) -> dict:
    return _ok(await content_service.list_comments(session, post_id))


@router.post("/{post_id}/comments", summary="发表评论（登录 + 验证码）")
async def create_comment(
    post_id: int,
    payload: CommentCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    if not captcha_service.verify_captcha(payload.captcha_id, payload.captcha_code):
        return {"code": 40001, "message": "验证码错误或已过期", "data": None}
    data = await content_service.create_comment(
        session, post_id=post_id, user_id=user.id, content=payload.content
    )
    return _ok(data, "评论成功")
