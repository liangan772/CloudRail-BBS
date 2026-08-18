"""审核工作流服务（两级审核：AI 初审 + 人工复审）——统一入口。

职责：
- queue_ai_audit：AI 初审 → 结论落库 audit_records（human_status=pending 进入人工复审队列）→ reject 自动下架
- queue_ai_audit_sync：Celery 任务内同步版（独立 engine，避免跨 event loop 复用连接池）
- review：人工复审终审（approved 恢复可见 / rejected 下架隐藏）

发帖 / 评论 / 图片审核一律走本模块，路由与任务只做薄封装。
"""

import asyncio
import json
import logging
from datetime import UTC
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.models.audit import AuditRecord
from app.models.comment import Comment
from app.models.post import Post
from app.services.audit import AIAuditService, AuditError

logger = logging.getLogger(__name__)

# 目标内容可见状态（posts/comments 共用约定）：0 正常（可见）/ 1 待审核（隐藏）
STATUS_VISIBLE = 0
STATUS_HIDDEN = 1

HUMAN_STATUS_PENDING = "pending"
HUMAN_STATUS_APPROVED = "approved"
HUMAN_STATUS_REJECTED = "rejected"


def build_record(
    *,
    target_type: str,
    target_id: int | None,
    content: str,
    media_url: str | None,
    result: dict[str, Any],
) -> dict[str, Any]:
    """构造 audit_records 落库字段（AI 初审后一律进入人工复审队列）。"""
    return {
        "target_type": target_type,
        "target_id": target_id,
        "content": content or "",
        "media_url": media_url,
        "result": result["result"],
        "score": float(result.get("score", 0)),
        "categories": json.dumps(result.get("categories", []), ensure_ascii=False),
        "reason": result.get("reason", ""),
        "model": result.get("model", ""),
        "human_status": HUMAN_STATUS_PENDING,
    }


def _first_image_url(result: dict[str, Any]) -> str | None:
    """帖子组合审核结果中取第一张图片地址（供后台复审预览）。"""
    image_results = result.get("image_results") or []
    if image_results and image_results[0].get("media_url"):
        return str(image_results[0]["media_url"])
    return None


async def _apply_ai_result(
    session: AsyncSession,
    *,
    target_type: str,
    target_id: int | None,
    content: str,
    media_url: str | None,
    result: dict[str, Any],
) -> AuditRecord:
    """AI 初审结论落库；reject 时自动下架目标内容（等待人工复审终审）。"""
    record = AuditRecord(**build_record(
        target_type=target_type,
        target_id=target_id,
        content=content,
        media_url=media_url,
        result=result,
    ))
    session.add(record)
    if result["result"] == "reject" and target_id is not None:
        await _hide_target(session, target_type, target_id)
    await session.commit()
    await session.refresh(record)
    return record


async def _hide_target(session: AsyncSession, target_type: str, target_id: int) -> None:
    """reject 自动下架：帖子/评论置为「待审核」（前端不可见）。"""
    if target_type == "post":
        post = await session.get(Post, target_id)
        if post is not None and post.status == STATUS_VISIBLE:
            post.status = STATUS_HIDDEN
    elif target_type == "comment":
        comment = await session.get(Comment, target_id)
        if comment is not None and comment.status == STATUS_VISIBLE:
            comment.status = STATUS_HIDDEN


