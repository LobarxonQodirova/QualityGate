"""
Views for metrics app.
"""

from datetime import timedelta

from django.db.models import Avg, Count, Max, Min, Q, Sum
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.defects.models import Defect
from apps.inspections.models import Inspection, InspectionResult

from .models import MetricDataPoint, QualityKPI, SPCControlChart, SPCDataPoint
from .serializers import (
    MetricDataPointSerializer,
    QualityKPICreateSerializer,
    QualityKPIDetailSerializer,
    QualityKPIListSerializer,
    SPCControlChartCreateSerializer,
    SPCControlChartDetailSerializer,
    SPCControlChartListSerializer,
    SPCDataPointSerializer,
)


class QualityKPIViewSet(viewsets.ModelViewSet):
    """CRUD for Quality KPIs with dashboard-friendly endpoints."""

    queryset = QualityKPI.objects.select_related("owner").prefetch_related("data_points").all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name", "code", "description"]
    filterset_fields = ["category", "unit", "is_active"]
    ordering_fields = ["name", "code", "category", "created_at"]
    ordering = ["category", "name"]
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return QualityKPICreateSerializer
        if self.action == "list":
            return QualityKPIListSerializer
        return QualityKPIDetailSerializer

    @action(detail=False, methods=["get"], url_path="dashboard")
    def dashboard(self, request):
        """
        Return a summary of all active KPIs suitable for a management dashboard.
        Groups KPIs by category with their current status.
        """
        kpis = QualityKPI.objects.filter(is_active=True).select_related("owner")
        dashboard_data = {}

        for kpi in kpis:
            category = kpi.get_category_display()
            if category not in dashboard_data:
                dashboard_data[category] = []
            dashboard_data[category].append({
                "id": str(kpi.id),
                "code": kpi.code,
                "name": kpi.name,
                "target": float(kpi.target_value),
                "current": float(kpi.latest_value) if kpi.latest_value is not None else None,
                "unit": kpi.get_unit_display(),
                "status": kpi.status_color,
                "trend_direction": kpi.trend_direction,
            })

        return Response(dashboard_data)

    @action(detail=True, methods=["get"], url_path="trend")
    def trend(self, request, pk=None):
        """
        Return time-series data for charting a KPI trend.
        Accepts optional ?months=12 query parameter.
        """
        kpi = self.get_object()
        months = int(request.query_params.get("months", 12))
        cutoff = timezone.now().date() - timedelta(days=months * 30)

        data_points = kpi.data_points.filter(period_end__gte=cutoff).order_by("period_end")
        serializer = MetricDataPointSerializer(data_points, many=True)

        return Response({
            "kpi_code": kpi.code,
            "kpi_name": kpi.name,
            "target": float(kpi.target_value),
            "warning_threshold": float(kpi.warning_threshold) if kpi.warning_threshold else None,
            "critical_threshold": float(kpi.critical_threshold) if kpi.critical_threshold else None,
            "trend_direction": kpi.trend_direction,
            "data_points": serializer.data,
        })

    @action(detail=False, methods=["get"], url_path="auto-calculate")
    def auto_calculate(self, request):
        """
        Auto-calculate common quality metrics from inspection and defect data.
        Returns calculated values that can then be saved as data points.
        """
        today = timezone.now().date()
        period_start = today.replace(day=1)  # first of current month

        # First Pass Yield: inspections accepted on first attempt
        total_inspections = Inspection.objects.filter(
            completed_at__date__gte=period_start,
            status=Inspection.Status.COMPLETED,
        ).count()
        accepted = Inspection.objects.filter(
            completed_at__date__gte=period_start,
            status=Inspection.Status.COMPLETED,
            disposition=Inspection.Disposition.ACCEPT,
        ).count()
        fpy = (accepted / total_inspections * 100) if total_inspections > 0 else None

        # Defect Rate (DPMO approximation)
        defects_this_period = Defect.objects.filter(
            detected_date__date__gte=period_start,
        ).count()
        total_inspected = Inspection.objects.filter(
            completed_at__date__gte=period_start,
            status=Inspection.Status.COMPLETED,
        ).aggregate(total=Sum("sample_size"))["total"] or 0
        dpmo = (defects_this_period / total_inspected * 1_000_000) if total_inspected > 0 else None

        # Average Days to Close Defects
        closed_defects = Defect.objects.filter(
            closed_date__date__gte=period_start,
            status=Defect.Status.CLOSED,
        )
        avg_days_to_close = None
        if closed_defects.exists():
            total_days = sum(d.days_open for d in closed_defects)
            avg_days_to_close = round(total_days / closed_defects.count(), 1)

        return Response({
            "period_start": period_start.isoformat(),
            "period_end": today.isoformat(),
            "first_pass_yield": fpy,
            "total_inspections": total_inspections,
            "defect_count": defects_this_period,
            "dpmo": dpmo,
            "total_units_inspected": total_inspected,
            "avg_days_to_close_defect": avg_days_to_close,
        })


