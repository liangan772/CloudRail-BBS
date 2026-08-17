"""AI 审核记录表（audit_records）。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, BigIntPk


class AuditRecord(Base):
    """AI 内容审核记录（每次调用 LLM 审核落一条，支持追溯与人工复核）。"""

    __tablename__ = "audit_records"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    target_type: Mapped[str] = mapped_column(String(16), default="post")  # post / comment / user
    target_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, default=None)
    content: Mapped[str] = mapped_column(Text)
    result: Mapped[str] = mapped_column(String(16))  # pass / review / reject
    score: Mapped[float] = mapped_column(Float, default=0.0)
    categories: Mapped[str] = mapped_column(String(255), default="")  # JSON 数组字符串
    reason: Mapped[str] = mapped_column(String(255), default="")
    model: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
