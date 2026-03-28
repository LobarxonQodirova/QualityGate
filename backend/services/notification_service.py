"""
Notification Service.

Centralized notification handling for the QualityGate system.
Sends email notifications for quality events such as defect creation,
inspection completion, CAPA assignments, audit findings, and overdue items.
"""

import logging
from typing import Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Sends quality-event notifications via email.

    All methods are safe to call -- exceptions are caught and logged
    rather than propagated, so callers are never blocked by email failures.
    """

    FROM_EMAIL = None  # Will fall back to settings.DEFAULT_FROM_EMAIL

    @classmethod
    def _get_from_email(cls):
        return cls.FROM_EMAIL or settings.DEFAULT_FROM_EMAIL

    # ------------------------------------------------------------------
    #  Defect notifications
    # ------------------------------------------------------------------
    @classmethod
    def notify_defect_created(cls, defect):
        """Notify assigned user that a new defect has been created."""
        if not defect.assigned_to or not defect.assigned_to.email:
            return

        subject = f"[QualityGate] New Defect {defect.defect_number} - {defect.get_severity_display()}"
        body = (
            f"Hello {defect.assigned_to.first_name or defect.assigned_to.username},\n\n"
            f"A new defect has been assigned to you:\n\n"
            f"  Number: {defect.defect_number}\n"
            f"  Title: {defect.title}\n"
            f"  Severity: {defect.get_severity_display()}\n"
            f"  Product: {defect.product_name}\n"
            f"  Part: {defect.part_number or 'N/A'}\n"
            f"  Reported By: {defect.reported_by.get_full_name() if defect.reported_by else 'N/A'}\n"
            f"  Target Close: {defect.target_close_date or 'Not set'}\n\n"
            f"Please review and begin containment / investigation.\n\n"
            f"Regards,\nQualityGate System"
        )
        cls._send(subject, body, [defect.assigned_to.email])

    @classmethod
    def notify_defect_status_changed(cls, defect, old_status):
        """Notify relevant parties when a defect status changes."""
        recipients = set()
        if defect.reported_by and defect.reported_by.email:
            recipients.add(defect.reported_by.email)
        if defect.assigned_to and defect.assigned_to.email:
            recipients.add(defect.assigned_to.email)

        if not recipients:
            return

        subject = f"[QualityGate] Defect {defect.defect_number} status: {defect.get_status_display()}"
        body = (
            f"Defect {defect.defect_number} - \"{defect.title}\"\n"
            f"Status changed: {old_status} -> {defect.get_status_display()}\n\n"
            f"Severity: {defect.get_severity_display()}\n"
            f"Assigned To: {defect.assigned_to.get_full_name() if defect.assigned_to else 'Unassigned'}\n\n"
            f"Regards,\nQualityGate System"
        )
        cls._send(subject, body, list(recipients))

    # ------------------------------------------------------------------
    #  Inspection notifications
    # ------------------------------------------------------------------
    @classmethod
    def notify_inspection_completed(cls, inspection):
        """Notify stakeholders when an inspection is completed."""
        recipients = set()
        if inspection.inspector and inspection.inspector.email:
            recipients.add(inspection.inspector.email)
        if inspection.reviewed_by and inspection.reviewed_by.email:
            recipients.add(inspection.reviewed_by.email)

        if not recipients:
            return

        pass_rate = inspection.pass_rate
        pass_rate_str = f"{pass_rate}%" if pass_rate is not None else "N/A"

        subject = (
            f"[QualityGate] Inspection {inspection.inspection_number} "
            f"completed - {inspection.get_disposition_display()}"
        )
        body = (
            f"Inspection {inspection.inspection_number} has been completed.\n\n"
            f"  Product: {inspection.product_name}\n"
            f"  Part: {inspection.part_number or 'N/A'}\n"
            f"  Disposition: {inspection.get_disposition_display()}\n"
            f"  Pass Rate: {pass_rate_str}\n"
            f"  Defects Found: {inspection.total_defects_found}\n"
            f"  Inspector: {inspection.inspector.get_full_name() if inspection.inspector else 'N/A'}\n\n"
            f"Regards,\nQualityGate System"
        )
        cls._send(subject, body, list(recipients))

    @classmethod
    def notify_inspection_rejected(cls, inspection):
        """Send urgent notification when an inspection results in rejection."""
        from apps.accounts.models import User

        # Notify quality managers
        managers = User.objects.filter(
            role__in=[User.Role.QUALITY_MANAGER, User.Role.ADMIN],
            is_active=True,
        ).values_list("email", flat=True)

        recipients = [e for e in managers if e]
        if not recipients:
            return

        subject = (
            f"[QualityGate] REJECTED: Inspection {inspection.inspection_number} "
            f"- {inspection.product_name}"
        )
        body = (
            f"An inspection has been REJECTED and requires immediate attention.\n\n"
            f"  Inspection: {inspection.inspection_number}\n"
            f"  Product: {inspection.product_name}\n"
            f"  Part: {inspection.part_number or 'N/A'}\n"
            f"  Batch: {inspection.batch_number or 'N/A'}\n"
            f"  Lot Size: {inspection.lot_size}\n"
            f"  Inspector: {inspection.inspector.get_full_name() if inspection.inspector else 'N/A'}\n"
            f"  Defects Found: {inspection.total_defects_found}\n\n"
            f"Please initiate containment and corrective action.\n\n"
            f"Regards,\nQualityGate System"
        )
        cls._send(subject, body, list(recipients))

    # ------------------------------------------------------------------
    #  Audit notifications
    # ------------------------------------------------------------------
    @classmethod
    def notify_audit_finding_created(cls, finding):
        """Notify auditee when a new finding is raised."""
        audit = finding.audit
        recipients = []
        if audit.auditee_contact:
            recipients.append(audit.auditee_contact)
        if audit.lead_auditor and audit.lead_auditor.email:
            recipients.append(audit.lead_auditor.email)

        if not recipients:
            return

        subject = (
            f"[QualityGate] Audit Finding {finding.finding_number} "
            f"- {finding.get_classification_display()}"
        )
        body = (
            f"A new audit finding has been raised:\n\n"
            f"  Audit: {audit.audit_number} - {audit.title}\n"
            f"  Finding: {finding.finding_number}\n"
            f"  Classification: {finding.get_classification_display()}\n"
            f"  Clause: {finding.clause_reference or 'N/A'}\n\n"
            f"Description:\n{finding.description}\n\n"
            f"Response Due Date: {finding.response_due_date or 'Not set'}\n\n"
            f"Regards,\nQualityGate System"
        )
        cls._send(subject, body, recipients)

    # ------------------------------------------------------------------
    #  Overdue digest
    # ------------------------------------------------------------------
    @classmethod
    def send_overdue_digest(cls, user, overdue_items):
        """
        Send a daily digest of overdue items to a user.

        Args:
            user: User instance with an email.
            overdue_items: dict with keys 'defects', 'capa_tasks', 'findings',
                           each mapping to a list of item dicts.
        """
        if not user.email:
            return

        total = sum(len(v) for v in overdue_items.values())
        if total == 0:
            return

        lines = [f"Hello {user.first_name or user.username},\n"]
        lines.append(f"You have {total} overdue quality item(s):\n")

        if overdue_items.get("defects"):
            lines.append("\nOverdue Defects:")
            for d in overdue_items["defects"]:
                lines.append(f"  - {d['number']}: {d['title']} (due {d['due_date']})")

        if overdue_items.get("capa_tasks"):
            lines.append("\nOverdue CAPA Tasks:")
            for t in overdue_items["capa_tasks"]:
                lines.append(f"  - {t['parent_number']} Task: {t['title']} (due {t['due_date']})")

        if overdue_items.get("findings"):
            lines.append("\nOverdue Audit Findings:")
            for f_item in overdue_items["findings"]:
                lines.append(f"  - {f_item['number']}: {f_item['classification']} (due {f_item['due_date']})")

        lines.append("\n\nPlease address these items as soon as possible.")
        lines.append("\nRegards,\nQualityGate System")

        subject = f"[QualityGate] Daily Overdue Digest - {total} Item(s)"
        cls._send(subject, "\n".join(lines), [user.email])

    # ------------------------------------------------------------------
    #  Internal helper
    # ------------------------------------------------------------------
    @classmethod
    def _send(cls, subject: str, body: str, recipients: list, html_body: Optional[str] = None):
        """
        Send an email, logging errors rather than raising.

        Args:
            subject: Email subject.
            body: Plain-text body.
            recipients: List of email addresses.
            html_body: Optional HTML body.
        """
        if not recipients:
            return

        try:
            if html_body:
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=body,
                    from_email=cls._get_from_email(),
                    to=recipients,
                )
                msg.attach_alternative(html_body, "text/html")
                msg.send(fail_silently=False)
            else:
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=cls._get_from_email(),
                    recipient_list=recipients,
                    fail_silently=False,
                )
            logger.info("Notification sent: '%s' to %s", subject, ", ".join(recipients))
        except Exception:
            logger.exception("Failed to send notification: '%s' to %s", subject, ", ".join(recipients))
