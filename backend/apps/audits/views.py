"""
Views for audits app.
"""

from django.db.models import Count, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Audit, AuditChecklistItem, AuditEvidence, AuditFinding
from .serializers import (
    AuditChecklistItemSerializer,
    AuditCreateSerializer,
    AuditDetailSerializer,
    AuditEvidenceSerializer,
    AuditFindingCreateSerializer,
    AuditFindingDetailSerializer,
    AuditFindingListSerializer,
    AuditListSerializer,
)


class AuditViewSet(viewsets.ModelViewSet):
    """CRUD for audits with workflow management."""

    queryset = Audit.objects.select_related("lead_auditor").prefetch_related(
        "auditors", "findings", "checklist_items"
    ).all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["audit_number", "title", "standard", "department"]
    filterset_fields = ["audit_type", "status", "result", "lead_auditor"]
    ordering_fields = ["audit_number", "planned_start", "status", "created_at"]
    ordering = ["-planned_start"]
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return AuditCreateSerializer
        if self.action == "list":
            return AuditListSerializer
        return AuditDetailSerializer

    @action(detail=True, methods=["post"], url_path="start")
    def start_audit(self, request, pk=None):
        """Mark an audit as started."""
        audit = self.get_object()
        if audit.status != Audit.Status.PLANNED:
            return Response(
                {"error": True, "message": "Only planned audits can be started."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        audit.status = Audit.Status.IN_PROGRESS
        audit.actual_start = timezone.now().date()
        audit.save()
        return Response(AuditDetailSerializer(audit).data)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete_audit(self, request, pk=None):
        """Mark an audit as completed and set result."""
        audit = self.get_object()
        if audit.status != Audit.Status.IN_PROGRESS:
            return Response(
                {"error": True, "message": "Only in-progress audits can be completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        audit.status = Audit.Status.COMPLETED
        audit.actual_end = timezone.now().date()
        audit.executive_summary = request.data.get("executive_summary", audit.executive_summary)
        audit.strengths = request.data.get("strengths", audit.strengths)
        audit.opportunities_for_improvement = request.data.get(
            "opportunities_for_improvement",
            audit.opportunities_for_improvement,
        )

        # Auto-determine result based on findings
        major_count = audit.findings.filter(
            classification=AuditFinding.Classification.MAJOR_NC
        ).count()
        minor_count = audit.findings.filter(
            classification=AuditFinding.Classification.MINOR_NC
        ).count()
        if major_count > 0:
            audit.result = Audit.Result.FAIL
        elif minor_count > 0:
            audit.result = Audit.Result.CONDITIONAL
        else:
            audit.result = Audit.Result.PASS

        audit.save()
        return Response(AuditDetailSerializer(audit).data)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """Get audit summary statistics."""
        qs = self.get_queryset()
        today = timezone.now().date()
        return Response({
            "total": qs.count(),
            "planned": qs.filter(status=Audit.Status.PLANNED).count(),
            "in_progress": qs.filter(status=Audit.Status.IN_PROGRESS).count(),
            "completed": qs.filter(status=Audit.Status.COMPLETED).count(),
            "overdue": qs.filter(
                planned_end__lt=today,
            ).exclude(
                status__in=[Audit.Status.COMPLETED, Audit.Status.CANCELLED]
            ).count(),
            "by_type": list(
                qs.values("audit_type").annotate(count=Count("id")).order_by("-count")
            ),
            "by_result": list(
                qs.filter(status=Audit.Status.COMPLETED)
                .values("result")
                .annotate(count=Count("id"))
                .order_by("result")
            ),
            "total_findings": AuditFinding.objects.filter(audit__in=qs).count(),
            "open_findings": AuditFinding.objects.filter(
                audit__in=qs
            ).exclude(
                status=AuditFinding.Status.VERIFIED_CLOSED
            ).count(),
        })


class AuditFindingViewSet(viewsets.ModelViewSet):
    """CRUD for audit findings."""

    queryset = AuditFinding.objects.select_related(
        "audit", "closed_by", "checklist_item"
    ).prefetch_related("evidence_files").all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["finding_number", "description", "clause_reference"]
    filterset_fields = ["audit", "classification", "status"]
    ordering_fields = ["finding_number", "classification", "created_at"]
    ordering = ["-created_at"]
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return AuditFindingCreateSerializer
        if self.action == "list":
            return AuditFindingListSerializer
        return AuditFindingDetailSerializer

    @action(detail=True, methods=["post"], url_path="respond")
    def submit_response(self, request, pk=None):
        """Submit auditee response to a finding."""
        finding = self.get_object()
        finding.auditee_response = request.data.get("auditee_response", "")
        finding.proposed_corrective_action = request.data.get("proposed_corrective_action", "")
        finding.response_date = timezone.now().date()
        finding.status = AuditFinding.Status.RESPONSE_SUBMITTED
        finding.save()
        return Response(AuditFindingDetailSerializer(finding).data)

    @action(detail=True, methods=["post"], url_path="close")
    def close_finding(self, request, pk=None):
        """Close a finding after verification."""
        finding = self.get_object()
        finding.status = AuditFinding.Status.VERIFIED_CLOSED
        finding.closed_by = request.user
        finding.closed_date = timezone.now()
        finding.closure_notes = request.data.get("closure_notes", "")
        finding.save()
        return Response(AuditFindingDetailSerializer(finding).data)


class AuditChecklistItemViewSet(viewsets.ModelViewSet):
    """CRUD for audit checklist items."""

    queryset = AuditChecklistItem.objects.select_related("audit").all()
    serializer_class = AuditChecklistItemSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["audit", "compliance_status"]
    ordering_fields = ["sequence"]
    ordering = ["sequence"]
    permission_classes = [IsAuthenticated]


class AuditEvidenceViewSet(viewsets.ModelViewSet):
    """CRUD for audit evidence files."""

    queryset = AuditEvidence.objects.select_related("audit", "finding", "uploaded_by").all()
    serializer_class = AuditEvidenceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["audit", "finding", "evidence_type"]
    permission_classes = [IsAuthenticated]
