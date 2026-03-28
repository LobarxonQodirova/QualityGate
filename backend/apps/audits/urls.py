"""
URL configuration for audits app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AuditChecklistItemViewSet,
    AuditEvidenceViewSet,
    AuditFindingViewSet,
    AuditViewSet,
)

router = DefaultRouter()
router.register(r"audits", AuditViewSet, basename="audit")
router.register(r"findings", AuditFindingViewSet, basename="audit-finding")
router.register(r"checklist-items", AuditChecklistItemViewSet, basename="audit-checklist-item")
router.register(r"evidence", AuditEvidenceViewSet, basename="audit-evidence")

urlpatterns = [
    path("", include(router.urls)),
]
