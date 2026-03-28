"""
Admin configuration for audits app.
"""

from django.contrib import admin

from .models import Audit, AuditChecklistItem, AuditEvidence, AuditFinding


class AuditChecklistItemInline(admin.TabularInline):
    model = AuditChecklistItem
    extra = 1
    ordering = ["sequence"]


class AuditFindingInline(admin.TabularInline):
    model = AuditFinding
    extra = 0
    fields = [
        "finding_number", "classification", "status",
        "clause_reference", "description",
    ]
    readonly_fields = ["finding_number"]


class AuditEvidenceInline(admin.TabularInline):
    model = AuditEvidence
    extra = 0
    raw_id_fields = ["uploaded_by", "finding"]


@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin):
    list_display = [
        "audit_number", "title", "audit_type", "status", "result",
        "lead_auditor", "planned_start", "planned_end",
        "total_findings", "is_overdue",
    ]
    list_filter = ["audit_type", "status", "result"]
    search_fields = ["audit_number", "title", "standard", "department"]
    raw_id_fields = ["lead_auditor"]
    filter_horizontal = ["auditors"]
    inlines = [AuditChecklistItemInline, AuditFindingInline, AuditEvidenceInline]
    date_hierarchy = "planned_start"

    def total_findings(self, obj):
        return obj.total_findings

    def is_overdue(self, obj):
        return obj.is_overdue
    is_overdue.boolean = True


@admin.register(AuditFinding)
class AuditFindingAdmin(admin.ModelAdmin):
    list_display = [
        "finding_number", "audit", "classification", "status",
        "clause_reference", "response_due_date", "is_overdue",
    ]
    list_filter = ["classification", "status"]
    search_fields = ["finding_number", "description", "clause_reference"]
    raw_id_fields = ["audit", "checklist_item", "closed_by"]

    def is_overdue(self, obj):
        return obj.is_overdue
    is_overdue.boolean = True


@admin.register(AuditChecklistItem)
class AuditChecklistItemAdmin(admin.ModelAdmin):
    list_display = ["audit", "sequence", "clause_reference", "compliance_status"]
    list_filter = ["compliance_status"]
    raw_id_fields = ["audit"]


@admin.register(AuditEvidence)
class AuditEvidenceAdmin(admin.ModelAdmin):
    list_display = ["title", "audit", "finding", "evidence_type", "uploaded_by", "uploaded_at"]
    list_filter = ["evidence_type"]
    raw_id_fields = ["audit", "finding", "uploaded_by"]
