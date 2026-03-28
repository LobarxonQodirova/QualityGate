"""
URL configuration for compliance app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ComplianceAssessmentViewSet,
    ComplianceRequirementViewSet,
    DocumentControlViewSet,
    StandardViewSet,
)

router = DefaultRouter()
router.register(r"standards", StandardViewSet, basename="standard")
router.register(r"requirements", ComplianceRequirementViewSet, basename="compliance-requirement")
router.register(r"assessments", ComplianceAssessmentViewSet, basename="compliance-assessment")
router.register(r"documents", DocumentControlViewSet, basename="document-control")

urlpatterns = [
    path("", include(router.urls)),
]
