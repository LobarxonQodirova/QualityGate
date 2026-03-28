"""
Quality Metrics models: QualityMetric, MetricDataPoint, QualityKPI, SPCControlChart.

Provides structured storage for quality KPIs, trend data, and SPC
(Statistical Process Control) charting data.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class QualityKPI(models.Model):
    """
    Definition of a Quality Key Performance Indicator.
    Each KPI has a target, thresholds, and tracks actual values over time.
    """

    class Category(models.TextChoices):
        PROCESS = "process", "Process Performance"
        PRODUCT = "product", "Product Quality"
        DELIVERY = "delivery", "Delivery Performance"
        CUSTOMER = "customer", "Customer Satisfaction"
        COST = "cost", "Cost of Quality"
        COMPLIANCE = "compliance", "Compliance"
        CAPA = "capa", "CAPA Effectiveness"

    class Unit(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage (%)"
        PPM = "ppm", "Parts Per Million"
        COUNT = "count", "Count"
        HOURS = "hours", "Hours"
        DAYS = "days", "Days"
        CURRENCY = "currency", "Currency"
        SCORE = "score", "Score (1-10)"

    class TrendDirection(models.TextChoices):
        HIGHER_IS_BETTER = "higher", "Higher is Better"
        LOWER_IS_BETTER = "lower", "Lower is Better"
        TARGET_IS_BEST = "target", "Closest to Target is Best"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=300, unique=True)
    code = models.CharField(max_length=30, unique=True, help_text="Short code (e.g., FPY, DPMO, OTD)")
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    unit = models.CharField(max_length=20, choices=Unit.choices)
    trend_direction = models.CharField(
        max_length=10,
        choices=TrendDirection.choices,
        default=TrendDirection.HIGHER_IS_BETTER,
    )

    target_value = models.DecimalField(max_digits=12, decimal_places=4)
    warning_threshold = models.DecimalField(
        max_digits=12, decimal_places=4,
        blank=True, null=True,
        help_text="Value that triggers a warning (yellow status)",
    )
    critical_threshold = models.DecimalField(
        max_digits=12, decimal_places=4,
        blank=True, null=True,
        help_text="Value that triggers critical alert (red status)",
    )

    formula = models.TextField(
        blank=True,
        help_text="Calculation formula or description of how this KPI is measured",
    )
    data_source = models.CharField(
        max_length=200, blank=True,
        help_text="Where the raw data comes from (e.g., inspections, defects)",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_kpis",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "name"]
        verbose_name = "Quality KPI"
        verbose_name_plural = "Quality KPIs"

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def latest_value(self):
        """Get the most recent data point value."""
        dp = self.data_points.order_by("-period_end").first()
        return dp.value if dp else None

    @property
    def status_color(self):
        """Return 'green', 'yellow', or 'red' based on latest value."""
        val = self.latest_value
        if val is None:
            return "gray"
        if self.trend_direction == self.TrendDirection.HIGHER_IS_BETTER:
            if val >= self.target_value:
                return "green"
            if self.warning_threshold and val >= self.warning_threshold:
                return "yellow"
            return "red"
        elif self.trend_direction == self.TrendDirection.LOWER_IS_BETTER:
            if val <= self.target_value:
                return "green"
            if self.warning_threshold and val <= self.warning_threshold:
                return "yellow"
            return "red"
        else:
            deviation = abs(val - self.target_value)
            if self.critical_threshold and deviation >= self.critical_threshold:
                return "red"
            if self.warning_threshold and deviation >= self.warning_threshold:
                return "yellow"
            return "green"


class MetricDataPoint(models.Model):
    """
    A single data point for a quality KPI.
    Records the measured value for a specific time period.
    """

    class Frequency(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        YEARLY = "yearly", "Yearly"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kpi = models.ForeignKey(QualityKPI, on_delete=models.CASCADE, related_name="data_points")
    value = models.DecimalField(max_digits=14, decimal_places=4)
    frequency = models.CharField(max_length=15, choices=Frequency.choices, default=Frequency.MONTHLY)
    period_start = models.DateField(help_text="Start of the measurement period")
    period_end = models.DateField(help_text="End of the measurement period")
    sample_size = models.PositiveIntegerField(
        blank=True, null=True,
        help_text="Number of samples in this measurement period",
    )
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="recorded_data_points",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-period_end"]
        verbose_name = "Metric Data Point"
        verbose_name_plural = "Metric Data Points"
        unique_together = [("kpi", "period_start", "period_end")]

    def __str__(self):
        return f"{self.kpi.code}: {self.value} ({self.period_start} to {self.period_end})"

    @property
    def meets_target(self):
        kpi = self.kpi
        if kpi.trend_direction == QualityKPI.TrendDirection.HIGHER_IS_BETTER:
            return self.value >= kpi.target_value
        elif kpi.trend_direction == QualityKPI.TrendDirection.LOWER_IS_BETTER:
            return self.value <= kpi.target_value
        else:
            return abs(self.value - kpi.target_value) <= (kpi.warning_threshold or Decimal("0"))


class SPCControlChart(models.Model):
    """
    SPC (Statistical Process Control) chart configuration.
    Stores the control limits and configuration for X-bar, R-chart, etc.
    """

    class ChartType(models.TextChoices):
        XBAR_R = "xbar_r", "X-bar & R Chart"
        XBAR_S = "xbar_s", "X-bar & S Chart"
        INDIVIDUALS = "individuals", "Individuals & Moving Range (I-MR)"
        P_CHART = "p_chart", "p Chart (Proportion Defective)"
        NP_CHART = "np_chart", "np Chart (Count Defective)"
        C_CHART = "c_chart", "c Chart (Defects per Unit)"
        U_CHART = "u_chart", "u Chart (Defects per Opportunity)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=300)
    chart_type = models.CharField(max_length=20, choices=ChartType.choices)
    characteristic = models.CharField(
        max_length=300,
        help_text="Quality characteristic being monitored",
    )
    process_name = models.CharField(max_length=300, blank=True)
    part_number = models.CharField(max_length=100, blank=True)

    # Control limits
    upper_control_limit = models.FloatField(help_text="UCL")
    center_line = models.FloatField(help_text="CL (process mean)")
    lower_control_limit = models.FloatField(help_text="LCL")

    # Specification limits (optional)
    upper_spec_limit = models.FloatField(blank=True, null=True, help_text="USL")
    lower_spec_limit = models.FloatField(blank=True, null=True, help_text="LSL")

    # Config
    subgroup_size = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_spc_charts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "SPC Control Chart"
        verbose_name_plural = "SPC Control Charts"

    def __str__(self):
        return f"{self.name} ({self.get_chart_type_display()})"

    @property
    def total_data_points(self):
        return self.data_points.count()

    @property
    def out_of_control_count(self):
        """Count data points outside control limits."""
        return self.data_points.filter(
            models.Q(value__gt=self.upper_control_limit)
            | models.Q(value__lt=self.lower_control_limit)
        ).count()


class SPCDataPoint(models.Model):
    """Individual measurement data point for an SPC control chart."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chart = models.ForeignKey(SPCControlChart, on_delete=models.CASCADE, related_name="data_points")
    subgroup_number = models.PositiveIntegerField()
    value = models.FloatField(help_text="Measured value (or subgroup mean)")
    range_value = models.FloatField(blank=True, null=True, help_text="Range or moving range")
    std_dev = models.FloatField(blank=True, null=True, help_text="Subgroup standard deviation")
    recorded_at = models.DateTimeField(default=timezone.now)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["chart", "subgroup_number"]
        verbose_name = "SPC Data Point"
        verbose_name_plural = "SPC Data Points"
        unique_together = [("chart", "subgroup_number")]

    def __str__(self):
        return f"#{self.subgroup_number}: {self.value}"

    @property
    def is_in_control(self):
        return self.chart.lower_control_limit <= self.value <= self.chart.upper_control_limit
