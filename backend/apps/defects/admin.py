"""
Admin configuration for defects app.
"""

from django.contrib import admin

from .models import Defect, DefectCategory, DefectImage, RootCauseAnalysis


@admin.register(DefectCategory)
class DefectCategoryAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "parent", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "code"]


class DefectImageInline(admin.TabularInline):
    model = DefectImage
    extra = 0
    raw_id_fields = ["uploaded_by"]


class RootCauseAnalysisInline(admin.StackedInline):
    model = RootCauseAnalysis
    extra = 0
    raw_id_fields = ["analyzed_by", "verified_by"]


@admin.register(Defect)
class DefectAdmin(admin.ModelAdmin):
    list_display = [
        "defect_number", "title", "severity", "status",
        "product_name", "assigned_to", "detected_date",
        "target_close_date", "is_overdue",
    ]
    list_filter = ["severity", "status", "detection_method", "category"]
    search_fields = ["defect_number", "title", "product_name", "part_number"]
    raw_id_fields = ["reported_by", "assigned_to", "closed_by", "inspection", "category"]
    inlines = [DefectImageInline, RootCauseAnalysisInline]
    date_hierarchy = "detected_date"

    def is_overdue(self, obj):
        return obj.is_overdue
    is_overdue.boolean = True


@admin.register(DefectImage)
class DefectImageAdmin(admin.ModelAdmin):
    list_display = ["defect", "caption", "uploaded_by", "uploaded_at"]
    raw_id_fields = ["defect", "uploaded_by"]


@admin.register(RootCauseAnalysis)
class RootCauseAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        "defect", "methodology", "cause_category",
        "analyzed_by", "is_verified",
    ]
    list_filter = ["methodology", "cause_category", "is_verified"]
    raw_id_fields = ["defect", "analyzed_by", "verified_by"]
