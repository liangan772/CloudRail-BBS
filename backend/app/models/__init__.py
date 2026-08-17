"""SQLAlchemy 模型层。

按 docs/开发文档.md 第 5 章规划的表结构逐模块实现；
导入约定：`from app.models import Base`，Base 在此包统一导出供 Alembic autogenerate 使用。
"""

from sqlalchemy.orm import DeclarativeBase

from app.models.audit import AuditRecord

__all__ = ["Base", "AuditRecord"]


class Base(DeclarativeBase):
    """所有 ORM 模型的声明基类。"""
