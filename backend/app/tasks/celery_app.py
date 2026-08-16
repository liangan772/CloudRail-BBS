"""Celery 应用（Redis 作为 Broker / Backend）。

启动 Worker：celery -A app.tasks.celery_app:celery_app worker --loglevel=info
启动 Beat：  celery -A app.tasks.celery_app:celery_app beat --loglevel=info

任务清单见文档 7.3：send_notification / sync_post_views / sync_likes / recalc_hot_rank /
push_notification / sync_sign_in / recalc_rank / check_achievements / recalc_topic_hot /
clean_view_history / send_report_result / send_email / process_image / clean_expired_data。
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "forum",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.celery_app"],
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
    beat_schedule={
        # 示例定时任务；实现后按文档 7.3 补齐
        "sync-post-views": {
            "task": "app.tasks.sync_post_views",
            "schedule": 60.0,
        },
    },
)


@app.task(bind=True, name="app.tasks.sync_post_views")
def sync_post_views(self) -> str:
    """占位任务：浏览计数合并入库（TODO 实现）。"""
    return "sync_post_views: no-op (skeleton)"
