"""内容服务：帖子 / 评论 / 分类。"""

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.category import Category
from app.models.comment import Comment
from app.models.post import Post
from app.models.user import User


def _post_out(post: Post, author_name: str | None = None, category_name: str | None = None) -> dict:
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "summary": post.content[:120],
        "category_id": post.category_id,
        "category": category_name,
        "author_id": post.user_id,
        "author": None if post.is_anonymous else author_name,
        "is_anonymous": post.is_anonymous,
        "is_pinned": post.is_pinned,
        "is_essence": post.is_essence,
        "view_count": post.view_count,
        "like_count": post.like_count,
        "comment_count": post.comment_count,
        "created_at": post.created_at.isoformat() if post.created_at else None,
    }


def _comment_out(comment: Comment, author_name: str | None = None) -> dict:
    return {
        "id": comment.id,
        "post_id": comment.post_id,
        "parent_id": comment.parent_id,
        "content": comment.content,
        "author": author_name,
        "like_count": comment.like_count,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


async def list_categories(session: AsyncSession) -> list[dict]:
    rows = (
        await session.execute(
            select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order, Category.id)
        )
    ).scalars().all()
    return [
        {"id": c.id, "name": c.name, "description": c.description, "sort_order": c.sort_order}
        for c in rows
    ]


async def list_posts(
    session: AsyncSession,
    *,
    sort: str = "latest",
    category_id: int | None = None,
    cursor: int | None = None,
    page: int = 1,
    limit: int = 20,
) -> list[dict]:
    stmt = select(Post).where(Post.status == 0)
    if category_id:
        stmt = stmt.where(Post.category_id == category_id)

    # 针对不同排序模式采用合适的分页方式
    if sort == "hot":
        # 热门流采用 offset 分页，避免 ID 游标导致漏数据
        offset = (max(1, page) - 1) * limit
        stmt = stmt.order_by(Post.view_count.desc(), Post.id.desc()).offset(offset).limit(limit)
    elif sort == "essence":
        if cursor:
            stmt = stmt.where(Post.id < cursor)
        stmt = stmt.where(Post.is_essence.is_(True)).order_by(Post.id.desc()).limit(limit)
    else:
        # 最新流使用高性能 ID 游标分页
        if cursor:
            stmt = stmt.where(Post.id < cursor)
        stmt = stmt.order_by(Post.id.desc()).limit(limit)

    posts = (await session.execute(stmt)).scalars().all()
    return await _enrich_posts(session, posts)


async def list_hot_posts(session: AsyncSession, limit: int = 10) -> list[dict]:
    stmt = (
        select(Post)
        .where(Post.status == 0)
        .order_by(Post.view_count.desc(), Post.like_count.desc(), Post.id.desc())
        .limit(limit)
    )
    posts = (await session.execute(stmt)).scalars().all()
    return await _enrich_posts(session, posts)


async def _enrich_posts(session: AsyncSession, posts: list[Post]) -> list[dict]:
    if not posts:
        return []
    user_ids = {p.user_id for p in posts}
    cat_ids = {p.category_id for p in posts}
    users = {
        u.id: u.username
        for u in (
            await session.execute(select(User).where(User.id.in_(user_ids)))
        ).scalars().all()
    }
    cats = {
        c.id: c.name
        for c in (
            await session.execute(select(Category).where(Category.id.in_(cat_ids)))
        ).scalars().all()
    }
    return [_post_out(p, users.get(p.user_id), cats.get(p.category_id)) for p in posts]


async def get_post(session: AsyncSession, post_id: int) -> dict:
    post = await session.get(Post, post_id)
    if post is None or post.status != 0:
        raise HTTPException(status_code=404, detail="帖子不存在")
    post.view_count += 1
    await session.commit()
    user = await session.get(User, post.user_id)
    cat = await session.get(Category, post.category_id)
    return _post_out(post, user.username if user else None, cat.name if cat else None)


async def create_post(
    session: AsyncSession,
    *,
    user_id: int,
    title: str,
    content: str,
    category_id: int,
    is_anonymous: bool = False,
) -> dict:
    title = title.strip()
    if not title or len(title) > 128:
        raise HTTPException(status_code=400, detail="标题不能为空且不超过 128 字")
    if not content.strip():
        raise HTTPException(status_code=400, detail="正文不能为空")
    cat = await session.get(Category, category_id)
    if cat is None:
        raise HTTPException(status_code=400, detail="分类不存在")

    post = Post(
        user_id=user_id,
        category_id=category_id,
        title=title,
        content=content.strip(),
        is_anonymous=is_anonymous,
    )
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return _post_out(post, "匿名用户" if is_anonymous else None, cat.name)


async def list_comments(session: AsyncSession, post_id: int) -> list[dict]:
    rows = (
        await session.execute(
            select(Comment).where(Comment.post_id == post_id, Comment.status == 0).order_by(Comment.id)
        )
    ).scalars().all()
    if not rows:
        return []
    user_ids = {c.user_id for c in rows}
    users = {
        u.id: u.username
        for u in (await session.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
    }
    return [_comment_out(c, users.get(c.user_id)) for c in rows]


async def create_comment(
    session: AsyncSession, *, post_id: int, user_id: int, content: str
) -> dict:
    content = content.strip()
    if not content or len(content) > 2000:
        raise HTTPException(status_code=400, detail="评论内容不能为空且不超过 2000 字")
        
    post = await session.get(Post, post_id)
    if post is None or post.status != 0:
        raise HTTPException(status_code=404, detail="帖子不存在")

    comment = Comment(post_id=post_id, user_id=user_id, content=content)
    session.add(comment)
    
    # 🌟 修复：数据库原子自增，杜绝高并发写丢失
    await session.execute(
        update(Post).where(Post.id == post_id).values(comment_count=Post.comment_count + 1)
    )
    await session.commit()
    await session.refresh(comment)
    
    user = await session.get(User, user_id)
    return _comment_out(comment, user.username if user else None)