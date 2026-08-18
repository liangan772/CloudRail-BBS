"""AI 审核记录表（audit_records）。

两级审核流程（AI 初审 + 人工复审）：
1. AI 初审：AIAuditService 审核文本 / 图片 / 帖子（文本+图片），结论落库（result/score/...）；
2. 人工复审：所有 AI 结论进入复审队列（human_status=pending），管理员在后台逐条复审：
   approved=通过（恢复/保持可见），rejected=驳回（下架隐藏），并记录复审人与备注。
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, BigIntPk


class AuditRecord(Base):
    """AI 内容审核记录（每次调用 LLM 审核落一条，支持追溯与人工复审）。"""

    __tablename__ = "audit_records"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    target_type: Mapped[str] = mapped_column(String(16), default="post")  # post / comment / image
    target_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, default=None)
    content: Mapped[str] = mapped_column(Text, default="")
    # 图片地址：target_type=image 时为被审图片；帖子带图时为第一张附图
    media_url: Mapped[str | None] = mapped_column(String(1024), nullable=True, default=None)
    result: Mapped[str] = mapped_column(String(16))  # AI 初审结论：pass / review / reject
    score: Mapped[float] = mapped_column(Float, default=0.0)
    categories: Mapped[str] = mapped_column(String(255), default="")  # JSON 数组字符串
    reason: Mapped[str] = mapped_column(String(255), default="")
    model: Mapped[str] = mapped_column(String(64), default="")
    # 人工复审（AI 初审后必须人工复审）
    human_status: Mapped[str] = mapped_column(String(16), default="pending")  # pending / approved / rejected
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, default=None)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    review_note: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
