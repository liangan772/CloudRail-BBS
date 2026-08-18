"""AI 自动审核 API（两级审核的 AI 初审环节）。

- POST /audit/text   同步文本审核（需登录）
- POST /audit/image  同步图片审核（视觉模型；media_url 为 http(s) 或 data URI）
- POST /audit/post   同步帖子组合审核（标题 + 正文 + 正文图片，汇总取最严结论）

AI 初审结论由审核工作流统一落库（services.audit_flow.queue_ai_audit），
进入人工复审队列（human_status=pending）；管理后台 GET /admin/audits + PUT /admin/audits/{id}/review 完成终审。
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.core.deps import CurrentUser, get_current_user
from app.schemas.audit import (
    AuditImageRequest,
    AuditImageResponse,
    AuditPostRequest,
    AuditPostResponse,
    AuditRequest,
    AuditResponse,
)
from app.services.audit import AIAuditService, AuditError

router = APIRouter(prefix="/audit", tags=["AI 审核"])


async def _call_ai(service: AIAuditService, coro):
    """统一异常收敛：AuditError / 网络错误 → 502（mock 模式不触发）。"""
    try:
        return await coro
    except AuditError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"AI 服务调用失败: {exc}") from exc


@router.post("/text", response_model=AuditResponse, summary="同步 AI 文本审核")
async def audit_text(
    payload: AuditRequest,
    _user: CurrentUser = Depends(get_current_user),
) -> AuditResponse:
    """调用 LLM 审核文本，返回 pass / review / reject 结论与违规分。"""
    service = AIAuditService()
    result = await _call_ai(service, service.audit_text(payload.content, title=payload.title))
    return AuditResponse(**result)


@router.post("/image", response_model=AuditImageResponse, summary="同步 AI 图片审核")
async def audit_image(
    payload: AuditImageRequest,
    _user: CurrentUser = Depends(get_current_user),
) -> AuditImageResponse:
    """调用视觉模型审核单张图片（http(s) 链接或 data URI）。"""
    service = AIAuditService()
    result = await _call_ai(service, service.audit_image(payload.media_url, context=payload.context))
    return AuditImageResponse(**result, media_url=payload.media_url)


@router.post("/post", response_model=AuditPostResponse, summary="同步 AI 帖子审核（文本+图片）")
async def audit_post(
    payload: AuditPostRequest,
    _user: CurrentUser = Depends(get_current_user),
) -> AuditPostResponse:
    """帖子组合审核：正文文本 + 图片（自动从正文提取，或显式传入 image_urls）。

    汇总规则：任一图片/文本 reject 则整体 reject，否则任一 review 则整体 review。
    """
    service = AIAuditService()
    result = await _call_ai(
        service,
        service.audit_post(payload.content, title=payload.title, image_urls=payload.image_urls or None),
    )
    image_results = result.pop("image_results", [])
    return AuditPostResponse(**result, image_results=image_results)
