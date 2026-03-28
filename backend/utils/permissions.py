"""
Reusable permission classes for QualityGate API.

Provides role-based access control aligned with quality management
organizational roles defined in the accounts app.
"""

from rest_framework import permissions

from apps.accounts.models import User


class IsAdminUser(permissions.BasePermission):
    """Allow access only to admin users."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == User.Role.ADMIN
        )


class IsQualityManager(permissions.BasePermission):
    """Allow access to quality managers and admins."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in (User.Role.ADMIN, User.Role.QUALITY_MANAGER)
        )


class IsQualityStaff(permissions.BasePermission):
    """Allow access to any quality staff member (manager, engineer, inspector, auditor)."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.is_quality_staff
        )


class IsInspector(permissions.BasePermission):
    """Allow access to users with inspector role or certified inspector status."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return (
            request.user.role == User.Role.INSPECTOR
            or request.user.is_certified_inspector
        )


class IsAuditor(permissions.BasePermission):
    """Allow access to auditors, quality managers, and admins."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in (
                User.Role.ADMIN,
                User.Role.QUALITY_MANAGER,
                User.Role.AUDITOR,
            )
        )


class ReadOnlyOrQualityStaff(permissions.BasePermission):
    """
    Allow read-only access to all authenticated users.
    Write operations require quality staff role.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_quality_staff


class IsOwnerOrQualityManager(permissions.BasePermission):
    """
    Object-level permission: allow owners to edit their own items,
    and quality managers / admins to edit anything.
    """

    owner_field = "reported_by"  # Override in view if different

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.role in (User.Role.ADMIN, User.Role.QUALITY_MANAGER):
            return True

        owner_field = getattr(view, "owner_field", self.owner_field)
        owner = getattr(obj, owner_field, None)
        return owner == request.user


class CanManageDocuments(permissions.BasePermission):
    """
    Document control permission: only quality managers, quality engineers,
    and admins can create/modify controlled documents.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.role in (
            User.Role.ADMIN,
            User.Role.QUALITY_MANAGER,
            User.Role.QUALITY_ENGINEER,
        )
