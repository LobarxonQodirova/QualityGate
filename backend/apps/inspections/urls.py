"""
URL configuration for inspections app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    InspectionChecklistViewSet,
    InspectionItemViewSet,
    InspectionResultViewSet,
    InspectionViewSet,
)

router = DefaultRouter()
router.register(r"inspections", InspectionViewSet, basename="inspection")
router.register(r"checklists", InspectionChecklistViewSet, basename="checklist")
router.register(r"checklist-items", InspectionItemViewSet, basename="checklist-item")
router.register(r"results", InspectionResultViewSet, basename="inspection-result")

urlpatterns = [
    path("", include(router.urls)),
]
