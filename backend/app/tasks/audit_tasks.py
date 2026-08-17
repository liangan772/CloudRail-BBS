"""AI 自动审核异步任务。

使用方式（发帖/评论后调用，见文档 7.3 / 9.16）：
    audit_content.delay(content, target_type="post", target_id=post_id, title=title)

TODO（接入数据库会话后）：
- 审核结果写入 audit_records 表（AuditRecord 模型已就绪）
- result=reject 时自动将目标内容置为「待审核」并通知管理员
- result=review 时标记目标内容进入人工审核队列
"""

import logging

from app.services.audit import AIAuditService, AuditError
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
    """异步 AI 内容审核（同步调用 LLM，返回结构化结果）。"""
    service = AIAuditService()
    try:
        result = service.audit_text_sync(content, title=title)
    except AuditError as exc:
        logger.warning("audit_content skipped: %s", exc)
        return {"skipped": True, "reason": str(exc)}
    except Exception as exc:  # 网络等异常：指数退避重试
        logger.error("audit_content failed: %s", exc)
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1)) from exc

    # TODO: result 落库 audit_records（含 target_type/target_id）；reject 自动下架、review 转人工
    logger.info(
        "audit_content result=%s score=%s target=%s:%s",
        result["result"],
        result["score"],
        target_type,
        target_id,
    )
    return result
