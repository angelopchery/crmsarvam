"""
Celery application configuration for background tasks.
"""
import os
import logging
from celery import Celery

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create Celery application
celery_app = Celery(
    "crmsarvam",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.transcription_worker",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task settings
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit
    task_acks_late=True,  # Only ack after task completes
    worker_prefetch_multiplier=1,  # Disable prefetching for better fairness
    # Result settings
    result_expires=86400,  # Results expire after 24 hours
    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    # Routing
    task_routes={
        "app.workers.transcription_worker.process_transcription": {
            "queue": "transcription",
            "routing_key": "transcription",
        },
    },
    # Task naming
    task_default_queue="default",
)

logger.info("Celery application configured")
