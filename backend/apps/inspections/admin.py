"""
Admin configuration for inspections app.
"""

from django.contrib import admin

from .models import Inspection, InspectionChecklist, InspectionItem, InspectionResult


class InspectionItemInline(admin.TabularInline):
    model = InspectionItem
    extra = 1
    ordering = ["sequence"]


@admin.register(InspectionChecklist)
class InspectionChecklistAdmin(admin.ModelAdmin):
    list_display = [
        "code", "name", "checklist_type", "product_line",
        "revision", "item_count", "is_active", "created_at",
    ]
    list_filter = ["checklist_type", "is_active"]
    search_fields = ["code", "name", "product_line"]
    inlines = [InspectionItemInline]
    raw_id_fields = ["created_by", "approved_by"]


class InspectionResultInline(admin.TabularInline):
    model = InspectionResult
    extra = 0
    raw_id_fields = ["inspection_item", "recorded_by"]


@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    list_display = [
        "inspection_number", "product_name", "status", "disposition",
        "inspector", "scheduled_date", "completed_at",
    ]
    list_filter = ["status", "disposition", "checklist__checklist_type"]
    search_fields = ["inspection_number", "product_name", "part_number", "batch_number"]
    raw_id_fields = ["checklist", "inspector", "reviewed_by"]
    inlines = [InspectionResultInline]
    date_hierarchy = "created_at"


@admin.register(InspectionItem)
class InspectionItemAdmin(admin.ModelAdmin):
    list_display = [
        "characteristic", "checklist", "sequence",
        "measurement_type", "is_critical", "is_active",
    ]
    list_filter = ["measurement_type", "is_critical", "is_active"]
    search_fields = ["characteristic"]
    raw_id_fields = ["checklist"]


@admin.register(InspectionResult)
class InspectionResultAdmin(admin.ModelAdmin):
    list_display = [
        "inspection", "inspection_item", "measured_value",
        "is_conforming", "recorded_by", "recorded_at",
    ]
    list_filter = ["is_conforming"]
    raw_id_fields = ["inspection", "inspection_item", "recorded_by"]
