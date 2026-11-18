from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery(
    "fleetmind",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.email"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_ignore_result=True,
    broker_connection_retry_on_startup=True,
)
