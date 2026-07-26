"""Celery beat task — nightly lesson generation."""

import logging
from datetime import date

from src.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="generate_daily_lessons")
def generate_daily_lessons_task() -> dict:
    """Nightly batch: generate tomorrow's lessons for all active schedules."""
    logger.info("Daily lesson generation triggered")
    # TODO: Implement in v2 — iterate all active schedules, generate lessons
    return {"status": "ok", "lessons_generated": 0}
