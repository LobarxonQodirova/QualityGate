"""
Defect models: Defect, DefectCategory, DefectImage, RootCauseAnalysis.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class DefectCategory(models.Model):
    """Category/classification for defects (e.g., Dimensional, Surface, Functional)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subcategories",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Defect Category"
        verbose_name_plural = "Defect Categories"

    def __str__(self):
        return f"{self.code} - {self.name}"


class Defect(models.Model):
    """
    A quality defect/nonconformance record.
    Tracks the defect lifecycle from detection through resolution.
    """

    class Severity(models.TextChoices):
        CRITICAL = "critical", "Critical"
        MAJOR = "major", "Major"
        MINOR = "minor", "Minor"
        COSMETIC = "cosmetic", "Cosmetic"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        UNDER_REVIEW = "under_review", "Under Review"
        CONTAINMENT = "containment", "Containment Action"
        ROOT_CAUSE = "root_cause", "Root Cause Analysis"
        CORRECTIVE_ACTION = "corrective_action", "Corrective Action"
        VERIFICATION = "verification", "Verification"
        CLOSED = "closed", "Closed"
        REJECTED = "rejected", "Rejected (Not a Defect)"

    class DetectionMethod(models.TextChoices):
        INSPECTION = "inspection", "Inspection"
        TESTING = "testing", "Testing"
        CUSTOMER_COMPLAINT = "customer_complaint", "Customer Complaint"
        AUDIT = "audit", "Audit Finding"
        OPERATOR = "operator", "Operator Detected"
        AUTOMATED = "automated", "Automated Detection"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    defect_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=500)
    description = models.TextField()
    category = models.ForeignKey(
        DefectCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="defects",
    )
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.MINOR)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    detection_method = models.CharField(
        max_length=20,
        choices=DetectionMethod.choices,
        default=DetectionMethod.INSPECTION,
    )

    # Product information
    product_name = models.CharField(max_length=300)
    part_number = models.CharField(max_length=100, blank=True)
    batch_number = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    quantity_affected = models.PositiveIntegerField(default=1)
    quantity_inspected = models.PositiveIntegerField(default=1)

    # Location
    production_line = models.CharField(max_length=200, blank=True)
    workstation = models.CharField(max_length=200, blank=True)
    operation = models.CharField(max_length=200, blank=True, help_text="Operation/process step where defect occurred")

    # People
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="reported_defects",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_defects",
    )

    # Related inspection
    inspection = models.ForeignKey(
        "inspections.Inspection",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="defects",
    )

    # Containment
    containment_action = models.TextField(blank=True, help_text="Immediate containment action taken")
    containment_date = models.DateTimeField(blank=True, null=True)

    # Cost
    estimated_cost = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True,
        help_text="Estimated cost of the defect (scrap, rework, etc.)",
    )
    actual_cost = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    # Dates
    detected_date = models.DateTimeField(default=timezone.now)
    target_close_date = models.DateField(blank=True, null=True)
    closed_date = models.DateTimeField(blank=True, null=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_defects",
    )

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Defect"
        verbose_name_plural = "Defects"

    def __str__(self):
        return f"{self.defect_number} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.defect_number:
            prefix = "DEF"
            year = timezone.now().strftime("%Y")
            last = Defect.objects.filter(
                defect_number__startswith=f"{prefix}-{year}"
            ).order_by("-defect_number").first()
            if last:
                last_seq = int(last.defect_number.split("-")[-1])
                seq = last_seq + 1
            else:
                seq = 1
            self.defect_number = f"{prefix}-{year}-{seq:05d}"
        super().save(*args, **kwargs)

    @property
    def defect_rate(self):
        if self.quantity_inspected == 0:
            return 0
        return round((self.quantity_affected / self.quantity_inspected) * 100, 2)

    @property
    def is_overdue(self):
        if self.target_close_date and self.status != self.Status.CLOSED:
            return timezone.now().date() > self.target_close_date
        return False

    @property
    def days_open(self):
        end = self.closed_date or timezone.now()
        return (end - self.detected_date).days


class DefectImage(models.Model):
    """Photographic evidence attached to a defect."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    defect = models.ForeignKey(Defect, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="defect_images/%Y/%m/")
    caption = models.CharField(max_length=300, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]
        verbose_name = "Defect Image"
        verbose_name_plural = "Defect Images"

    def __str__(self):
        return f"Image for {self.defect.defect_number}: {self.caption or 'No caption'}"


class RootCauseAnalysis(models.Model):
    """
    Root cause analysis for a defect.
    Supports 5-Why, Fishbone (Ishikawa), and other methodologies.
    """

    class Methodology(models.TextChoices):
        FIVE_WHY = "five_why", "5-Why Analysis"
        FISHBONE = "fishbone", "Fishbone (Ishikawa) Diagram"
        FAULT_TREE = "fault_tree", "Fault Tree Analysis"
        PARETO = "pareto", "Pareto Analysis"
        EIGHT_D = "eight_d", "8D Problem Solving"
        OTHER = "other", "Other"

    class CauseCategory(models.TextChoices):
        MAN = "man", "Man (People)"
        MACHINE = "machine", "Machine (Equipment)"
        METHOD = "method", "Method (Process)"
        MATERIAL = "material", "Material"
        MEASUREMENT = "measurement", "Measurement"
        ENVIRONMENT = "environment", "Mother Nature (Environment)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    defect = models.OneToOneField(Defect, on_delete=models.CASCADE, related_name="root_cause_analysis")
    methodology = models.CharField(max_length=20, choices=Methodology.choices, default=Methodology.FIVE_WHY)

    # 5-Why fields
    why_1 = models.TextField(blank=True, help_text="First Why")
    why_2 = models.TextField(blank=True, help_text="Second Why")
    why_3 = models.TextField(blank=True, help_text="Third Why")
    why_4 = models.TextField(blank=True, help_text="Fourth Why")
    why_5 = models.TextField(blank=True, help_text="Fifth Why")

    # Fishbone / general fields
    cause_category = models.CharField(
        max_length=20,
        choices=CauseCategory.choices,
        blank=True,
    )
    root_cause = models.TextField(help_text="Identified root cause")
    contributing_factors = models.JSONField(
        default=list,
        blank=True,
        help_text="List of contributing factors grouped by category",
    )
    evidence = models.TextField(blank=True, help_text="Evidence supporting the root cause determination")

    analyzed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="root_cause_analyses",
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_analyses",
    )
    analysis_date = models.DateTimeField(default=timezone.now)
    verified_date = models.DateTimeField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Root Cause Analysis"
        verbose_name_plural = "Root Cause Analyses"

    def __str__(self):
        return f"RCA for {self.defect.defect_number}: {self.root_cause[:80]}"
