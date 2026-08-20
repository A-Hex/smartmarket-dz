# backend/app/jobs/celery_app.py
"""
Celery application instance.

Task modules (cleaning, analytics, decision, reports) are registered here as
they are implemented in later phases (see BUILD SEQUENCE section 16). Phase 1
only wires the app so `docker-compose up worker` starts cleanly.
"""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "smartmarket",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# celery_app.autodiscover_tasks(["app.jobs"])  # enabled once task modules exist
