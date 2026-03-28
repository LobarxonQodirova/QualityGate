"""
Views for accounts app.
"""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from .models import Inspector, QualityTeam, User
from .serializers import (
    ChangePasswordSerializer,
    InspectorSerializer,
    QualityTeamSerializer,
    UserCreateSerializer,
    UserDetailSerializer,
    UserListSerializer,
)


class IsAdminOrQualityManager(permissions.BasePermission):
    """Allow access only to admins and quality managers."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.role in (User.Role.ADMIN, User.Role.QUALITY_MANAGER)


class UserViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for users.
    List/retrieve: any authenticated user.
    Create/update/delete: admin or quality manager only.
    """

    queryset = User.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["first_name", "last_name", "email", "employee_id"]
    filterset_fields = ["role", "department", "is_active", "is_certified_inspector"]
    ordering_fields = ["last_name", "first_name", "created_at", "role"]
    ordering = ["last_name", "first_name"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action == "list":
            return UserListSerializer
        return UserDetailSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdminOrQualityManager()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=["get"], url_path="me")
    def current_user(self, request):
        """Get current authenticated user profile."""
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="change-password")
    def change_password(self, request):
        """Change current user's password."""
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response(
            {"message": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )


class InspectorViewSet(viewsets.ModelViewSet):
    """CRUD operations for inspector profiles."""

    queryset = Inspector.objects.select_related("user").all()
    serializer_class = InspectorSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["user__first_name", "user__last_name", "certification_number"]
    filterset_fields = ["certification_level", "is_active"]
    ordering_fields = ["certification_level", "certified_date", "total_inspections"]
    ordering = ["-certification_level"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdminOrQualityManager()]
        return [permissions.IsAuthenticated()]


class QualityTeamViewSet(viewsets.ModelViewSet):
    """CRUD operations for quality teams."""

    queryset = QualityTeam.objects.select_related("leader").prefetch_related("members").all()
    serializer_class = QualityTeamSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name", "production_area"]
    filterset_fields = ["is_active"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdminOrQualityManager()]
        return [permissions.IsAuthenticated()]
