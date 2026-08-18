"""敏感词模型（sensitive_words 表，持久化敏感词库）。"""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, BigIntPk


class SensitiveWord(Base):
    """敏感词库（DB 持久化；启动时加载进 DFA 过滤器，管理端可增删）。"""

    __tablename__ = "sensitive_words"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
