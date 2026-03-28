"""
Serializers for audits app.
"""

from rest_framework import serializers

from apps.accounts.serializers import UserListSerializer

from .models import Audit, AuditChecklistItem, AuditEvidence, AuditFinding


class AuditChecklistItemSerializer(serializers.ModelSerializer):
    """Serializer for audit checklist items."""

    class Meta:
        model = AuditChecklistItem
        fields = [
            "id", "audit", "sequence", "clause_reference", "question",
            "compliance_status", "evidence_notes", "auditor_comments",
        ]
        read_only_fields = ["id"]


class AuditEvidenceSerializer(serializers.ModelSerializer):
    """Serializer for audit evidence files."""

    uploaded_by = UserListSerializer(read_only=True)

    class Meta:
        model = AuditEvidence
        fields = [
            "id", "audit", "finding", "evidence_type", "title",
            "description", "file", "uploaded_by", "uploaded_at",
        ]
        read_only_fields = ["id", "uploaded_at"]

    def create(self, validated_data):
        validated_data["uploaded_by"] = self.context["request"].user
        return super().create(validated_data)


class AuditFindingListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for finding list views."""

    is_overdue = serializers.BooleanField(read_only=True)
    days_open = serializers.IntegerField(read_only=True)

    class Meta:
        model = AuditFinding
        fields = [
            "id", "finding_number", "audit", "classification", "status",
            "clause_reference", "description", "response_due_date",
            "is_overdue", "days_open", "created_at",
        ]
        read_only_fields = ["id", "finding_number", "created_at"]


class AuditFindingDetailSerializer(serializers.ModelSerializer):
    """Full serializer for finding detail views."""

    closed_by = UserListSerializer(read_only=True)
    evidence_files = AuditEvidenceSerializer(many=True, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_open = serializers.IntegerField(read_only=True)

    class Meta:
        model = AuditFinding
        fields = [
            "id", "audit", "finding_number", "classification", "status",
            "clause_reference", "description", "objective_evidence",
            "requirement", "checklist_item",
            "auditee_response", "proposed_corrective_action",
            "response_due_date", "response_date",
            "closed_by", "closed_date", "closure_notes",
            "evidence_files", "is_overdue", "days_open",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "finding_number", "created_at", "updated_at"]


class AuditFindingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating findings."""

    class Meta:
        model = AuditFinding
        fields = [
            "id", "audit", "classification", "clause_reference",
            "description", "objective_evidence", "requirement",
            "checklist_item", "response_due_date",
        ]
        read_only_fields = ["id"]


class AuditListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for audit list views."""

    lead_auditor = UserListSerializer(read_only=True)
    total_findings = serializers.IntegerField(read_only=True)
    major_findings_count = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Audit
        fields = [
            "id", "audit_number", "title", "audit_type", "status",
            "result", "standard", "department", "lead_auditor",
            "planned_start", "planned_end", "total_findings",
            "major_findings_count", "is_overdue", "created_at",
        ]
        read_only_fields = ["id", "audit_number", "created_at"]


class AuditDetailSerializer(serializers.ModelSerializer):
    """Full serializer for audit detail views."""

    lead_auditor = UserListSerializer(read_only=True)
    auditors = UserListSerializer(many=True, read_only=True)
    findings = AuditFindingListSerializer(many=True, read_only=True)
    checklist_items = AuditChecklistItemSerializer(many=True, read_only=True)
    evidence_files = AuditEvidenceSerializer(many=True, read_only=True)
    total_findings = serializers.IntegerField(read_only=True)
    major_findings_count = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Audit
        fields = [
            "id", "audit_number", "title", "audit_type", "status", "result",
            "scope", "standard", "department", "process_area", "supplier_name",
            "lead_auditor", "auditors", "auditee_contact",
            "planned_start", "planned_end", "actual_start", "actual_end",
            "executive_summary", "strengths", "opportunities_for_improvement",
            "findings", "checklist_items", "evidence_files",
            "total_findings", "major_findings_count", "is_overdue",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "audit_number", "created_at", "updated_at"]


class AuditCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating audits."""

    auditor_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = Audit
        fields = [
            "id", "title", "audit_type", "scope", "standard",
            "department", "process_area", "supplier_name",
            "lead_auditor", "auditor_ids", "auditee_contact",
            "planned_start", "planned_end",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        auditor_ids = validated_data.pop("auditor_ids", [])
        audit = Audit.objects.create(**validated_data)
        if auditor_ids:
            from apps.accounts.models import User
            audit.auditors.set(User.objects.filter(id__in=auditor_ids))
        return audit

    def update(self, instance, validated_data):
        auditor_ids = validated_data.pop("auditor_ids", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if auditor_ids is not None:
            from apps.accounts.models import User
            instance.auditors.set(User.objects.filter(id__in=auditor_ids))
        return instance
