"""
Audit models: Audit, AuditFinding, AuditChecklistItem, AuditEvidence.

Supports internal audits, supplier audits, and regulatory audits aligned
with ISO 9001, AS9100, IATF 16949 and similar QMS standards.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Audit(models.Model):
    """
    An audit event.  Covers internal quality audits, supplier audits,
    and external / regulatory audits.
    """

    class AuditType(models.TextChoices):
        INTERNAL = "internal", "Internal Audit"
        SUPPLIER = "supplier", "Supplier Audit"
        CUSTOMER = "customer", "Customer Audit"
        REGULATORY = "regulatory", "Regulatory / Certification Audit"
        PROCESS = "process", "Process Audit"
        PRODUCT = "product", "Product Audit"

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        FOLLOW_UP = "follow_up", "Follow-Up Required"

    class Result(models.TextChoices):
        PASS = "pass", "Pass"
        CONDITIONAL = "conditional", "Conditional Pass"
        FAIL = "fail", "Fail"
        PENDING = "pending", "Pending Review"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    audit_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=500)
    audit_type = models.CharField(max_length=20, choices=AuditType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    result = models.CharField(max_length=20, choices=Result.choices, default=Result.PENDING)

    # Scope
    scope = models.TextField(help_text="Audit scope and objectives")
    standard = models.CharField(
        max_length=200,
        blank=True,
        help_text="Applicable standard (e.g., ISO 9001:2015 Clause 8)",
    )
    department = models.CharField(max_length=200, blank=True)
    process_area = models.CharField(max_length=200, blank=True)
    supplier_name = models.CharField(max_length=300, blank=True)

    # People
    lead_auditor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="led_audits",
    )
    auditors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="audits_participated",
    )
    auditee_contact = models.CharField(max_length=300, blank=True)

    # Schedule
    planned_start = models.DateField()
    planned_end = models.DateField()
    actual_start = models.DateField(blank=True, null=True)
    actual_end = models.DateField(blank=True, null=True)

    # Summary
    executive_summary = models.TextField(blank=True)
    strengths = models.TextField(blank=True)
    opportunities_for_improvement = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-planned_start"]
        verbose_name = "Audit"
        verbose_name_plural = "Audits"

    def __str__(self):
        return f"{self.audit_number} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.audit_number:
            prefix = "AUD"
            year = timezone.now().strftime("%Y")
            last = (
                Audit.objects.filter(audit_number__startswith=f"{prefix}-{year}")
                .order_by("-audit_number")
                .first()
            )
            if last:
                last_seq = int(last.audit_number.split("-")[-1])
                seq = last_seq + 1
            else:
                seq = 1
            self.audit_number = f"{prefix}-{year}-{seq:05d}"
        super().save(*args, **kwargs)

    @property
    def total_findings(self):
        return self.findings.count()

    @property
    def major_findings_count(self):
        return self.findings.filter(classification=AuditFinding.Classification.MAJOR_NC).count()

    @property
    def is_overdue(self):
        if self.status not in (self.Status.COMPLETED, self.Status.CANCELLED):
            return timezone.now().date() > self.planned_end
        return False


class AuditChecklistItem(models.Model):
    """Individual audit question or verification point within an audit."""

    class ComplianceStatus(models.TextChoices):
        CONFORMING = "conforming", "Conforming"
        NON_CONFORMING = "non_conforming", "Non-Conforming"
        OBSERVATION = "observation", "Observation"
        NOT_APPLICABLE = "not_applicable", "Not Applicable"
        NOT_VERIFIED = "not_verified", "Not Yet Verified"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name="checklist_items")
    sequence = models.PositiveIntegerField()
    clause_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Standard clause reference (e.g., 8.5.1)",
    )
    question = models.TextField(help_text="Audit question or verification point")
    compliance_status = models.CharField(
        max_length=20,
        choices=ComplianceStatus.choices,
        default=ComplianceStatus.NOT_VERIFIED,
    )
    evidence_notes = models.TextField(blank=True, help_text="Objective evidence observed")
    auditor_comments = models.TextField(blank=True)

    class Meta:
        ordering = ["audit", "sequence"]
        verbose_name = "Audit Checklist Item"
        verbose_name_plural = "Audit Checklist Items"
        unique_together = [("audit", "sequence")]

    def __str__(self):
        return f"#{self.sequence}: {self.question[:80]}"


class AuditFinding(models.Model):
    """
    A finding raised during an audit.
    Findings can be major/minor nonconformities, observations, or OFIs.
    """

    class Classification(models.TextChoices):
        MAJOR_NC = "major_nc", "Major Nonconformity"
        MINOR_NC = "minor_nc", "Minor Nonconformity"
        OBSERVATION = "observation", "Observation"
        OFI = "ofi", "Opportunity for Improvement"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESPONSE_SUBMITTED = "response_submitted", "Response Submitted"
        CORRECTIVE_ACTION = "corrective_action", "Corrective Action In Progress"
        VERIFIED_CLOSED = "verified_closed", "Verified & Closed"
        OVERDUE = "overdue", "Overdue"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name="findings")
    finding_number = models.CharField(max_length=50, unique=True)
    classification = models.CharField(max_length=20, choices=Classification.choices)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.OPEN)

    clause_reference = models.CharField(max_length=100, blank=True)
    description = models.TextField(help_text="Detailed description of the finding")
    objective_evidence = models.TextField(
        blank=True,
        help_text="Objective evidence supporting the finding",
    )
    requirement = models.TextField(
        blank=True,
        help_text="The requirement that is not met",
    )
    checklist_item = models.ForeignKey(
        AuditChecklistItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="findings",
    )

    # Response
    auditee_response = models.TextField(blank=True)
    proposed_corrective_action = models.TextField(blank=True)
    response_due_date = models.DateField(blank=True, null=True)
    response_date = models.DateField(blank=True, null=True)

    # Closure
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_findings",
    )
    closed_date = models.DateTimeField(blank=True, null=True)
    closure_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-classification", "-created_at"]
        verbose_name = "Audit Finding"
        verbose_name_plural = "Audit Findings"

    def __str__(self):
        return f"{self.finding_number} - {self.get_classification_display()}"

    def save(self, *args, **kwargs):
        if not self.finding_number:
            prefix = "FND"
            year = timezone.now().strftime("%Y")
            last = (
                AuditFinding.objects.filter(finding_number__startswith=f"{prefix}-{year}")
                .order_by("-finding_number")
                .first()
            )
            if last:
                last_seq = int(last.finding_number.split("-")[-1])
                seq = last_seq + 1
            else:
                seq = 1
            self.finding_number = f"{prefix}-{year}-{seq:05d}"
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        if self.response_due_date and self.status == self.Status.OPEN:
            return timezone.now().date() > self.response_due_date
        return False

    @property
    def days_open(self):
        end = self.closed_date or timezone.now()
        return (end - self.created_at).days


class AuditEvidence(models.Model):
    """Documentary evidence attached to an audit or finding."""

    class EvidenceType(models.TextChoices):
        DOCUMENT = "document", "Document"
        PHOTO = "photo", "Photo"
        RECORD = "record", "Quality Record"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    audit = models.ForeignKey(Audit, on_delete=models.CASCADE, related_name="evidence_files")
    finding = models.ForeignKey(
        AuditFinding,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="evidence_files",
    )
    evidence_type = models.CharField(max_length=20, choices=EvidenceType.choices)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to="audit_evidence/%Y/%m/")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]
        verbose_name = "Audit Evidence"
        verbose_name_plural = "Audit Evidence Files"

    def __str__(self):
        return f"{self.title} ({self.get_evidence_type_display()})"
