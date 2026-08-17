"""评论模型。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, BigIntPk


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    parent_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(Integer, default=0)  # 0 正常 / 1 待审核 / 2 已删除
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
