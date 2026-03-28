"""
Views for CAPA app.
"""

from django.db.models import Count, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import CAPATask, CorrectiveAction, PreventiveAction
from .serializers import (
    CAPATaskSerializer,
    CorrectiveActionCreateSerializer,
    CorrectiveActionDetailSerializer,
    CorrectiveActionListSerializer,
    PreventiveActionCreateSerializer,
    PreventiveActionDetailSerializer,
    PreventiveActionListSerializer,
)


class CorrectiveActionViewSet(viewsets.ModelViewSet):
    """CRUD for corrective actions with workflow management."""

    queryset = CorrectiveAction.objects.select_related(
        "initiated_by", "assigned_to", "verified_by", "defect"
    ).prefetch_related("tasks").all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["ca_number", "title", "description"]
    filterset_fields = ["status", "priority", "source", "assigned_to"]
    ordering_fields = ["ca_number", "priority", "status", "target_date", "created_at"]
    ordering = ["-created_at"]
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return CorrectiveActionCreateSerializer
        if self.action == "list":
            return CorrectiveActionListSerializer
        return CorrectiveActionDetailSerializer

    @action(detail=True, methods=["post"], url_path="verify")
    def verify(self, request, pk=None):
        """Verify the effectiveness of a corrective action."""
        ca = self.get_object()
        effectiveness = request.data.get("effectiveness_rating")
        results = request.data.get("verification_results", "")
        method = request.data.get("verification_method", "")

        if not effectiveness:
            return Response(
                {"error": True, "message": "effectiveness_rating is required (1-5)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ca.verified_by = request.user
        ca.verification_date = timezone.now()
        ca.effectiveness_rating = int(effectiveness)
        ca.verification_results = results
        ca.verification_method = method

        if int(effectiveness) >= 4:
            ca.status = CorrectiveAction.Status.VERIFIED_EFFECTIVE
        else:
            ca.status = CorrectiveAction.Status.VERIFIED_INEFFECTIVE

        ca.save()
        return Response(CorrectiveActionDetailSerializer(ca).data)

    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        """Close a corrective action."""
        ca = self.get_object()
        if ca.status not in (
            CorrectiveAction.Status.VERIFIED_EFFECTIVE,
            CorrectiveAction.Status.CANCELLED,
        ):
            return Response(
                {"error": True, "message": "CA must be verified effective before closing."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ca.status = CorrectiveAction.Status.CLOSED
        ca.completed_date = timezone.now()
        ca.save()
        return Response(CorrectiveActionDetailSerializer(ca).data)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """Get corrective action summary statistics."""
        qs = self.get_queryset()
        today = timezone.now().date()
        return Response({
            "total": qs.count(),
            "open": qs.filter(status__in=[
                CorrectiveAction.Status.OPEN,
                CorrectiveAction.Status.IN_PROGRESS,
            ]).count(),
            "overdue": qs.filter(
                target_date__lt=today,
            ).exclude(status__in=[
                CorrectiveAction.Status.CLOSED,
                CorrectiveAction.Status.CANCELLED,
                CorrectiveAction.Status.VERIFIED_EFFECTIVE,
            ]).count(),
            "pending_verification": qs.filter(
                status=CorrectiveAction.Status.PENDING_VERIFICATION
            ).count(),
            "closed_this_month": qs.filter(
                status=CorrectiveAction.Status.CLOSED,
                completed_date__month=today.month,
                completed_date__year=today.year,
            ).count(),
            "by_priority": list(
                qs.values("priority").annotate(count=Count("id")).order_by("priority")
            ),
            "by_source": list(
                qs.values("source").annotate(count=Count("id")).order_by("-count")
            ),
        })


class PreventiveActionViewSet(viewsets.ModelViewSet):
    """CRUD for preventive actions."""

    queryset = PreventiveAction.objects.select_related(
        "initiated_by", "assigned_to", "verified_by"
    ).prefetch_related("tasks").all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["pa_number", "title", "description"]
    filterset_fields = ["status", "priority", "assigned_to"]
    ordering_fields = ["pa_number", "priority", "status", "target_date", "created_at"]
    ordering = ["-created_at"]
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return PreventiveActionCreateSerializer
        if self.action == "list":
            return PreventiveActionListSerializer
        return PreventiveActionDetailSerializer

    @action(detail=True, methods=["post"], url_path="verify")
    def verify(self, request, pk=None):
        """Verify a preventive action."""
        pa = self.get_object()
        pa.verified_by = request.user
        pa.verification_date = timezone.now()
        pa.verification_results = request.data.get("verification_results", "")
        pa.verification_method = request.data.get("verification_method", "")
        pa.status = PreventiveAction.Status.VERIFIED_EFFECTIVE
        pa.save()
        return Response(PreventiveActionDetailSerializer(pa).data)

    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        """Close a preventive action."""
        pa = self.get_object()
        pa.status = PreventiveAction.Status.CLOSED
        pa.completed_date = timezone.now()
        pa.save()
        return Response(PreventiveActionDetailSerializer(pa).data)


class CAPATaskViewSet(viewsets.ModelViewSet):
    """CRUD for CAPA tasks."""

    queryset = CAPATask.objects.select_related(
        "corrective_action", "preventive_action", "assigned_to"
    ).all()
    serializer_class = CAPATaskSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["title"]
    filterset_fields = ["status", "corrective_action", "preventive_action", "assigned_to"]
    ordering_fields = ["sequence", "due_date", "status"]
    ordering = ["sequence"]
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"], url_path="complete")
    def complete_task(self, request, pk=None):
        """Mark a task as completed."""
        task = self.get_object()
        task.status = CAPATask.Status.COMPLETED
        task.completed_date = timezone.now()
        task.completion_notes = request.data.get("completion_notes", "")
        task.save()
        return Response(CAPATaskSerializer(task).data)
