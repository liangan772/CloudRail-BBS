"""AI 审核请求 / 响应 Schema（文本 / 图片 / 帖子）。"""

from pydantic import BaseModel, Field


class AuditRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20000, description="待审核内容（帖子正文 / 评论等）")
    title: str | None = Field(default=None, max_length=128, description="可选标题，辅助判断上下文")


class AuditImageRequest(BaseModel):
    media_url: str = Field(
        min_length=1,
        max_length=2048,
        description="图片地址（http(s) 链接或 data:image/... 的 data URI）",
    )
    context: str = Field(default="", max_length=2000, description="可选上下文（如图片所在帖子的摘要），辅助判断")


class AuditPostRequest(BaseModel):
    content: str = Field(min_length=1, max_length=50000, description="帖子正文")
    title: str | None = Field(default=None, max_length=128, description="可选标题，辅助判断上下文")
    image_urls: list[str] = Field(
        default_factory=list,
        max_length=8,
        description="附加图片地址（不传则自动从正文提取，最多 4 张）",
    )


class AuditResponse(BaseModel):
    result: str = Field(description="审核结论：pass 通过 / review 转人工 / reject 拦截")
    score: float = Field(ge=0, le=100, description="违规程度 0-100，越高越违规")
    categories: list[str] = Field(default_factory=list, description="命中的违规类别")
    reason: str = Field(default="", description="判定理由（中文）")
    model: str = Field(default="", description="使用的模型")


class AuditImageResponse(AuditResponse):
    media_url: str = Field(default="", description="被审核的图片地址")


class AuditPostResponse(AuditResponse):
    image_results: list[AuditImageResponse] = Field(
        default_factory=list, description="每张图片的独立审核结果（正文提取或显式传入）"
    )
