"""Celery 应用（Redis 作为 Broker / Backend）。"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "forum",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.celery_app",
        "app.tasks.audit_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=30,
    task_max_retries=3,
    # 投递不重试：Redis 不可用时快速失败，由调用方降级（如 posts 降级后台任务）
    broker_connection_max_retries=0,
    broker_connection_retry_on_startup=False,
    task_publish_retry=False,
    broker_transport_options={
        "max_retries": 0,
        "socket_connect_timeout": 1,
        "socket_timeout": 1,
    },
    # result backend 同样快速失败（本地无 Redis 时不等待重试）
    result_backend_transport_options={
        "max_retries": 0,
        "socket_connect_timeout": 1,
        "socket_timeout": 1,
    },
    beat_schedule={
        "sync-post-views": {
            "task": "app.tasks.sync_post_views",
            "schedule": 60.0,
        },
    },
)


@celery_app.task(bind=True, name="app.tasks.sync_post_views")
def sync_post_views(self) -> str:
    """占位任务：浏览计数合并入库（TODO 实现）。"""
    return "sync_post_views: no-op (skeleton)"