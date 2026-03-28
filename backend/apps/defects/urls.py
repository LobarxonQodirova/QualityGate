"""
URL configuration for defects app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DefectCategoryViewSet,
    DefectImageViewSet,
    DefectViewSet,
    RootCauseAnalysisViewSet,
)

router = DefaultRouter()
router.register(r"defects", DefectViewSet, basename="defect")
router.register(r"categories", DefectCategoryViewSet, basename="defect-category")
router.register(r"images", DefectImageViewSet, basename="defect-image")
router.register(r"rca", RootCauseAnalysisViewSet, basename="root-cause-analysis")

urlpatterns = [
    path("", include(router.urls)),
]
