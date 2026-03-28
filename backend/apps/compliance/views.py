"""
Views for compliance app.
"""

from django.db.models import Count, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    ComplianceAssessment,
    ComplianceRequirement,
    DocumentControl,
    Standard,
)
from .serializers import (
    ComplianceAssessmentCreateSerializer,
    ComplianceAssessmentSerializer,
    ComplianceRequirementCreateSerializer,
    ComplianceRequirementSerializer,
    DocumentControlCreateSerializer,
    DocumentControlDetailSerializer,
    DocumentControlListSerializer,
    StandardCreateSerializer,
    StandardDetailSerializer,
    StandardListSerializer,
)


class StandardViewSet(viewsets.ModelViewSet):
    """CRUD for quality and regulatory standards."""

    queryset = Standard.objects.prefetch_related("requirements").all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["name", "code", "issuing_body"]
    filterset_fields = ["category", "is_active"]
    ordering_fields = ["code", "name", "created_at"]
    ordering = ["code"]
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return StandardCreateSerializer
        if self.action == "list":
            return StandardListSerializer
        return StandardDetailSerializer

    @action(detail=False, methods=["get"], url_path="compliance-overview")
    def compliance_overview(self, request):
        """
        Overview of compliance status across all active standards.
        Suitable for management review dashboards.
        """
        standards = Standard.objects.filter(is_active=True)
        overview = []

        for std in standards:
            total_reqs = std.requirements.filter(is_applicable=True).count()
            if total_reqs == 0:
                continue

            assessed_reqs = ComplianceAssessment.objects.filter(
                requirement__standard=std,
            ).values("requirement").distinct().count()

            compliant_count = 0
            partial_count = 0
            non_compliant_count = 0

            for req in std.requirements.filter(is_applicable=True):
                latest = req.latest_assessment
                if latest:
                    if latest.status == ComplianceAssessment.Status.COMPLIANT:
                        compliant_count += 1
                    elif latest.status == ComplianceAssessment.Status.PARTIALLY_COMPLIANT:
                        partial_count += 1
                    elif latest.status == ComplianceAssessment.Status.NON_COMPLIANT:
                        non_compliant_count += 1

            overview.append({
                "standard_id": str(std.id),
                "standard_code": std.code,
                "standard_name": std.name,
                "total_requirements": total_reqs,
                "assessed": assessed_reqs,
                "compliant": compliant_count,
                "partially_compliant": partial_count,
                "non_compliant": non_compliant_count,
                "not_assessed": total_reqs - assessed_reqs,
                "compliance_percentage": round(
                    (compliant_count / total_reqs) * 100, 1
                ) if total_reqs > 0 else 0,
            })

        return Response(overview)


class ComplianceRequirementViewSet(viewsets.ModelViewSet):
    """CRUD for compliance requirements."""

    queryset = ComplianceRequirement.objects.select_related("standard", "parent_clause").all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["clause_number", "title", "description"]
    filterset_fields = ["standard", "priority", "is_applicable", "responsible_department"]
    ordering_fields = ["clause_number", "standard"]
    ordering = ["standard", "clause_number"]
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ComplianceRequirementCreateSerializer
        return ComplianceRequirementSerializer


class ComplianceAssessmentViewSet(viewsets.ModelViewSet):
    """CRUD for compliance assessments."""

    queryset = ComplianceAssessment.objects.select_related(
        "requirement", "requirement__standard", "assessed_by", "reviewed_by"
    ).all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["evidence_description", "gaps_identified"]
    filterset_fields = ["requirement", "status", "assessed_by"]
    ordering_fields = ["assessment_date", "created_at"]
    ordering = ["-assessment_date"]
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ComplianceAssessmentCreateSerializer
        return ComplianceAssessmentSerializer

    @action(detail=True, methods=["post"], url_path="review")
    def review(self, request, pk=None):
        """Mark an assessment as reviewed."""
        assessment = self.get_object()
        assessment.reviewed_by = request.user
        assessment.review_date = timezone.now().date()
        assessment.save()
        return Response(ComplianceAssessmentSerializer(assessment).data)


class DocumentControlViewSet(viewsets.ModelViewSet):
    """CRUD for controlled documents with workflow."""

    queryset = DocumentControl.objects.select_related(
        "author", "approved_by", "standard", "supersedes"
    ).all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ["document_number", "title", "description"]
    filterset_fields = ["document_type", "status", "department", "standard"]
    ordering_fields = ["document_number", "title", "created_at", "effective_date"]
    ordering = ["document_number"]
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return DocumentControlCreateSerializer
        if self.action == "list":
            return DocumentControlListSerializer
        return DocumentControlDetailSerializer

    @action(detail=True, methods=["post"], url_path="approve")
    def approve_document(self, request, pk=None):
        """Approve a document and set it as effective."""
        doc = self.get_object()
        if doc.status not in (DocumentControl.Status.DRAFT, DocumentControl.Status.IN_REVIEW):
            return Response(
                {"error": True, "message": "Only draft or in-review documents can be approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        doc.approved_by = request.user
        doc.approved_date = timezone.now()
        doc.status = DocumentControl.Status.APPROVED
        doc.save()
        return Response(DocumentControlDetailSerializer(doc).data)

    @action(detail=True, methods=["post"], url_path="make-effective")
    def make_effective(self, request, pk=None):
        """Activate an approved document."""
        doc = self.get_object()
        if doc.status != DocumentControl.Status.APPROVED:
            return Response(
                {"error": True, "message": "Only approved documents can be made effective."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        doc.status = DocumentControl.Status.EFFECTIVE
        doc.effective_date = timezone.now().date()
        doc.save()

        # Supersede the previous version if set
        if doc.supersedes and doc.supersedes.status == DocumentControl.Status.EFFECTIVE:
            doc.supersedes.status = DocumentControl.Status.SUPERSEDED
            doc.supersedes.save()

        return Response(DocumentControlDetailSerializer(doc).data)

    @action(detail=True, methods=["post"], url_path="create-revision")
    def create_revision(self, request, pk=None):
        """Create a new revision of a document."""
        original = self.get_object()

        new_doc = DocumentControl(
            title=original.title,
            document_type=original.document_type,
            status=DocumentControl.Status.DRAFT,
            description=original.description,
            standard=original.standard,
            department=original.department,
            process_area=original.process_area,
            supersedes=original,
            author=request.user,
            retention_period_years=original.retention_period_years,
        )

        # Increment revision
        rev = original.revision
        if rev.isalpha() and len(rev) == 1:
            new_doc.revision = chr(ord(rev) + 1)
        else:
            try:
                new_doc.revision = str(int(rev) + 1)
            except ValueError:
                new_doc.revision = rev + ".1"

        # Copy the file reference
        if original.file:
            new_doc.file = original.file

        new_doc.save()
        return Response(
            DocumentControlDetailSerializer(new_doc).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="review-due")
    def documents_due_for_review(self, request):
        """List documents that are due or overdue for periodic review."""
        today = timezone.now().date()
        docs = DocumentControl.objects.filter(
            status=DocumentControl.Status.EFFECTIVE,
            review_date__lte=today,
        ).order_by("review_date")
        serializer = DocumentControlListSerializer(docs, many=True)
        return Response(serializer.data)