class MetricDataPointViewSet(viewsets.ModelViewSet):
    """CRUD for metric data points."""

    queryset = MetricDataPoint.objects.select_related("kpi", "recorded_by").all()
    serializer_class = MetricDataPointSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["kpi", "frequency"]
    ordering_fields = ["period_end", "created_at"]
    ordering = ["-period_end"]
    permission_classes = [IsAuthenticated]


class SPCControlChartViewSet(viewsets.ModelViewSet):
    """CRUD for SPC control charts."""

    queryset = SPCControlChart.objects.select_related("created_by").prefetch_related(
        "data_points"
    ).all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name", "characteristic", "process_name", "part_number"]
    filterset_fields = ["chart_type", "is_active"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return SPCControlChartCreateSerializer
        if self.action == "list":
            return SPCControlChartListSerializer
        return SPCControlChartDetailSerializer

    @action(detail=True, methods=["get"], url_path="analysis")
    def analysis(self, request, pk=None):
        """
        Perform basic SPC analysis on the chart data.
        Returns control limit violations and process capability indicators.
        """
        chart = self.get_object()
        data_points = chart.data_points.order_by("subgroup_number")

        if not data_points.exists():
            return Response({"message": "No data points available for analysis."})

        values = list(data_points.values_list("value", flat=True))
        n = len(values)
        mean_val = sum(values) / n
        variance = sum((x - mean_val) ** 2 for x in values) / n
        std_dev = variance ** 0.5

        out_of_control = [
            {"subgroup": dp.subgroup_number, "value": dp.value}
            for dp in data_points
            if not dp.is_in_control
        ]

        # Process capability
        cp = None
        cpk = None
        if chart.upper_spec_limit and chart.lower_spec_limit and std_dev > 0:
            cp = (chart.upper_spec_limit - chart.lower_spec_limit) / (6 * std_dev)
            cpu = (chart.upper_spec_limit - mean_val) / (3 * std_dev)
            cpl = (mean_val - chart.lower_spec_limit) / (3 * std_dev)
            cpk = min(cpu, cpl)

        return Response({
            "chart_id": str(chart.id),
            "chart_name": chart.name,
            "total_points": n,
            "mean": round(mean_val, 4),
            "std_dev": round(std_dev, 4),
            "ucl": chart.upper_control_limit,
            "cl": chart.center_line,
            "lcl": chart.lower_control_limit,
            "out_of_control_points": out_of_control,
            "out_of_control_percentage": round(len(out_of_control) / n * 100, 2) if n > 0 else 0,
            "cp": round(cp, 3) if cp else None,
            "cpk": round(cpk, 3) if cpk else None,
        })


class SPCDataPointViewSet(viewsets.ModelViewSet):
    """CRUD for SPC data points."""

    queryset = SPCDataPoint.objects.select_related("chart", "recorded_by").all()
    serializer_class = SPCDataPointSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["chart"]
    ordering_fields = ["subgroup_number", "recorded_at"]
    ordering = ["subgroup_number"]
    permission_classes = [IsAuthenticated]
