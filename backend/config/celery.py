"""
Celery configuration for QualityGate project.
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("qualitygate")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

# Periodic task schedule
app.conf.beat_schedule = {
    "check-overdue-capa-tasks": {
        "task": "apps.capa.tasks.check_overdue_capa_tasks",
        "schedule": crontab(hour="8", minute="0"),
        "kwargs": {},
    },
    "recalculate-spc-control-limits": {
        "task": "apps.metrics.tasks.recalculate_spc_limits",
        "schedule": crontab(minute="*/30"),
        "kwargs": {},
    },
    "generate-daily-quality-summary": {
        "task": "apps.metrics.tasks.generate_daily_quality_summary",
        "schedule": crontab(hour="23", minute="55"),
        "kwargs": {},
    },
    "check-upcoming-audits": {
        "task": "apps.audits.tasks.notify_upcoming_audits",
        "schedule": crontab(hour="7", minute="0"),
        "kwargs": {},
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task that prints request info."""
    print(f"Request: {self.request!r}")
