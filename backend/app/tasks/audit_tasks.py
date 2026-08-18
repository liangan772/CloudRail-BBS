"""AI 自动审核异步任务（两级审核流程的 AI 初审环节）。

使用方式：
    audit_content.delay(content, target_type="post", target_id=post_id, title=title)
    audit_image.delay(media_url, target_id=post_id, context=...)

审核逻辑统一委托 services.audit_flow.queue_ai_audit_sync：
AI 初审 → 结论落库 audit_records（human_status=pending 进入人工复审队列）→ reject 自动下架。
"""

import logging

from app.services import audit_flow
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.audit_content", max_retries=3)
def audit_content(
    self,
    content: str,
    target_type: str = "post",
    target_id: int | None = None,
    title: str | None = None,
) -> dict:
    """异步 AI 内容审核（帖子=文本+图片组合；评论等=文本），结果落库并进入人工复审队列。"""
    try:
        return audit_flow.queue_ai_audit_sync(
            target_type=target_type,
            target_id=target_id,
            content=content or "",
            title=title,
        )
    except Exception as exc:  # noqa: BLE001 非预期异常：指数退避重试
        logger.error("audit_content failed: %s", exc)
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1)) from exc


@celery_app.task(bind=True, name="app.tasks.audit_image", max_retries=3)
def audit_image(
    self,
    media_url: str,
    target_id: int | None = None,
    context: str = "",
) -> dict:
    """异步 AI 图片审核（视觉模型），结果落库并进入人工复审队列。"""
    try:
        return audit_flow.queue_ai_audit_sync(
            target_type="image",
            target_id=target_id,
            content=context or "图片审核",
            media_url=media_url,
            context=context,
        )
    except Exception as exc:  # noqa: BLE001 非预期异常：指数退避重试
        logger.error("audit_image failed: %s", exc)
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1)) from exc
