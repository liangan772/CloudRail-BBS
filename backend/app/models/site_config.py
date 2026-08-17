"""站点配置表（site_configs，key-value）。

管理后台可配置项（v1.4）：
- post_image_enabled：帖子是否允许展示图片（true/false）
- site_name：站点名称
"""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class SiteConfig(Base):
    __tablename__ = "site_configs"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(String(255), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
