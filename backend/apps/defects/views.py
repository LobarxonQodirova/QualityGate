"""
Views for defects app.
"""

from django.db.models import Count, Q, Sum
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Defect, DefectCategory, DefectImage, RootCauseAnalysis
from .serializers import (
    DefectCategorySerializer,
    DefectCreateSerializer,
    DefectDetailSerializer,
    DefectImageSerializer,
    DefectListSerializer,
    RootCauseAnalysisCreateSerializer,
    RootCauseAnalysisSerializer,
)


class DefectCategoryViewSet(viewsets.ModelViewSet):
    """CRUD for defect categories."""

    queryset = DefectCategory.objects.filter(parent__isnull=True)
    serializer_class = DefectCategorySerializer
    filter_backends = [SearchFilter]
    search_fields = ["name", "code"]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = DefectCategory.objects.all()
        if self.request.query_params.get("top_level") == "true":
            qs = qs.filter(parent__isnull=True)
        return qs


class DefectViewSet(viewsets.ModelViewSet):
    """CRUD for defects with lifecycle management."""

    queryset = Defect.objects.select_related(
        "category", "reported_by", "assigned_to", "closed_by", "inspection"
    ).prefetch_related("images").all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["defect_number", "title", "product_name", "part_number", "batch_number"]
    filterset_fields = ["severity", "status", "category", "detection_method", "assigned_to"]
    ordering_fields = ["defect_number", "severity", "status", "detected_date", "created_at"]
    ordering = ["-created_at"]
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return DefectCreateSerializer
        if self.action == "list":
            return DefectListSerializer
        return DefectDetailSerializer

    @action(detail=True, methods=["post"], url_path="close")
    def close_defect(self, request, pk=None):
        """Close a defect."""
        defect = self.get_object()
        if defect.status == Defect.Status.CLOSED:
            return Response(
                {"error": True, "message": "Defect is already closed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        defect.status = Defect.Status.CLOSED
        defect.closed_date = timezone.now()
        defect.closed_by = request.user
        if request.data.get("actual_cost"):
            defect.actual_cost = request.data["actual_cost"]
        if request.data.get("notes"):
            defect.notes = (defect.notes + "\n\n" + request.data["notes"]).strip()
        defect.save()
        return Response(DefectDetailSerializer(defect).data)

    @action(detail=True, methods=["post"], url_path="assign")
    def assign_defect(self, request, pk=None):
        """Assign a defect to a user."""
        defect = self.get_object()
        user_id = request.data.get("assigned_to")
        if not user_id:
            return Response(
                {"error": True, "message": "assigned_to is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        defect.assigned_to_id = user_id
        if defect.status == Defect.Status.OPEN:
            defect.status = Defect.Status.UNDER_REVIEW
        defect.save()
        return Response(DefectDetailSerializer(defect).data)

    @action(detail=True, methods=["post"], url_path="add-image")
    def add_image(self, request, pk=None):
        """Upload an image to a defect."""
        defect = self.get_object()
        serializer = DefectImageSerializer(
            data={**request.data, "defect": defect.id},
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """Get defect summary statistics."""
        qs = self.get_queryset()
        total = qs.count()
        open_count = qs.exclude(status=Defect.Status.CLOSED).count()
        overdue_count = qs.filter(
            target_close_date__lt=timezone.now().date(),
        ).exclude(status=Defect.Status.CLOSED).count()

        by_severity = qs.values("severity").annotate(count=Count("id")).order_by("severity")
        by_status = qs.values("status").annotate(count=Count("id")).order_by("status")
        by_category = qs.values("category__name").annotate(
            count=Count("id")
        ).order_by("-count")[:10]

        total_cost = qs.aggregate(
            estimated=Sum("estimated_cost"),
            actual=Sum("actual_cost"),
        )

        return Response({
            "total": total,
            "open": open_count,
            "overdue": overdue_count,
            "by_severity": list(by_severity),
            "by_status": list(by_status),
            "by_category": list(by_category),
            "total_estimated_cost": total_cost["estimated"],
            "total_actual_cost": total_cost["actual"],
        })


class DefectImageViewSet(viewsets.ModelViewSet):
    """CRUD for defect images."""

    queryset = DefectImage.objects.select_related("defect", "uploaded_by").all()
    serializer_class = DefectImageSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["defect"]
    permission_classes = [IsAuthenticated]


class RootCauseAnalysisViewSet(viewsets.ModelViewSet):
    """CRUD for root cause analyses."""

    queryset = RootCauseAnalysis.objects.select_related(
        "defect", "analyzed_by", "verified_by"
    ).all()
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["root_cause"]
    filterset_fields = ["methodology", "cause_category", "is_verified"]
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return RootCauseAnalysisCreateSerializer
        return RootCauseAnalysisSerializer

    @action(detail=True, methods=["post"], url_path="verify")
    def verify(self, request, pk=None):
        """Mark an RCA as verified."""
        rca = self.get_object()
        rca.is_verified = True
        rca.verified_by = request.user
        rca.verified_date = timezone.now()
        rca.save()
        return Response(RootCauseAnalysisSerializer(rca).data)
