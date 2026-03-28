"""
CAPA models: CorrectiveAction, PreventiveAction, CAPATask.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class CorrectiveAction(models.Model):
    """
    Corrective Action record.
    Addresses the root cause of an existing nonconformance to prevent recurrence.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        PENDING_VERIFICATION = "pending_verification", "Pending Verification"
        VERIFIED_EFFECTIVE = "verified_effective", "Verified - Effective"
        VERIFIED_INEFFECTIVE = "verified_ineffective", "Verified - Ineffective"
        CLOSED = "closed", "Closed"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    class Source(models.TextChoices):
        DEFECT = "defect", "Defect/NCR"
        AUDIT = "audit", "Audit Finding"
        CUSTOMER_COMPLAINT = "customer_complaint", "Customer Complaint"
        MANAGEMENT_REVIEW = "management_review", "Management Review"
        INTERNAL = "internal", "Internal Observation"
        REGULATORY = "regulatory", "Regulatory Requirement"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ca_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=500)
    description = models.TextField()
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.DEFECT)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.DRAFT)

    # Related items
    defect = models.ForeignKey(
        "defects.Defect",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="corrective_actions",
    )
    audit_finding = models.ForeignKey(
        "audits.AuditFinding",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="corrective_actions",
    )

    # Root cause
    root_cause = models.TextField(blank=True)
    immediate_containment = models.TextField(blank=True)

    # Action details
    action_plan = models.TextField(help_text="Detailed plan of corrective action steps")
    expected_outcome = models.TextField(blank=True)

    # People
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="initiated_cas",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_cas",
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_cas",
    )

    # Dates
    initiated_date = models.DateTimeField(default=timezone.now)
    target_date = models.DateField()
    completed_date = models.DateTimeField(blank=True, null=True)
    verification_date = models.DateTimeField(blank=True, null=True)

    # Verification
    verification_method = models.TextField(blank=True)
    verification_results = models.TextField(blank=True)
    effectiveness_rating = models.PositiveSmallIntegerField(
        blank=True, null=True,
        help_text="Effectiveness rating 1-5 (5=fully effective)",
    )

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Corrective Action"
        verbose_name_plural = "Corrective Actions"

    def __str__(self):
        return f"{self.ca_number} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.ca_number:
            prefix = "CA"
            year = timezone.now().strftime("%Y")
            last = CorrectiveAction.objects.filter(
                ca_number__startswith=f"{prefix}-{year}"
            ).order_by("-ca_number").first()
            if last:
                last_seq = int(last.ca_number.split("-")[-1])
                seq = last_seq + 1
            else:
                seq = 1
            self.ca_number = f"{prefix}-{year}-{seq:05d}"
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        if self.status not in (self.Status.CLOSED, self.Status.CANCELLED, self.Status.VERIFIED_EFFECTIVE):
            return timezone.now().date() > self.target_date
        return False

    @property
    def days_until_due(self):
        return (self.target_date - timezone.now().date()).days

    @property
    def task_completion_rate(self):
        total = self.tasks.count()
        if total == 0:
            return None
        completed = self.tasks.filter(status=CAPATask.Status.COMPLETED).count()
        return round((completed / total) * 100, 1)


class PreventiveAction(models.Model):
    """
    Preventive Action record.
    Proactive measures to eliminate potential causes of nonconformances.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        PENDING_VERIFICATION = "pending_verification", "Pending Verification"
        VERIFIED_EFFECTIVE = "verified_effective", "Verified - Effective"
        CLOSED = "closed", "Closed"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pa_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=500)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.DRAFT)

    # Analysis
    potential_risk = models.TextField(help_text="Description of the potential nonconformance or risk")
    risk_assessment = models.TextField(blank=True)
    action_plan = models.TextField(help_text="Detailed plan of preventive action steps")
    expected_outcome = models.TextField(blank=True)

    # People
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="initiated_pas",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_pas",
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_pas",
    )

    # Dates
    initiated_date = models.DateTimeField(default=timezone.now)
    target_date = models.DateField()
    completed_date = models.DateTimeField(blank=True, null=True)
    verification_date = models.DateTimeField(blank=True, null=True)

    # Verification
    verification_method = models.TextField(blank=True)
    verification_results = models.TextField(blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Preventive Action"
        verbose_name_plural = "Preventive Actions"

    def __str__(self):
        return f"{self.pa_number} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.pa_number:
            prefix = "PA"
            year = timezone.now().strftime("%Y")
            last = PreventiveAction.objects.filter(
                pa_number__startswith=f"{prefix}-{year}"
            ).order_by("-pa_number").first()
            if last:
                last_seq = int(last.pa_number.split("-")[-1])
                seq = last_seq + 1
            else:
                seq = 1
            self.pa_number = f"{prefix}-{year}-{seq:05d}"
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        if self.status not in (self.Status.CLOSED, self.Status.CANCELLED, self.Status.VERIFIED_EFFECTIVE):
            return timezone.now().date() > self.target_date
        return False


class CAPATask(models.Model):
    """
    Individual task within a CAPA (corrective or preventive action).
    Breaks down the action plan into trackable tasks.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        BLOCKED = "blocked", "Blocked"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    corrective_action = models.ForeignKey(
        CorrectiveAction,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="tasks",
    )
    preventive_action = models.ForeignKey(
        PreventiveAction,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="tasks",
    )
    sequence = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="capa_tasks",
    )
    due_date = models.DateField()
    completed_date = models.DateTimeField(blank=True, null=True)
    completion_notes = models.TextField(blank=True)
    evidence = models.FileField(upload_to="capa_evidence/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sequence"]
        verbose_name = "CAPA Task"
        verbose_name_plural = "CAPA Tasks"

    def __str__(self):
        parent = self.corrective_action or self.preventive_action
        parent_num = parent.ca_number if self.corrective_action else parent.pa_number
        return f"{parent_num} Task #{self.sequence}: {self.title}"

    @property
    def is_overdue(self):
        if self.status not in (self.Status.COMPLETED, self.Status.CANCELLED):
            return timezone.now().date() > self.due_date
        return False
