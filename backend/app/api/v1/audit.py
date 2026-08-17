"""AI 自动审核 API。

按文档 6.2「AI 自动审核」：
- POST /audit/text  同步文本审核（需登录；供发帖/评论前调用、管理端复核）
- GET  /admin/audits 审核记录查询（管理后台，见 admin 模块 TODO）
"""

from fastapi import APIRouter, Depends, HTTPException

import httpx

from app.core.deps import CurrentUser, get_current_user
from app.schemas.audit import AuditRequest, AuditResponse
from app.services.audit import AIAuditService, AuditError

router = APIRouter(prefix="/audit", tags=["AI 审核"])


@router.post("/text", response_model=AuditResponse, summary="同步 AI 文本审核")
async def audit_text(
    payload: AuditRequest,
    _user: CurrentUser = Depends(get_current_user),
) -> AuditResponse:
    """调用 LLM 审核文本，返回 pass / review / reject 结论与违规分。

    未配置 AI（AI_ENABLED=false 或缺 API Key）时返回 502。
    """
    service = AIAuditService()
    try:
        result = await service.audit_text(payload.content, title=payload.title)
    except AuditError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"AI 服务调用失败: {exc}") from exc
    return AuditResponse(**result)
