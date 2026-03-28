"""
Admin configuration for accounts app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Inspector, QualityTeam, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "email", "first_name", "last_name", "role",
        "department", "employee_id", "is_active",
    ]
    list_filter = ["role", "department", "is_active", "is_certified_inspector"]
    search_fields = ["email", "first_name", "last_name", "employee_id"]
    ordering = ["last_name", "first_name"]

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Quality Info", {
            "fields": (
                "role", "employee_id", "department", "phone",
                "avatar", "is_certified_inspector", "certification_expiry",
            ),
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Quality Info", {
            "fields": ("email", "first_name", "last_name", "role", "employee_id", "department"),
        }),
    )


@admin.register(Inspector)
class InspectorAdmin(admin.ModelAdmin):
    list_display = [
        "user", "certification_level", "certification_number",
        "certification_expiry", "total_inspections", "is_active",
    ]
    list_filter = ["certification_level", "is_active"]
    search_fields = ["user__first_name", "user__last_name", "certification_number"]
    raw_id_fields = ["user"]


@admin.register(QualityTeam)
class QualityTeamAdmin(admin.ModelAdmin):
    list_display = ["name", "leader", "production_area", "member_count", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "production_area"]
    raw_id_fields = ["leader"]
    filter_horizontal = ["members"]
