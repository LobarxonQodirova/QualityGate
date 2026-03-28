"""
Celery tasks for inspections app.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Avg, Count, F, Q, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_overdue_inspections(self):
    """
    Find planned inspections past their scheduled date that have not started.
    Sends reminder emails to assigned inspectors.
    Runs daily via Celery Beat.
    """
    from .models import Inspection

    now = timezone.now()
    overdue_inspections = Inspection.objects.filter(
        status=Inspection.Status.PLANNED,
        scheduled_date__lt=now,
    ).select_related("inspector", "checklist")

    count = overdue_inspections.count()
    logger.info("Found %d overdue planned inspections.", count)

    notified = 0
    for inspection in overdue_inspections:
        if not inspection.inspector or not inspection.inspector.email:
            continue

        days_overdue = (now - inspection.scheduled_date).days
        try:
            send_mail(
                subject=(
                    f"[QualityGate] Overdue Inspection {inspection.inspection_number} "
                    f"({days_overdue} day(s))"
                ),
                message=(
                    f"Hello {inspection.inspector.first_name or inspection.inspector.username},\n\n"
                    f"The following inspection is overdue:\n\n"
                    f"  Number: {inspection.inspection_number}\n"
                    f"  Product: {inspection.product_name}\n"
                    f"  Part: {inspection.part_number or 'N/A'}\n"
                    f"  Checklist: {inspection.checklist.name}\n"
                    f"  Scheduled: {inspection.scheduled_date.strftime('%Y-%m-%d %H:%M')}\n"
                    f"  Days Overdue: {days_overdue}\n\n"
                    f"Please start this inspection as soon as possible.\n\n"
                    f"Regards,\nQualityGate System"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[inspection.inspector.email],
                fail_silently=False,
            )
            notified += 1
        except Exception as exc:
            logger.error(
                "Failed to send overdue notice for %s: %s",
                inspection.inspection_number, exc,
            )

    return {"overdue_inspections": count, "notifications_sent": notified}


@shared_task(bind=True)
def generate_daily_inspection_summary(self):
    """
    Generate and email a daily summary of inspection activity.
    Sent to quality managers at end of day.
    """
    from apps.accounts.models import User
    from .models import Inspection

    today = timezone.now().date()
    start_of_day = timezone.make_aware(
        timezone.datetime.combine(today, timezone.datetime.min.time())
    )
    end_of_day = start_of_day + timedelta(days=1)

    completed_today = Inspection.objects.filter(
        status=Inspection.Status.COMPLETED,
        completed_at__range=(start_of_day, end_of_day),
    )
    started_today = Inspection.objects.filter(
        status=Inspection.Status.IN_PROGRESS,
        started_at__range=(start_of_day, end_of_day),
    )
    planned_tomorrow = Inspection.objects.filter(
        status=Inspection.Status.PLANNED,
        scheduled_date__date=today + timedelta(days=1),
    )

    # Disposition breakdown for completed inspections
    accepted = completed_today.filter(disposition=Inspection.Disposition.ACCEPT).count()
    rejected = completed_today.filter(disposition=Inspection.Disposition.REJECT).count()
    conditional = completed_today.filter(disposition=Inspection.Disposition.CONDITIONAL).count()
    rework = completed_today.filter(disposition=Inspection.Disposition.REWORK).count()

    body_lines = [
        f"QualityGate Daily Inspection Summary for {today.isoformat()}\n",
        f"{'=' * 55}\n",
        f"Inspections Completed Today: {completed_today.count()}",
        f"  - Accepted: {accepted}",
        f"  - Rejected: {rejected}",
        f"  - Conditional: {conditional}",
        f"  - Rework: {rework}",
        f"\nInspections Started Today: {started_today.count()}",
        f"Inspections Scheduled Tomorrow: {planned_tomorrow.count()}\n",
    ]

    # List rejected inspections for visibility
    if rejected > 0:
        body_lines.append("Rejected Inspections (require attention):")
        for insp in completed_today.filter(disposition=Inspection.Disposition.REJECT):
            body_lines.append(
                f"  - {insp.inspection_number}: {insp.product_name} "
                f"(Part: {insp.part_number or 'N/A'}, "
                f"Inspector: {insp.inspector.get_full_name() if insp.inspector else 'N/A'})"
            )
        body_lines.append("")

    body_lines.append("Regards,\nQualityGate System")
    body = "\n".join(body_lines)

    # Send to quality managers
    managers = User.objects.filter(
        role__in=[User.Role.QUALITY_MANAGER, User.Role.ADMIN],
        is_active=True,
    ).values_list("email", flat=True)
    recipients = [e for e in managers if e]

    if recipients:
        try:
            send_mail(
                subject=f"[QualityGate] Daily Inspection Summary - {today.isoformat()}",
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                fail_silently=False,
            )
            logger.info("Daily inspection summary sent to %d recipients.", len(recipients))
        except Exception as exc:
            logger.error("Failed to send daily inspection summary: %s", exc)

    return {
        "date": today.isoformat(),
        "completed": completed_today.count(),
        "accepted": accepted,
        "rejected": rejected,
        "recipients": len(recipients),
    }
