"""
Views for inspections app.
"""

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Inspection, InspectionChecklist, InspectionItem, InspectionResult
from .serializers import (
    BulkInspectionResultSerializer,
    InspectionChecklistCreateSerializer,
    InspectionChecklistDetailSerializer,
    InspectionChecklistListSerializer,
    InspectionCreateSerializer,
    InspectionDetailSerializer,
    InspectionItemSerializer,
    InspectionListSerializer,
    InspectionResultCreateSerializer,
    InspectionResultSerializer,
)


class InspectionChecklistViewSet(viewsets.ModelViewSet):
    """CRUD for inspection checklists."""

    queryset = InspectionChecklist.objects.select_related("created_by", "approved_by").all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name", "code", "product_line"]
    filterset_fields = ["checklist_type", "is_active"]
    ordering_fields = ["name", "code", "created_at"]
    ordering = ["-created_at"]
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return InspectionChecklistCreateSerializer
        if self.action == "list":
            return InspectionChecklistListSerializer
        return InspectionChecklistDetailSerializer

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        """Approve a checklist for use."""
        checklist = self.get_object()
        checklist.approved_by = request.user
        checklist.approved_date = timezone.now()
        checklist.save()
        return Response(
            {"message": f"Checklist {checklist.code} approved."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="duplicate")
    def duplicate(self, request, pk=None):
        """Duplicate a checklist with a new revision."""
        original = self.get_object()
        items = list(original.items.all())

        original.pk = None
        original.code = f"{original.code}-COPY"
        try:
            rev_parts = original.revision.split(".")
            rev_parts[-1] = str(int(rev_parts[-1]) + 1)
            original.revision = ".".join(rev_parts)
        except (ValueError, IndexError):
            original.revision = original.revision + ".1"
        original.approved_by = None
        original.approved_date = None
        original.created_by = request.user
        original.save()

        for item in items:
            item.pk = None
            item.checklist = original
            item.save()

        serializer = InspectionChecklistDetailSerializer(original)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class InspectionItemViewSet(viewsets.ModelViewSet):
    """CRUD for inspection items within checklists."""

    queryset = InspectionItem.objects.select_related("checklist").all()
    serializer_class = InspectionItemSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["checklist", "measurement_type", "is_critical", "is_active"]
    ordering_fields = ["sequence"]
    ordering = ["sequence"]
    permission_classes = [IsAuthenticated]


class InspectionViewSet(viewsets.ModelViewSet):
    """CRUD for inspections."""

    queryset = Inspection.objects.select_related(
        "checklist", "inspector", "reviewed_by"
    ).prefetch_related("results").all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["inspection_number", "product_name", "part_number", "batch_number"]
    filterset_fields = ["status", "disposition", "inspector", "checklist"]
    ordering_fields = ["inspection_number", "created_at", "scheduled_date", "completed_at"]
    ordering = ["-created_at"]
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return InspectionCreateSerializer
        if self.action == "list":
            return InspectionListSerializer
        return InspectionDetailSerializer

    @action(detail=True, methods=["post"], url_path="start")
    def start_inspection(self, request, pk=None):
        """Mark inspection as started."""
        inspection = self.get_object()
        if inspection.status != Inspection.Status.PLANNED:
            return Response(
                {"error": True, "message": "Only planned inspections can be started."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        inspection.status = Inspection.Status.IN_PROGRESS
        inspection.started_at = timezone.now()
        if not inspection.inspector:
            inspection.inspector = request.user
        inspection.save()
        return Response(InspectionDetailSerializer(inspection).data)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete_inspection(self, request, pk=None):
        """Mark inspection as completed and calculate disposition."""
        inspection = self.get_object()
        if inspection.status != Inspection.Status.IN_PROGRESS:
            return Response(
                {"error": True, "message": "Only in-progress inspections can be completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inspection.status = Inspection.Status.COMPLETED
        inspection.completed_at = timezone.now()

        # Auto-determine disposition based on results
        results = inspection.results.all()
        if results.exists():
            non_conforming = results.filter(is_conforming=False)
            critical_failures = non_conforming.filter(inspection_item__is_critical=True)
            if critical_failures.exists():
                inspection.disposition = Inspection.Disposition.REJECT
            elif non_conforming.exists():
                inspection.disposition = Inspection.Disposition.CONDITIONAL
            else:
                inspection.disposition = Inspection.Disposition.ACCEPT
        else:
            inspection.disposition = Inspection.Disposition.PENDING

        inspection.save()
        return Response(InspectionDetailSerializer(inspection).data)

    @action(detail=True, methods=["post"], url_path="submit-results")
    def submit_results(self, request, pk=None):
        """Bulk submit inspection results."""
        inspection = self.get_object()
        serializer = BulkInspectionResultSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        results = serializer.save()
        return Response(
            InspectionResultSerializer(results, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class InspectionResultViewSet(viewsets.ModelViewSet):
    """CRUD for inspection results."""

    queryset = InspectionResult.objects.select_related(
        "inspection", "inspection_item", "recorded_by"
    ).all()
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["inspection", "is_conforming", "inspection_item"]
    ordering_fields = ["recorded_at"]
    ordering = ["inspection_item__sequence"]
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return InspectionResultCreateSerializer
        return InspectionResultSerializer
