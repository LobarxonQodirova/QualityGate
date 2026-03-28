"""
Serializers for inspections app.
"""

from rest_framework import serializers

from apps.accounts.serializers import UserListSerializer

from .models import Inspection, InspectionChecklist, InspectionItem, InspectionResult


class InspectionItemSerializer(serializers.ModelSerializer):
    """Serializer for inspection checklist items."""

    class Meta:
        model = InspectionItem
        fields = [
            "id", "checklist", "sequence", "characteristic", "description",
            "measurement_type", "unit_of_measure", "nominal_value",
            "upper_spec_limit", "lower_spec_limit", "tolerance",
            "measurement_tool", "sample_size", "is_critical",
            "reference_image", "is_active",
        ]
        read_only_fields = ["id"]


class InspectionChecklistListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for checklist list views."""

    created_by = UserListSerializer(read_only=True)
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = InspectionChecklist
        fields = [
            "id", "name", "code", "checklist_type", "product_line",
            "revision", "item_count", "created_by", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class InspectionChecklistDetailSerializer(serializers.ModelSerializer):
    """Full serializer for checklist detail with items."""

    created_by = UserListSerializer(read_only=True)
    approved_by = UserListSerializer(read_only=True)
    items = InspectionItemSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = InspectionChecklist
        fields = [
            "id", "name", "code", "checklist_type", "description",
            "product_line", "revision", "applicable_standards",
            "created_by", "approved_by", "approved_date",
            "items", "item_count", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class InspectionChecklistCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating checklists with nested items."""

    items = InspectionItemSerializer(many=True, required=False)

    class Meta:
        model = InspectionChecklist
        fields = [
            "id", "name", "code", "checklist_type", "description",
            "product_line", "revision", "applicable_standards",
            "items", "is_active",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        validated_data["created_by"] = self.context["request"].user
        checklist = InspectionChecklist.objects.create(**validated_data)
        for item_data in items_data:
            item_data.pop("checklist", None)
            InspectionItem.objects.create(checklist=checklist, **item_data)
        return checklist


class InspectionResultSerializer(serializers.ModelSerializer):
    """Serializer for individual inspection results."""

    recorded_by = UserListSerializer(read_only=True)

    class Meta:
        model = InspectionResult
        fields = [
            "id", "inspection", "inspection_item", "measured_value",
            "text_value", "is_conforming", "deviation",
            "defect_description", "photo", "recorded_by", "recorded_at",
        ]
        read_only_fields = ["id", "deviation", "recorded_at"]


class InspectionResultCreateSerializer(serializers.ModelSerializer):
    """Serializer for recording inspection results."""

    class Meta:
        model = InspectionResult
        fields = [
            "id", "inspection", "inspection_item", "measured_value",
            "text_value", "is_conforming", "defect_description", "photo",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        validated_data["recorded_by"] = self.context["request"].user
        return super().create(validated_data)


class BulkInspectionResultSerializer(serializers.Serializer):
    """Serializer for submitting multiple results at once."""

    results = InspectionResultCreateSerializer(many=True)

    def create(self, validated_data):
        results_data = validated_data["results"]
        user = self.context["request"].user
        created = []
        for result_data in results_data:
            result_data["recorded_by"] = user
            created.append(InspectionResult.objects.create(**result_data))
        return created


class InspectionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for inspection list views."""

    inspector = UserListSerializer(read_only=True)
    checklist_name = serializers.CharField(source="checklist.name", read_only=True)
    pass_rate = serializers.FloatField(read_only=True)
    total_defects_found = serializers.IntegerField(read_only=True)

    class Meta:
        model = Inspection
        fields = [
            "id", "inspection_number", "checklist", "checklist_name",
            "status", "disposition", "product_name", "part_number",
            "batch_number", "lot_size", "sample_size", "inspector",
            "scheduled_date", "completed_at", "pass_rate",
            "total_defects_found", "created_at",
        ]
        read_only_fields = ["id", "inspection_number", "created_at"]


class InspectionDetailSerializer(serializers.ModelSerializer):
    """Full inspection serializer with results."""

    inspector = UserListSerializer(read_only=True)
    reviewed_by = UserListSerializer(read_only=True)
    checklist = InspectionChecklistListSerializer(read_only=True)
    results = InspectionResultSerializer(many=True, read_only=True)
    pass_rate = serializers.FloatField(read_only=True)
    total_defects_found = serializers.IntegerField(read_only=True)

    class Meta:
        model = Inspection
        fields = [
            "id", "inspection_number", "checklist", "status", "disposition",
            "product_name", "part_number", "batch_number", "lot_size",
            "sample_size", "work_order", "supplier", "inspector",
            "reviewed_by", "scheduled_date", "started_at", "completed_at",
            "production_line", "workstation", "notes", "results",
            "pass_rate", "total_defects_found", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "inspection_number", "created_at", "updated_at"]


class InspectionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating inspections."""

    class Meta:
        model = Inspection
        fields = [
            "id", "checklist", "product_name", "part_number",
            "batch_number", "lot_size", "sample_size", "work_order",
            "supplier", "inspector", "scheduled_date",
            "production_line", "workstation", "notes",
        ]
        read_only_fields = ["id"]