async def queue_ai_audit(
    session: AsyncSession,
    *,
    target_type: str,
    target_id: int | None,
    content: str,
    title: str | None = None,
    media_url: str | None = None,
    context: str = "",
) -> dict[str, Any]:
    """AI 初审并落库（FastAPI 请求内使用；async 审核模式由 Celery 调用 sync 版本）。

    返回 {result, score, categories, reason, model, record_id}；
    AI 未启用 / 调用异常时返回 {"skipped": True, "reason": ...}（不阻塞业务）。
    """
    service = AIAuditService()
    try:
        if target_type == "post":
            result = await service.audit_post(content, title=title)
            media_url = media_url or _first_image_url(result)
        elif target_type == "image":
            result = await service.audit_image(media_url or "", context=context)
        else:  # comment / 其他文本
            result = await service.audit_text(content, title=title)
    except AuditError as exc:
        logger.warning("AI 审核跳过 target=%s:%s: %s", target_type, target_id, exc)
        return {"skipped": True, "reason": str(exc)}
    except Exception as exc:  # noqa: BLE001 网络等异常：降级放行，由人工复审兜底
        logger.warning("AI 审核调用失败 target=%s:%s: %s", target_type, target_id, exc)
        return {"skipped": True, "reason": str(exc)}

    try:
        record = await _apply_ai_result(
            session,
            target_type=target_type,
            target_id=target_id,
            content=content or "",
            media_url=media_url,
            result=result,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("audit_record 落库失败: %s", exc)
        await session.rollback()
        return {"skipped": True, "reason": f"落库失败: {exc}"}

    logger.info(
        "AI 初审完成 result=%s score=%s target=%s:%s record=%s",
        result["result"], result["score"], target_type, target_id, record.id,
    )
    return {**result, "record_id": record.id}


def queue_ai_audit_sync(
    *,
    target_type: str,
    target_id: int | None,
    content: str,
    title: str | None = None,
    media_url: str | None = None,
    context: str = "",
) -> dict[str, Any]:
    """AI 初审并落库（Celery 任务内使用）。

    为每次调用创建独立 engine 并 dispose，避免 asyncpg 连接池跨 event loop 复用问题。
    """
    service = AIAuditService()
    try:
        if target_type == "post":
            result = service.audit_post_sync(content, title=title)
            media_url = media_url or _first_image_url(result)
        elif target_type == "image":
            result = service.audit_image_sync(media_url or "", context=context)
        else:
            result = service.audit_text_sync(content, title=title)
    except AuditError as exc:
        logger.warning("AI 审核跳过 target=%s:%s: %s", target_type, target_id, exc)
        return {"skipped": True, "reason": str(exc)}
    except Exception as exc:  # noqa: BLE001
        logger.warning("AI 审核调用失败 target=%s:%s: %s", target_type, target_id, exc)
        return {"skipped": True, "reason": str(exc)}

    async def _run() -> dict[str, Any]:
        engine = create_async_engine(settings.database_url, echo=False)
        try:
            async with AsyncSession(engine) as session:
                record = await _apply_ai_result(
                    session,
                    target_type=target_type,
                    target_id=target_id,
                    content=content or "",
                    media_url=media_url,
                    result=result,
                )
                return {**result, "record_id": record.id}
        finally:
            await engine.dispose()

    try:
        return asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        logger.error("audit_record 落库失败（sync）: %s", exc)
        return {"skipped": True, "reason": f"落库失败: {exc}"}


async def review_record(
    session: AsyncSession,
    *,
    record_id: int,
    action: str,
    reviewer_id: int,
    note: str = "",
) -> AuditRecord:
    """人工复审终审：approved=通过（恢复/保持可见），rejected=驳回（下架隐藏）。

    校验：记录必须存在且处于待复审（pending）状态。
    抛出 LookupError（记录不存在）/ ValueError（已复审）供路由转换为 HTTP 错误。
    """
    record = await session.get(AuditRecord, record_id)
    if record is None:
        raise LookupError("审核记录不存在")
    if record.human_status != HUMAN_STATUS_PENDING:
        raise ValueError("该记录已完成复审，不可重复操作")

    record.human_status = action
    record.reviewed_by = reviewer_id
    from datetime import datetime

    record.reviewed_at = datetime.now(UTC)
    record.review_note = note

    # 同步目标内容可见状态：驳回→下架隐藏，通过→恢复可见
    if record.target_id is not None:
        if record.target_type == "post":
            target = await session.get(Post, record.target_id)
        elif record.target_type == "comment":
            target = await session.get(Comment, record.target_id)
        else:
            target = None
        if target is not None:
            if action == HUMAN_STATUS_REJECTED and target.status == STATUS_VISIBLE:
                target.status = STATUS_HIDDEN
            elif action == HUMAN_STATUS_APPROVED and target.status == STATUS_HIDDEN:
                target.status = STATUS_VISIBLE

    await session.commit()
    await session.refresh(record)
    return record


def records_out(records: list[AuditRecord]) -> list[dict]:
    """审核记录序列化（供管理后台列表）。"""
    return [_record_out(r) for r in records]


def _record_out(record: AuditRecord) -> dict:
    try:
        categories = json.loads(record.categories) if record.categories else []
    except json.JSONDecodeError:
        categories = []
    if not isinstance(categories, list):
        categories = []
    return {
        "id": record.id,
        "target_type": record.target_type,
        "target_id": record.target_id,
        "content": record.content[:500],
        "media_url": record.media_url,
        "result": record.result,
        "score": record.score,
        "categories": categories,
        "reason": record.reason,
        "model": record.model,
        "human_status": record.human_status,
        "reviewed_by": record.reviewed_by,
        "reviewed_at": record.reviewed_at.isoformat() if record.reviewed_at else None,
        "review_note": record.review_note,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }
