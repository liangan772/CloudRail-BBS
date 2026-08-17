"""SQLAlchemy 模型层。

按 docs/开发文档.md 第 5 章规划的表结构逐模块实现；
导入约定：`from app.models import Base`，Base 在此包统一导出供 Alembic autogenerate 使用。
注意：必须先定义 Base 再导入子模块（子模块内引用 Base，避免循环导入）。
"""

from sqlalchemy import BigInteger, Integer
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 ORM 模型的声明基类。"""


# 大整数主键：PostgreSQL 用 BIGINT，SQLite 开发降级用 INTEGER（否则无法自增）
BigIntPk = BigInteger().with_variant(Integer, "sqlite")


from app.models.admin_log import AdminLog  # noqa: E402
from app.models.audit import AuditRecord  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models.comment import Comment  # noqa: E402
from app.models.post import Post  # noqa: E402
from app.models.site_config import SiteConfig  # noqa: E402
from app.models.user import User  # noqa: E402

__all__ = [
    "Base",
    "BigIntPk",
    "AdminLog",
    "AuditRecord",
    "Category",
    "Comment",
    "Post",
    "SiteConfig",
    "User",
]
