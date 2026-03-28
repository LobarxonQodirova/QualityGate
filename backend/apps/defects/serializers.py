"""
Serializers for defects app.
"""

from rest_framework import serializers

from apps.accounts.serializers import UserListSerializer

from .models import Defect, DefectCategory, DefectImage, RootCauseAnalysis


class DefectCategorySerializer(serializers.ModelSerializer):
    """Serializer for defect categories."""

    subcategories = serializers.SerializerMethodField()

    class Meta:
        model = DefectCategory
        fields = [
            "id", "name", "code", "description", "parent",
            "subcategories", "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_subcategories(self, obj):
        children = obj.subcategories.filter(is_active=True)
        return DefectCategorySerializer(children, many=True).data


class DefectImageSerializer(serializers.ModelSerializer):
    """Serializer for defect images."""

    uploaded_by = UserListSerializer(read_only=True)

    class Meta:
        model = DefectImage
        fields = ["id", "defect", "image", "caption", "uploaded_by", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]

    def create(self, validated_data):
        validated_data["uploaded_by"] = self.context["request"].user
        return super().create(validated_data)


class RootCauseAnalysisSerializer(serializers.ModelSerializer):
    """Serializer for root cause analysis."""

    analyzed_by = UserListSerializer(read_only=True)
    verified_by = UserListSerializer(read_only=True)

    class Meta:
        model = RootCauseAnalysis
        fields = [
            "id", "defect", "methodology", "why_1", "why_2", "why_3",
            "why_4", "why_5", "cause_category", "root_cause",
            "contributing_factors", "evidence", "analyzed_by",
            "verified_by", "analysis_date", "verified_date",
            "is_verified", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class RootCauseAnalysisCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating RCA."""

    class Meta:
        model = RootCauseAnalysis
        fields = [
            "id", "defect", "methodology", "why_1", "why_2", "why_3",
            "why_4", "why_5", "cause_category", "root_cause",
            "contributing_factors", "evidence",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        validated_data["analyzed_by"] = self.context["request"].user
        return super().create(validated_data)


class DefectListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for defect list views."""

    category_name = serializers.CharField(source="category.name", read_only=True, default="")
    reported_by = UserListSerializer(read_only=True)
    assigned_to = UserListSerializer(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_open = serializers.IntegerField(read_only=True)

    class Meta:
        model = Defect
        fields = [
            "id", "defect_number", "title", "category", "category_name",
            "severity", "status", "detection_method", "product_name",
            "part_number", "batch_number", "quantity_affected",
            "reported_by", "assigned_to", "detected_date",
            "target_close_date", "is_overdue", "days_open",
            "estimated_cost", "created_at",
        ]
        read_only_fields = ["id", "defect_number", "created_at"]


class DefectDetailSerializer(serializers.ModelSerializer):
    """Full serializer for defect detail views."""

    category = DefectCategorySerializer(read_only=True)
    reported_by = UserListSerializer(read_only=True)
    assigned_to = UserListSerializer(read_only=True)
    closed_by = UserListSerializer(read_only=True)
    images = DefectImageSerializer(many=True, read_only=True)
    root_cause_analysis = RootCauseAnalysisSerializer(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_open = serializers.IntegerField(read_only=True)
    defect_rate = serializers.FloatField(read_only=True)

    class Meta:
        model = Defect
        fields = [
            "id", "defect_number", "title", "description", "category",
            "severity", "status", "detection_method",
            "product_name", "part_number", "batch_number", "serial_number",
            "quantity_affected", "quantity_inspected",
            "production_line", "workstation", "operation",
            "reported_by", "assigned_to", "inspection",
            "containment_action", "containment_date",
            "estimated_cost", "actual_cost",
            "detected_date", "target_close_date", "closed_date", "closed_by",
            "notes", "images", "root_cause_analysis",
            "is_overdue", "days_open", "defect_rate",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "defect_number", "created_at", "updated_at"]


class DefectCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating defects."""

    class Meta:
        model = Defect
        fields = [
            "id", "title", "description", "category", "severity",
            "status", "detection_method",
            "product_name", "part_number", "batch_number", "serial_number",
            "quantity_affected", "quantity_inspected",
            "production_line", "workstation", "operation",
            "assigned_to", "inspection",
            "containment_action", "containment_date",
            "estimated_cost", "actual_cost",
            "detected_date", "target_close_date", "notes",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        validated_data["reported_by"] = self.context["request"].user
        return super().create(validated_data)
