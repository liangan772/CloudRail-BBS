"""举报模型（reports 表）。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, BigIntPk


class Report(Base):
    """用户举报（帖子/评论/用户），管理员处理：忽略 / 删除内容 / 封禁用户。"""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    reporter_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)  # post / comment / user
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[int] = mapped_column(Integer, default=0)  # 0 待处理 / 1 已处理 / 2 已忽略
    handled_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, default=None)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    handle_note: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
