"""管理后台：举报队列与处理。"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, require_role
from app.models.admin_log import AdminLog
from app.models.comment import Comment
from app.models.post import Post
from app.models.report import Report
from app.models.user import User
from app.services import auth as auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/reports", tags=["管理后台"])

REPORT_STATUS_LABEL = {0: "待处理", 1: "已处理", 2: "已忽略"}


class ReportHandleRequest(BaseModel):
    action: str = Field(pattern="^(ignore|remove|ban_user)$", description="ignore 忽略 / remove 删除内容 / ban_user 封禁用户")
    note: str = Field(default="", max_length=255)


def _report_out(report: Report, reporter: str | None, target_summary: str) -> dict:
    return {
        "id": report.id,
        "reporter_id": report.reporter_id,
        "reporter": reporter,
        "target_type": report.target_type,
        "target_id": report.target_id,
        "target_summary": target_summary,
        "reason": report.reason,
        "status": report.status,
        "handled_by": report.handled_by,
        "handled_at": report.handled_at.isoformat() if report.handled_at else None,
        "handle_note": report.handle_note,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


async def _target_summary(session: AsyncSession, report: Report) -> str:
    """举报目标摘要：帖子标题 / 评论内容 / 用户名。"""
    if report.target_type == "post":
        post = await session.get(Post, report.target_id)
        return post.title[:60] if post else "（帖子已删除）"
    if report.target_type == "comment":
        comment = await session.get(Comment, report.target_id)
        return comment.content[:60] if comment else "（评论已删除）"
    user = await session.get(User, report.target_id)
    return user.username if user else "（用户已删除）"


@router.get("", summary="举报队列（分页）")
async def list_reports(
    status: int = Query(0, ge=0, le=2, description="0 待处理 / 1 已处理 / 2 已忽略"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    _admin: CurrentUser = Depends(require_role(2)),
) -> dict:
    stmt = select(Report).where(Report.status == status)
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (
        (
            await session.execute(
                stmt.order_by(Report.id.desc()).offset((page - 1) * limit).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    items: list[dict] = []
    for report in rows:
        reporter = await session.get(User, report.reporter_id)
        summary = await _target_summary(session, report)
        items.append(_report_out(report, reporter.username if reporter else None, summary))
    return {"total": total or 0, "page": page, "limit": limit, "items": items}


@router.put("/{report_id}", summary="处理举报（忽略/删除内容/封禁用户）")
async def handle_report(
    payload: ReportHandleRequest,
    report_id: int = Path(ge=1),
    session: AsyncSession = Depends(get_db),
    admin: CurrentUser = Depends(require_role(2)),
) -> dict:
    report = await session.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="举报不存在")
    if report.status != 0:
        raise HTTPException(status_code=400, detail="该举报已处理")

    # 定位举报目标（post/comment 需找到作者，user 即目标）
    author_id: int | None = None
    post: Post | None = None
    comment: Comment | None = None

    if report.target_type == "post":
        post = await session.get(Post, report.target_id)
        if post is None:
            raise HTTPException(status_code=404, detail="被举报帖子不存在")
        author_id = post.user_id
    elif report.target_type == "comment":
        comment = await session.get(Comment, report.target_id)
        if comment is None:
            raise HTTPException(status_code=404, detail="被举报评论不存在")
        author_id = comment.user_id

    detail = payload.note or f"action={payload.action}"
    if payload.action == "remove":
        # 删除内容（软删除）：帖子 status=3 / 评论 status=2
        if report.target_type == "post" and post:
            post.status = 3
        elif report.target_type == "comment" and comment:
            comment.status = 2
        else:
            raise HTTPException(status_code=400, detail="remove 仅支持帖子/评论")
        report.status = 1
    elif payload.action == "ban_user":
        # 封禁用户（作者或直接目标用户）
        target_user_id = author_id if report.target_type in ("post", "comment") else report.target_id
        user = await session.get(User, target_user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="目标用户不存在")
        if user.id == admin.id:
            raise HTTPException(status_code=400, detail="不能封禁自己")
        user.status = 2
        detail = f"封禁用户 {user.username}" + (f"（{payload.note}）" if payload.note else "")
        report.status = 1
    elif payload.action == "ignore":
        report.status = 2  # 修复：设置为 2（已忽略）

    report.handled_by = admin.id
    report.handled_at = datetime.now(timezone.utc)
    report.handle_note = payload.note
    await session.commit()

    # 审计留痕
    try:
        session.add(
            AdminLog(
                admin_id=admin.id,
                action="report.handle",
                target_type="report",
                target_id=str(report_id),
                detail=detail,
            )
        )
        await session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("审计日志写入失败: %s", exc)
        await session.rollback()

    return {"id": report.id, "status": report.status, "action": payload.action}