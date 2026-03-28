"""
Serializers for CAPA app.
"""

from rest_framework import serializers

from apps.accounts.serializers import UserListSerializer

from .models import CAPATask, CorrectiveAction, PreventiveAction


class CAPATaskSerializer(serializers.ModelSerializer):
    """Serializer for CAPA tasks."""

    assigned_to_detail = UserListSerializer(source="assigned_to", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = CAPATask
        fields = [
            "id", "corrective_action", "preventive_action", "sequence",
            "title", "description", "status", "assigned_to",
            "assigned_to_detail", "due_date", "completed_date",
            "completion_notes", "evidence", "is_overdue",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        ca = attrs.get("corrective_action")
        pa = attrs.get("preventive_action")
        if not ca and not pa:
            raise serializers.ValidationError(
                "A task must be linked to either a corrective or preventive action."
            )
        if ca and pa:
            raise serializers.ValidationError(
                "A task cannot be linked to both a corrective and preventive action."
            )
        return attrs


class CorrectiveActionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for corrective action list views."""

    initiated_by = UserListSerializer(read_only=True)
    assigned_to = UserListSerializer(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    task_completion_rate = serializers.FloatField(read_only=True)
    days_until_due = serializers.IntegerField(read_only=True)

    class Meta:
        model = CorrectiveAction
        fields = [
            "id", "ca_number", "title", "source", "priority", "status",
            "initiated_by", "assigned_to", "initiated_date", "target_date",
            "is_overdue", "task_completion_rate", "days_until_due",
            "created_at",
        ]
        read_only_fields = ["id", "ca_number", "created_at"]


class CorrectiveActionDetailSerializer(serializers.ModelSerializer):
    """Full serializer for corrective action detail views."""

    initiated_by = UserListSerializer(read_only=True)
    assigned_to_detail = UserListSerializer(source="assigned_to", read_only=True)
    verified_by_detail = UserListSerializer(source="verified_by", read_only=True)
    tasks = CAPATaskSerializer(many=True, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    task_completion_rate = serializers.FloatField(read_only=True)
    days_until_due = serializers.IntegerField(read_only=True)

    class Meta:
        model = CorrectiveAction
        fields = [
            "id", "ca_number", "title", "description", "source",
            "priority", "status", "defect", "audit_finding",
            "root_cause", "immediate_containment",
            "action_plan", "expected_outcome",
            "initiated_by", "assigned_to", "assigned_to_detail",
            "verified_by", "verified_by_detail",
            "initiated_date", "target_date", "completed_date",
            "verification_date", "verification_method",
            "verification_results", "effectiveness_rating",
            "notes", "tasks", "is_overdue", "task_completion_rate",
            "days_until_due", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "ca_number", "created_at", "updated_at"]


class CorrectiveActionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating corrective actions."""

    tasks = CAPATaskSerializer(many=True, required=False)

    class Meta:
        model = CorrectiveAction
        fields = [
            "id", "title", "description", "source", "priority",
            "status", "defect", "audit_finding",
            "root_cause", "immediate_containment",
            "action_plan", "expected_outcome",
            "assigned_to", "target_date", "notes", "tasks",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        tasks_data = validated_data.pop("tasks", [])
        validated_data["initiated_by"] = self.context["request"].user
        ca = CorrectiveAction.objects.create(**validated_data)
        for i, task_data in enumerate(tasks_data, start=1):
            task_data.pop("corrective_action", None)
            task_data.pop("preventive_action", None)
            CAPATask.objects.create(
                corrective_action=ca,
                sequence=task_data.pop("sequence", i),
                **task_data,
            )
        return ca


class PreventiveActionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for preventive action list views."""

    initiated_by = UserListSerializer(read_only=True)
    assigned_to = UserListSerializer(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = PreventiveAction
        fields = [
            "id", "pa_number", "title", "priority", "status",
            "initiated_by", "assigned_to", "initiated_date",
            "target_date", "is_overdue", "created_at",
        ]
        read_only_fields = ["id", "pa_number", "created_at"]


class PreventiveActionDetailSerializer(serializers.ModelSerializer):
    """Full serializer for preventive action detail views."""

    initiated_by = UserListSerializer(read_only=True)
    assigned_to_detail = UserListSerializer(source="assigned_to", read_only=True)
    verified_by_detail = UserListSerializer(source="verified_by", read_only=True)
    tasks = CAPATaskSerializer(many=True, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = PreventiveAction
        fields = [
            "id", "pa_number", "title", "description", "priority",
            "status", "potential_risk", "risk_assessment",
            "action_plan", "expected_outcome",
            "initiated_by", "assigned_to", "assigned_to_detail",
            "verified_by", "verified_by_detail",
            "initiated_date", "target_date", "completed_date",
            "verification_date", "verification_method",
            "verification_results", "notes", "tasks",
            "is_overdue", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "pa_number", "created_at", "updated_at"]


class PreventiveActionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating preventive actions."""

    tasks = CAPATaskSerializer(many=True, required=False)

    class Meta:
        model = PreventiveAction
        fields = [
            "id", "title", "description", "priority", "status",
            "potential_risk", "risk_assessment",
            "action_plan", "expected_outcome",
            "assigned_to", "target_date", "notes", "tasks",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        tasks_data = validated_data.pop("tasks", [])
        validated_data["initiated_by"] = self.context["request"].user
        pa = PreventiveAction.objects.create(**validated_data)
        for i, task_data in enumerate(tasks_data, start=1):
            task_data.pop("corrective_action", None)
            task_data.pop("preventive_action", None)
            CAPATask.objects.create(
                preventive_action=pa,
                sequence=task_data.pop("sequence", i),
                **task_data,
            )
        return pa
