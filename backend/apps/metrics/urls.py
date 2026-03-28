"""
URL configuration for metrics app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    MetricDataPointViewSet,
    QualityKPIViewSet,
    SPCControlChartViewSet,
    SPCDataPointViewSet,
)

router = DefaultRouter()
router.register(r"kpis", QualityKPIViewSet, basename="quality-kpi")
router.register(r"data-points", MetricDataPointViewSet, basename="metric-data-point")
router.register(r"spc-charts", SPCControlChartViewSet, basename="spc-control-chart")
router.register(r"spc-data", SPCDataPointViewSet, basename="spc-data-point")

urlpatterns = [
    path("", include(router.urls)),
]
