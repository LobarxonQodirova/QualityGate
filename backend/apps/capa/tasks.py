"""
Celery tasks for CAPA app.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_overdue_capa_tasks(self):
    """
    Check for overdue CAPA tasks and send notification emails.
    Runs daily via Celery Beat.
    """
    from .models import CAPATask, CorrectiveAction, PreventiveAction

    today = timezone.now().date()

    # Find overdue CAPA tasks
    overdue_tasks = CAPATask.objects.filter(
        due_date__lt=today,
    ).exclude(
        status__in=[CAPATask.Status.COMPLETED, CAPATask.Status.CANCELLED],
    ).select_related("assigned_to", "corrective_action", "preventive_action")

    overdue_count = overdue_tasks.count()
    logger.info("Found %d overdue CAPA tasks.", overdue_count)

    # Group by assignee and send notifications
    assignee_tasks = {}
    for task in overdue_tasks:
        if task.assigned_to and task.assigned_to.email:
            assignee_tasks.setdefault(task.assigned_to, []).append(task)

    for user, tasks in assignee_tasks.items():
        try:
            task_lines = []
            for t in tasks:
                parent = t.corrective_action or t.preventive_action
                parent_num = ""
                if t.corrective_action:
                    parent_num = t.corrective_action.ca_number
                elif t.preventive_action:
                    parent_num = t.preventive_action.pa_number
                days_overdue = (today - t.due_date).days
                task_lines.append(
                    f"  - [{parent_num}] {t.title} (Due: {t.due_date}, {days_overdue} days overdue)"
                )

            body = (
                f"Hello {user.first_name or user.username},\n\n"
                f"You have {len(tasks)} overdue CAPA task(s):\n\n"
                + "\n".join(task_lines)
                + "\n\nPlease update the status of these tasks in QualityGate."
                + "\n\nRegards,\nQualityGate System"
            )

            send_mail(
                subject=f"[QualityGate] {len(tasks)} Overdue CAPA Task(s)",
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            logger.info("Sent overdue notification to %s for %d tasks.", user.email, len(tasks))
        except Exception as exc:
            logger.error("Failed to send overdue notification to %s: %s", user.email, exc)

    # Check for CAs approaching due date (3 days warning)
    warning_date = today + timedelta(days=3)
    upcoming_cas = CorrectiveAction.objects.filter(
        target_date=warning_date,
    ).exclude(
        status__in=[
            CorrectiveAction.Status.CLOSED,
            CorrectiveAction.Status.CANCELLED,
            CorrectiveAction.Status.VERIFIED_EFFECTIVE,
        ],
    ).select_related("assigned_to")

    for ca in upcoming_cas:
        if ca.assigned_to and ca.assigned_to.email:
            try:
                send_mail(
                    subject=f"[QualityGate] CA {ca.ca_number} due in 3 days",
                    message=(
                        f"Hello {ca.assigned_to.first_name or ca.assigned_to.username},\n\n"
                        f"Corrective Action {ca.ca_number} - \"{ca.title}\" is due on {ca.target_date}.\n"
                        f"Current status: {ca.get_status_display()}\n\n"
                        f"Please ensure all tasks are completed by the target date.\n\n"
                        f"Regards,\nQualityGate System"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[ca.assigned_to.email],
                    fail_silently=False,
                )
            except Exception as exc:
                logger.error("Failed to send warning for CA %s: %s", ca.ca_number, exc)

    return {
        "overdue_tasks": overdue_count,
        "notifications_sent": len(assignee_tasks),
        "upcoming_ca_warnings": upcoming_cas.count(),
    }


@shared_task(bind=True)
def send_capa_assignment_notification(self, capa_type, capa_id):
    """
    Send notification when a CAPA is assigned to someone.
    Called programmatically when assignment changes.
    """
    from .models import CorrectiveAction, PreventiveAction

    try:
        if capa_type == "corrective":
            capa = CorrectiveAction.objects.select_related("assigned_to", "initiated_by").get(id=capa_id)
            number = capa.ca_number
        else:
            capa = PreventiveAction.objects.select_related("assigned_to", "initiated_by").get(id=capa_id)
            number = capa.pa_number

        if not capa.assigned_to or not capa.assigned_to.email:
            logger.warning("No assignee email for %s %s", capa_type, number)
            return

        send_mail(
            subject=f"[QualityGate] {capa_type.title()} Action {number} assigned to you",
            message=(
                f"Hello {capa.assigned_to.first_name or capa.assigned_to.username},\n\n"
                f"A {capa_type} action has been assigned to you:\n\n"
                f"Number: {number}\n"
                f"Title: {capa.title}\n"
                f"Priority: {capa.get_priority_display()}\n"
                f"Target Date: {capa.target_date}\n"
                f"Initiated By: {capa.initiated_by.get_full_name() if capa.initiated_by else 'N/A'}\n\n"
                f"Please review and begin working on this action.\n\n"
                f"Regards,\nQualityGate System"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[capa.assigned_to.email],
            fail_silently=False,
        )
        logger.info("Sent assignment notification for %s %s to %s", capa_type, number, capa.assigned_to.email)
    except Exception as exc:
        logger.error("Failed to send assignment notification: %s", exc)
        raise self.retry(exc=exc)
