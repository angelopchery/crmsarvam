"""
Celery application — single source of truth.

Both FastAPI (which enqueues tasks) and the worker (which consumes them)
import `celery_app` from this module. One instance, one broker URL, no
custom routing — this guarantees .delay() lands on the same queue the
worker is listening on.
"""
import logging

from celery import Celery

from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "crmsarvam",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.transcription_worker"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3300,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=86400,
    task_default_retry_delay=60,
    task_max_retries=3,
)

logger.info(f"Celery app configured (broker={settings.REDIS_URL})")
