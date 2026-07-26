"""Celery application with Redis broker and task routing."""

from celery import Celery

from src.core.config import settings

celery_app = Celery(
    "linguanotebook",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "src.workers.parse_worker",
        "src.workers.embed_worker",
        "src.workers.lesson_worker",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "src.workers.parse_worker.*": {"queue": "parsing"},
        "src.workers.embed_worker.*": {"queue": "embedding"},
        "src.workers.lesson_worker.*": {"queue": "lessons"},
    },
)
