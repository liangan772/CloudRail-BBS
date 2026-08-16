"""SQLAlchemy 模型层。

骨架阶段为空；实现时按 docs/开发文档.md 第 5 章创建：
users / categories / posts / comments / tags / post_tags / likes / favorites / follows /
notifications / messages / oauth_accounts / user_devices / sign_in_records / points_records /
achievements / user_achievements / daily_tasks / user_tasks / banners / reports / blocks /
drafts / polls / poll_options / poll_votes / topic_follows / view_history / sensitive_words /
admin_logs / app_versions

导入约定：`from app.models import Base`，Base 在此包统一导出供 Alembic autogenerate 使用。
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 ORM 模型的声明基类。"""
