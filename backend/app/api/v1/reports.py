"""举报（用户侧）。

- POST /reports  举报帖子/评论/用户（登录；同一举报人对同一目标 24h 内限一次）
管理端队列见 api/v1/admin/reports.py。
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.models.comment import Comment
from app.models.post import Post
from app.models.report import Report
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["举报"])

REPORT_WINDOW = timedelta(hours=24)


class ReportCreate(BaseModel):
    target_type: str = Field(pattern="^(post|comment|user)$", description="举报目标类型")
    target_id: int = Field(ge=1, description="举报目标 ID")
    reason: str = Field(min_length=1, max_length=255, description="举报理由")


@router.post("", summary="举报帖子/评论/用户（24h 限一次）")
async def create_report(
    payload: ReportCreate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    # 1. 目标必须存在且可见
    if payload.target_type == "post":
        target = await session.get(Post, payload.target_id)
        if target is None or target.status != 0:
            raise HTTPException(status_code=404, detail="举报目标不存在")
    elif payload.target_type == "comment":
        target = await session.get(Comment, payload.target_id)
        if target is None or target.status != 0:
            raise HTTPException(status_code=404, detail="举报目标不存在")
    else:
        target = await session.get(User, payload.target_id)
        if target is None:
            raise HTTPException(status_code=404, detail="举报目标不存在")
        if target.id == user.id:
            raise HTTPException(status_code=400, detail="不能举报自己")

    # 2. 同一举报人 24h 内对同一目标限一次
    since = datetime.now(timezone.utc) - REPORT_WINDOW
    exists = await session.scalar(
        select(func.count())
        .select_from(Report)
        .where(
            Report.reporter_id == user.id,
            Report.target_type == payload.target_type,
            Report.target_id == payload.target_id,
            Report.created_at >= since,
        )
    )
    if exists:
        raise HTTPException(status_code=429, detail="您已举报过该内容，请勿重复举报")

    report = Report(
        reporter_id=user.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        reason=payload.reason,
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    logger.info("新举报 #%s %s:%s by user %s", report.id, payload.target_type, payload.target_id, user.id)
    return {"id": report.id, "status": report.status}
