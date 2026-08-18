"""管理后台：AI 审核记录（人工复审队列）——两级审核的人工复审环节。

- GET  /admin/audits            复审队列（默认待复审 human_status=pending，支持过滤/分页）
- PUT  /admin/audits/{id}/review 人工复审：approved=通过 / rejected=驳回（同步帖子/评论可见状态）
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import CurrentUser, require_role
from app.models.admin_log import AdminLog
from app.models.audit import AuditRecord
from app.services import audit_flow

router = APIRouter(prefix="/admin/audits", tags=["管理后台"])


class AuditReviewRequest(BaseModel):
    action: str = Field(pattern="^(approved|rejected)$", description="复审结论：approved 通过 / rejected 驳回")
    note: str = Field(default="", max_length=255, description="复审备注（驳回时建议填写原因）")


@router.get("", summary="AI 审核记录（复审队列）")
async def list_audits(
    human_status: str = Query(
        "pending",
        pattern="^(pending|approved|rejected|all)$",
        description="人工复审状态；all=全部",
    ),
    target_type: str | None = Query(None, pattern="^(post|comment|image)$", description="目标类型过滤"),
    result: str | None = Query(None, pattern="^(pass|review|reject)$", description="AI 初审结论过滤"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    _admin: CurrentUser = Depends(require_role(2)),
) -> dict:
    """审核记录分页列表。默认只返回待人工复审（pending）的记录。"""
    stmt = select(AuditRecord)
    if human_status != "all":
        stmt = stmt.where(AuditRecord.human_status == human_status)
    if target_type:
        stmt = stmt.where(AuditRecord.target_type == target_type)
    if result:
        stmt = stmt.where(AuditRecord.result == result)

    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (
        (
            await session.execute(
                stmt.order_by(AuditRecord.id.desc()).offset((page - 1) * limit).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return {"total": total or 0, "page": page, "limit": limit, "items": audit_flow.records_out(rows)}


@router.put("/{record_id}/review", summary="人工复审 AI 审核记录")
async def review_audit(
    payload: AuditReviewRequest,
    record_id: int = Path(ge=1),
    session: AsyncSession = Depends(get_db),
    admin: CurrentUser = Depends(require_role(2)),
) -> dict:
    """人工复审：approved=通过（恢复/保持可见），rejected=驳回（下架隐藏）。"""
    record = await session.get(AuditRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="审核记录不存在")
    if record.human_status != "pending":
        raise HTTPException(status_code=400, detail="该记录已完成复审，不可重复操作")

    try:
        await audit_flow.review_record(
            session,
            record_id=record_id,
            action=payload.action,
            reviewer_id=admin.id,
            note=payload.note,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # 管理操作审计留痕（失败仅告警，不阻断主流程）
    try:
        session.add(
            AdminLog(
                admin_id=admin.id,
                action="audit.review",
                target_type="audit_record",
                target_id=str(record_id),
                detail=f"{payload.action} note={payload.note}",
            )
        )
        await session.commit()
    except Exception:  # noqa: BLE001
        await session.rollback()

    return {"id": record.id, "human_status": record.human_status, "reviewed_at": datetime.now(UTC).isoformat()}
