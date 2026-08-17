"""AI 审核请求 / 响应 Schema。"""

from pydantic import BaseModel, Field


class AuditRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20000, description="待审核内容（帖子正文 / 评论等）")
    title: str | None = Field(default=None, max_length=128, description="可选标题，辅助判断上下文")


class AuditResponse(BaseModel):
    result: str = Field(description="审核结论：pass 通过 / review 转人工 / reject 拦截")
    score: float = Field(ge=0, le=100, description="违规程度 0-100，越高越违规")
    categories: list[str] = Field(default_factory=list, description="命中的违规类别")
    reason: str = Field(default="", description="判定理由（中文）")
    model: str = Field(default="", description="使用的模型")
