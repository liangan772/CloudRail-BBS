"""运营统计服务（管理后台仪表盘）。"""

from datetime import datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditRecord
from app.models.comment import Comment
from app.models.post import Post
from app.models.report import Report
from app.models.user import User

# 站内统计以 Asia/Shanghai（北京时间）计算“今日”起点
TZ = ZoneInfo("Asia/Shanghai")


async def get_overview(session: AsyncSession) -> dict:
    """仪表盘核心指标：总量 + 今日新增 + 待办队列。"""
    now = datetime.now(TZ)
    today_start = datetime.combine(now.date(), time.min, tzinfo=TZ)

    user_total = await session.scalar(select(func.count()).select_from(User))
    user_today = await session.scalar(
        select(func.count()).select_from(User).where(User.created_at >= today_start)
    )
    post_total = await session.scalar(
        select(func.count()).select_from(Post).where(Post.status != 3)
    )
    post_today = await session.scalar(
        select(func.count()).select_from(Post)
        .where(Post.status != 3, Post.created_at >= today_start)
    )
    comment_total = await session.scalar(
        select(func.count()).select_from(Comment).where(Comment.status != 2)
    )
    comment_today = await session.scalar(
        select(func.count()).select_from(Comment)
        .where(Comment.status != 2, Comment.created_at >= today_start)
    )
    pending_audits = await session.scalar(
        select(func.count()).select_from(AuditRecord).where(AuditRecord.human_status == "pending")
    )
    pending_reports = await session.scalar(
        select(func.count()).select_from(Report).where(Report.status == 0)
    )

    return {
        "users": {"total": user_total or 0, "today": user_today or 0},
        "posts": {"total": post_total or 0, "today": post_today or 0},
        "comments": {"total": comment_total or 0, "today": comment_today or 0},
        "pending_audits": pending_audits or 0,
        "pending_reports": pending_reports or 0,
    }
