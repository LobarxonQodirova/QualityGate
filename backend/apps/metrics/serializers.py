"""
Serializers for metrics app.
"""

from rest_framework import serializers

from apps.accounts.serializers import UserListSerializer

from .models import MetricDataPoint, QualityKPI, SPCControlChart, SPCDataPoint


class MetricDataPointSerializer(serializers.ModelSerializer):
    """Serializer for KPI data points."""

    recorded_by = UserListSerializer(read_only=True)
    meets_target = serializers.BooleanField(read_only=True)

    class Meta:
        model = MetricDataPoint
        fields = [
            "id", "kpi", "value", "frequency", "period_start", "period_end",
            "sample_size", "notes", "recorded_by", "meets_target", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        validated_data["recorded_by"] = self.context["request"].user
        return super().create(validated_data)


class QualityKPIListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for KPI list views."""

    latest_value = serializers.DecimalField(max_digits=14, decimal_places=4, read_only=True)
    status_color = serializers.CharField(read_only=True)
    owner = UserListSerializer(read_only=True)

    class Meta:
        model = QualityKPI
        fields = [
            "id", "name", "code", "category", "unit", "trend_direction",
            "target_value", "warning_threshold", "critical_threshold",
            "latest_value", "status_color", "owner", "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class QualityKPIDetailSerializer(serializers.ModelSerializer):
    """Full serializer for KPI detail with historical data points."""

    owner = UserListSerializer(read_only=True)
    data_points = MetricDataPointSerializer(many=True, read_only=True)
    latest_value = serializers.DecimalField(max_digits=14, decimal_places=4, read_only=True)
    status_color = serializers.CharField(read_only=True)

    class Meta:
        model = QualityKPI
        fields = [
            "id", "name", "code", "description", "category", "unit",
            "trend_direction", "target_value", "warning_threshold",
            "critical_threshold", "formula", "data_source",
            "owner", "is_active", "data_points", "latest_value",
            "status_color", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class QualityKPICreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating KPIs."""

    class Meta:
        model = QualityKPI
        fields = [
            "id", "name", "code", "description", "category", "unit",
            "trend_direction", "target_value", "warning_threshold",
            "critical_threshold", "formula", "data_source",
            "owner", "is_active",
        ]
        read_only_fields = ["id"]


class SPCDataPointSerializer(serializers.ModelSerializer):
    """Serializer for SPC chart data points."""

    recorded_by = UserListSerializer(read_only=True)
    is_in_control = serializers.BooleanField(read_only=True)

    class Meta:
        model = SPCDataPoint
        fields = [
            "id", "chart", "subgroup_number", "value", "range_value",
            "std_dev", "recorded_at", "recorded_by", "notes", "is_in_control",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        validated_data["recorded_by"] = self.context["request"].user
        return super().create(validated_data)


class SPCControlChartListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for SPC chart list views."""

    total_data_points = serializers.IntegerField(read_only=True)
    out_of_control_count = serializers.IntegerField(read_only=True)
    created_by = UserListSerializer(read_only=True)

    class Meta:
        model = SPCControlChart
        fields = [
            "id", "name", "chart_type", "characteristic", "process_name",
            "part_number", "upper_control_limit", "center_line",
            "lower_control_limit", "subgroup_size", "is_active",
            "total_data_points", "out_of_control_count",
            "created_by", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SPCControlChartDetailSerializer(serializers.ModelSerializer):
    """Full serializer for SPC chart with data points."""

    created_by = UserListSerializer(read_only=True)
    data_points = SPCDataPointSerializer(many=True, read_only=True)
    total_data_points = serializers.IntegerField(read_only=True)
    out_of_control_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = SPCControlChart
        fields = [
            "id", "name", "chart_type", "characteristic", "process_name",
            "part_number", "upper_control_limit", "center_line",
            "lower_control_limit", "upper_spec_limit", "lower_spec_limit",
            "subgroup_size", "is_active", "data_points",
            "total_data_points", "out_of_control_count",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SPCControlChartCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating SPC charts."""

    class Meta:
        model = SPCControlChart
        fields = [
            "id", "name", "chart_type", "characteristic", "process_name",
            "part_number", "upper_control_limit", "center_line",
            "lower_control_limit", "upper_spec_limit", "lower_spec_limit",
            "subgroup_size", "is_active",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)
