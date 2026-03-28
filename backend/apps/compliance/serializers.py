"""
Serializers for compliance app.
"""

from rest_framework import serializers

from apps.accounts.serializers import UserListSerializer

from .models import (
    ComplianceAssessment,
    ComplianceRequirement,
    DocumentControl,
    Standard,
)


class ComplianceAssessmentSerializer(serializers.ModelSerializer):
    """Serializer for compliance assessments."""

    assessed_by = UserListSerializer(read_only=True)
    reviewed_by = UserListSerializer(read_only=True)
    is_review_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = ComplianceAssessment
        fields = [
            "id", "requirement", "status", "assessment_date", "next_review_date",
            "evidence_description", "evidence_document",
            "gaps_identified", "action_plan", "completion_target",
            "assessed_by", "reviewed_by", "review_date",
            "notes", "is_review_overdue", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ComplianceAssessmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating assessments."""

    class Meta:
        model = ComplianceAssessment
        fields = [
            "id", "requirement", "status", "assessment_date", "next_review_date",
            "evidence_description", "evidence_document",
            "gaps_identified", "action_plan", "completion_target", "notes",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        validated_data["assessed_by"] = self.context["request"].user
        return super().create(validated_data)


class ComplianceRequirementSerializer(serializers.ModelSerializer):
    """Serializer for compliance requirements with latest assessment."""

    latest_assessment = ComplianceAssessmentSerializer(read_only=True)
    sub_requirements = serializers.SerializerMethodField()

    class Meta:
        model = ComplianceRequirement
        fields = [
            "id", "standard", "clause_number", "title", "description",
            "priority", "parent_clause", "is_applicable",
            "exclusion_justification", "responsible_department",
            "evidence_required", "latest_assessment",
            "sub_requirements", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_sub_requirements(self, obj):
        children = obj.sub_requirements.filter(is_applicable=True)
        return ComplianceRequirementSerializer(children, many=True).data


class ComplianceRequirementCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating requirements."""

    class Meta:
        model = ComplianceRequirement
        fields = [
            "id", "standard", "clause_number", "title", "description",
            "priority", "parent_clause", "is_applicable",
            "exclusion_justification", "responsible_department",
            "evidence_required",
        ]
        read_only_fields = ["id"]


class StandardListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for standard list views."""

    total_requirements = serializers.IntegerField(read_only=True)
    compliance_rate = serializers.FloatField(read_only=True)

    class Meta:
        model = Standard
        fields = [
            "id", "name", "code", "version", "category",
            "issuing_body", "is_active", "total_requirements",
            "compliance_rate", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class StandardDetailSerializer(serializers.ModelSerializer):
    """Full serializer for standard detail with requirements."""

    requirements = ComplianceRequirementSerializer(many=True, read_only=True)
    total_requirements = serializers.IntegerField(read_only=True)
    compliance_rate = serializers.FloatField(read_only=True)

    class Meta:
        model = Standard
        fields = [
            "id", "name", "code", "version", "category", "description",
            "issuing_body", "effective_date", "expiry_date", "document_url",
            "is_active", "requirements", "total_requirements",
            "compliance_rate", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StandardCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating standards."""

    class Meta:
        model = Standard
        fields = [
            "id", "name", "code", "version", "category", "description",
            "issuing_body", "effective_date", "expiry_date",
            "document_url", "is_active",
        ]
        read_only_fields = ["id"]


class DocumentControlListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for document list views."""

    author = UserListSerializer(read_only=True)
    is_review_due = serializers.BooleanField(read_only=True)

    class Meta:
        model = DocumentControl
        fields = [
            "id", "document_number", "title", "document_type", "status",
            "revision", "department", "author", "effective_date",
            "review_date", "is_review_due", "created_at",
        ]
        read_only_fields = ["id", "document_number", "created_at"]


class DocumentControlDetailSerializer(serializers.ModelSerializer):
    """Full serializer for document detail views."""

    author = UserListSerializer(read_only=True)
    approved_by = UserListSerializer(read_only=True)
    standard_detail = StandardListSerializer(source="standard", read_only=True)
    is_review_due = serializers.BooleanField(read_only=True)

    class Meta:
        model = DocumentControl
        fields = [
            "id", "document_number", "title", "document_type", "status",
            "revision", "description", "file", "file_size",
            "standard", "standard_detail", "department", "process_area",
            "supersedes", "author", "approved_by", "approved_date",
            "effective_date", "review_date", "retention_period_years",
            "is_review_due", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "document_number", "created_at", "updated_at"]


class DocumentControlCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating controlled documents."""

    class Meta:
        model = DocumentControl
        fields = [
            "id", "title", "document_type", "status", "revision",
            "description", "file", "standard", "department",
            "process_area", "supersedes", "effective_date",
            "review_date", "retention_period_years",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user
        return super().create(validated_data)
