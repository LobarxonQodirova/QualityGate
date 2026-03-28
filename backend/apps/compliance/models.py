"""
Compliance models: Standard, ComplianceRequirement, ComplianceAssessment,
DocumentControl.

Manages regulatory standards, compliance requirements tracking,
and controlled document management per ISO 9001 / QMS requirements.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Standard(models.Model):
    """
    A quality or regulatory standard (e.g., ISO 9001:2015, AS9100D, IATF 16949).
    """

    class Category(models.TextChoices):
        QMS = "qms", "Quality Management System"
        INDUSTRY = "industry", "Industry-Specific"
        REGULATORY = "regulatory", "Regulatory"
        CUSTOMER = "customer", "Customer-Specific"
        INTERNAL = "internal", "Internal Standard"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=300)
    code = models.CharField(max_length=50, unique=True, help_text="e.g., ISO-9001-2015")
    version = models.CharField(max_length=50, blank=True, help_text="e.g., 2015")
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.TextField(blank=True)
    issuing_body = models.CharField(max_length=200, blank=True, help_text="e.g., ISO, SAE, FAA")
    effective_date = models.DateField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    document_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "Standard"
        verbose_name_plural = "Standards"

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def total_requirements(self):
        return self.requirements.count()

    @property
    def compliance_rate(self):
        """Percentage of requirements assessed as compliant."""
        total = self.requirements.count()
        if total == 0:
            return None
        compliant = self.requirements.filter(
            assessments__status=ComplianceAssessment.Status.COMPLIANT,
        ).distinct().count()
        return round((compliant / total) * 100, 1)


class ComplianceRequirement(models.Model):
    """
    A specific requirement or clause within a standard.
    """

    class Priority(models.TextChoices):
        MANDATORY = "mandatory", "Mandatory (Shall)"
        RECOMMENDED = "recommended", "Recommended (Should)"
        OPTIONAL = "optional", "Optional (May)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    standard = models.ForeignKey(Standard, on_delete=models.CASCADE, related_name="requirements")
    clause_number = models.CharField(max_length=50, help_text="e.g., 8.5.1, 4.2.3")
    title = models.CharField(max_length=500)
    description = models.TextField(help_text="Full requirement text or summary")
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MANDATORY)
    parent_clause = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sub_requirements",
    )
    is_applicable = models.BooleanField(
        default=True,
        help_text="Whether this requirement applies to the organization",
    )
    exclusion_justification = models.TextField(
        blank=True,
        help_text="Justification if requirement is not applicable",
    )
    responsible_department = models.CharField(max_length=200, blank=True)
    evidence_required = models.TextField(
        blank=True,
        help_text="Description of evidence needed to demonstrate compliance",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["standard", "clause_number"]
        verbose_name = "Compliance Requirement"
        verbose_name_plural = "Compliance Requirements"
        unique_together = [("standard", "clause_number")]

    def __str__(self):
        return f"{self.standard.code} {self.clause_number}: {self.title}"

    @property
    def latest_assessment(self):
        return self.assessments.order_by("-assessment_date").first()


class ComplianceAssessment(models.Model):
    """
    Assessment of compliance against a specific requirement.
    Tracks the status and evidence for each requirement over time.
    """

    class Status(models.TextChoices):
        COMPLIANT = "compliant", "Compliant"
        PARTIALLY_COMPLIANT = "partially_compliant", "Partially Compliant"
        NON_COMPLIANT = "non_compliant", "Non-Compliant"
        NOT_ASSESSED = "not_assessed", "Not Yet Assessed"
        NOT_APPLICABLE = "not_applicable", "Not Applicable"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requirement = models.ForeignKey(
        ComplianceRequirement,
        on_delete=models.CASCADE,
        related_name="assessments",
    )
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.NOT_ASSESSED)
    assessment_date = models.DateField(default=timezone.now)
    next_review_date = models.DateField(blank=True, null=True)

    evidence_description = models.TextField(blank=True)
    evidence_document = models.FileField(upload_to="compliance_evidence/%Y/%m/", blank=True, null=True)
    gaps_identified = models.TextField(blank=True, help_text="Description of gaps if not fully compliant")
    action_plan = models.TextField(blank=True, help_text="Plan to address gaps")
    completion_target = models.DateField(blank=True, null=True)

    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="compliance_assessments",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_assessments",
    )
    review_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-assessment_date"]
        verbose_name = "Compliance Assessment"
        verbose_name_plural = "Compliance Assessments"

    def __str__(self):
        return f"{self.requirement} - {self.get_status_display()}"

    @property
    def is_review_overdue(self):
        if self.next_review_date:
            return timezone.now().date() > self.next_review_date
        return False


class DocumentControl(models.Model):
    """
    Controlled document management per ISO 9001 Clause 7.5.
    Tracks quality documents, their revisions, approvals, and distribution.
    """

    class DocumentType(models.TextChoices):
        POLICY = "policy", "Quality Policy"
        MANUAL = "manual", "Quality Manual"
        PROCEDURE = "procedure", "Standard Operating Procedure (SOP)"
        WORK_INSTRUCTION = "work_instruction", "Work Instruction"
        FORM = "form", "Form / Template"
        SPECIFICATION = "specification", "Specification"
        EXTERNAL = "external", "External Document"
        RECORD = "record", "Quality Record"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In Review"
        APPROVED = "approved", "Approved"
        EFFECTIVE = "effective", "Effective"
        SUPERSEDED = "superseded", "Superseded"
        OBSOLETE = "obsolete", "Obsolete"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=500)
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    revision = models.CharField(max_length=20, default="A")
    description = models.TextField(blank=True)

    # File
    file = models.FileField(upload_to="controlled_docs/%Y/%m/")
    file_size = models.PositiveIntegerField(blank=True, null=True, help_text="File size in bytes")

    # Relationships
    standard = models.ForeignKey(
        Standard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    department = models.CharField(max_length=200, blank=True)
    process_area = models.CharField(max_length=200, blank=True)
    supersedes = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="superseded_by",
    )

    # People
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="authored_documents",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_documents",
    )
    approved_date = models.DateTimeField(blank=True, null=True)

    # Dates
    effective_date = models.DateField(blank=True, null=True)
    review_date = models.DateField(blank=True, null=True, help_text="Next scheduled review date")
    retention_period_years = models.PositiveSmallIntegerField(
        default=7,
        help_text="Number of years to retain this document",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["document_number"]
        verbose_name = "Controlled Document"
        verbose_name_plural = "Controlled Documents"

    def __str__(self):
        return f"{self.document_number} Rev {self.revision} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.document_number:
            prefix = "DOC"
            year = timezone.now().strftime("%Y")
            last = (
                DocumentControl.objects.filter(
                    document_number__startswith=f"{prefix}-{year}"
                )
                .order_by("-document_number")
                .first()
            )
            if last:
                last_seq = int(last.document_number.split("-")[-1])
                seq = last_seq + 1
            else:
                seq = 1
            self.document_number = f"{prefix}-{year}-{seq:05d}"
        super().save(*args, **kwargs)

    @property
    def is_review_due(self):
        if self.review_date and self.status == self.Status.EFFECTIVE:
            return timezone.now().date() >= self.review_date
        return False
