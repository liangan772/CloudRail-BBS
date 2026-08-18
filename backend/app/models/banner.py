"""轮播图模型（banners 表）。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, BigIntPk


class Banner(Base):
    """首页轮播图（运营位），支持排序、启停与展示时段。"""

    __tablename__ = "banners"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(64), nullable=False)
    image_url: Mapped[str] = mapped_column(String(512), nullable=False)
    link_url: Mapped[str] = mapped_column(String(512), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
