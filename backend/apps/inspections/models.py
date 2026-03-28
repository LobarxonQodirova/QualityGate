"""
Inspection models: Inspection, InspectionChecklist, InspectionItem, InspectionResult.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class InspectionChecklist(models.Model):
    """
    Reusable inspection checklist template.
    A checklist defines a set of items to inspect for a given product or process.
    """

    class ChecklistType(models.TextChoices):
        INCOMING = "incoming", "Incoming Inspection"
        IN_PROCESS = "in_process", "In-Process Inspection"
        FINAL = "final", "Final Inspection"
        FIRST_ARTICLE = "first_article", "First Article Inspection (FAI)"
        RECEIVING = "receiving", "Receiving Inspection"
        PATROL = "patrol", "Patrol Inspection"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=300)
    code = models.CharField(max_length=50, unique=True, help_text="Checklist reference code (e.g., CL-2024-001)")
    checklist_type = models.CharField(max_length=20, choices=ChecklistType.choices)
    description = models.TextField(blank=True)
    product_line = models.CharField(max_length=200, blank=True)
    revision = models.CharField(max_length=20, default="1.0")
    applicable_standards = models.JSONField(
        default=list,
        blank=True,
        help_text="List of applicable standards (e.g., ['ISO 9001 Sec 8.6'])",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_checklists",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_checklists",
    )
    approved_date = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Inspection Checklist"
        verbose_name_plural = "Inspection Checklists"

    def __str__(self):
        return f"{self.code} - {self.name} (Rev {self.revision})"

    @property
    def item_count(self):
        return self.items.count()


class InspectionItem(models.Model):
    """
    A single item/characteristic within an inspection checklist.
    Defines what to measure, the specification limits, and measurement method.
    """

    class MeasurementType(models.TextChoices):
        PASS_FAIL = "pass_fail", "Pass / Fail"
        MEASUREMENT = "measurement", "Measurement (Numeric)"
        VISUAL = "visual", "Visual Inspection"
        ATTRIBUTE = "attribute", "Attribute Check"
        TEXT = "text", "Text / Notes"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    checklist = models.ForeignKey(
        InspectionChecklist,
        on_delete=models.CASCADE,
        related_name="items",
    )
    sequence = models.PositiveIntegerField(help_text="Order of this item in the checklist")
    characteristic = models.CharField(max_length=300, help_text="What is being inspected")
    description = models.TextField(blank=True, help_text="Detailed description or work instruction")
    measurement_type = models.CharField(max_length=20, choices=MeasurementType.choices)
    unit_of_measure = models.CharField(max_length=50, blank=True, help_text="e.g., mm, kg, psi")
    nominal_value = models.FloatField(blank=True, null=True, help_text="Target/nominal value")
    upper_spec_limit = models.FloatField(blank=True, null=True, help_text="USL")
    lower_spec_limit = models.FloatField(blank=True, null=True, help_text="LSL")
    tolerance = models.CharField(max_length=100, blank=True, help_text="Tolerance string (e.g., +/- 0.05)")
    measurement_tool = models.CharField(max_length=200, blank=True, help_text="Instrument to use")
    sample_size = models.PositiveIntegerField(default=1, help_text="Number of samples to inspect")
    is_critical = models.BooleanField(default=False, help_text="Critical-to-quality characteristic")
    reference_image = models.ImageField(upload_to="inspection_items/", blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["checklist", "sequence"]
        verbose_name = "Inspection Item"
        verbose_name_plural = "Inspection Items"
        unique_together = [("checklist", "sequence")]

    def __str__(self):
        return f"#{self.sequence}: {self.characteristic}"


class Inspection(models.Model):
    """
    An actual inspection event.
    Records who inspected what, when, and the overall outcome.
    """

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        ON_HOLD = "on_hold", "On Hold"
        CANCELLED = "cancelled", "Cancelled"

    class Disposition(models.TextChoices):
        ACCEPT = "accept", "Accept"
        REJECT = "reject", "Reject"
        CONDITIONAL = "conditional", "Conditional Accept"
        REWORK = "rework", "Rework Required"
        PENDING = "pending", "Pending Review"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inspection_number = models.CharField(
        max_length=50, unique=True,
        help_text="Auto-generated or manually entered inspection number",
    )
    checklist = models.ForeignKey(
        InspectionChecklist,
        on_delete=models.PROTECT,
        related_name="inspections",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    disposition = models.CharField(max_length=20, choices=Disposition.choices, default=Disposition.PENDING)

    # What is being inspected
    product_name = models.CharField(max_length=300)
    part_number = models.CharField(max_length=100, blank=True)
    batch_number = models.CharField(max_length=100, blank=True)
    lot_size = models.PositiveIntegerField(default=1)
    sample_size = models.PositiveIntegerField(default=1)
    work_order = models.CharField(max_length=100, blank=True)
    supplier = models.CharField(max_length=300, blank=True)

    # Who and when
    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inspections_performed",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inspections_reviewed",
    )
    scheduled_date = models.DateTimeField(blank=True, null=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    # Location
    production_line = models.CharField(max_length=200, blank=True)
    workstation = models.CharField(max_length=200, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Inspection"
        verbose_name_plural = "Inspections"

    def __str__(self):
        return f"{self.inspection_number} - {self.product_name}"

    def save(self, *args, **kwargs):
        if not self.inspection_number:
            prefix = "INS"
            year = timezone.now().strftime("%Y")
            last = Inspection.objects.filter(
                inspection_number__startswith=f"{prefix}-{year}"
            ).order_by("-inspection_number").first()
            if last:
                last_seq = int(last.inspection_number.split("-")[-1])
                seq = last_seq + 1
            else:
                seq = 1
            self.inspection_number = f"{prefix}-{year}-{seq:05d}"
        super().save(*args, **kwargs)

    @property
    def pass_rate(self):
        """Calculate percentage of items that passed."""
        results = self.results.all()
        total = results.count()
        if total == 0:
            return None
        passed = results.filter(is_conforming=True).count()
        return round((passed / total) * 100, 1)

    @property
    def total_defects_found(self):
        return self.results.filter(is_conforming=False).count()


class InspectionResult(models.Model):
    """
    Result for a single inspection item within an inspection.
    Records the actual measurement or observation.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inspection = models.ForeignKey(
        Inspection,
        on_delete=models.CASCADE,
        related_name="results",
    )
    inspection_item = models.ForeignKey(
        InspectionItem,
        on_delete=models.PROTECT,
        related_name="results",
    )
    measured_value = models.FloatField(blank=True, null=True, help_text="Actual measured value")
    text_value = models.TextField(blank=True, help_text="Text result for visual/attribute checks")
    is_conforming = models.BooleanField(default=True, help_text="Does the result meet specification?")
    deviation = models.FloatField(
        blank=True, null=True,
        help_text="Deviation from nominal value",
    )
    defect_description = models.TextField(blank=True, help_text="Description if non-conforming")
    photo = models.ImageField(upload_to="inspection_results/", blank=True, null=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="recorded_results",
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["inspection", "inspection_item__sequence"]
        verbose_name = "Inspection Result"
        verbose_name_plural = "Inspection Results"
        unique_together = [("inspection", "inspection_item")]

    def __str__(self):
        status_str = "PASS" if self.is_conforming else "FAIL"
        return f"{self.inspection_item.characteristic}: {status_str}"

    def save(self, *args, **kwargs):
        # Auto-determine conformance for measurement-type items
        item = self.inspection_item
        if (
            item.measurement_type == InspectionItem.MeasurementType.MEASUREMENT
            and self.measured_value is not None
        ):
            if item.nominal_value is not None:
                self.deviation = self.measured_value - item.nominal_value

            in_spec = True
            if item.upper_spec_limit is not None and self.measured_value > item.upper_spec_limit:
                in_spec = False
            if item.lower_spec_limit is not None and self.measured_value < item.lower_spec_limit:
                in_spec = False
            self.is_conforming = in_spec

        super().save(*args, **kwargs)
