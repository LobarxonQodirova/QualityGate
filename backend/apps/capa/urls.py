"""
URL configuration for CAPA app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CAPATaskViewSet, CorrectiveActionViewSet, PreventiveActionViewSet

router = DefaultRouter()
router.register(r"corrective", CorrectiveActionViewSet, basename="corrective-action")
router.register(r"preventive", PreventiveActionViewSet, basename="preventive-action")
router.register(r"tasks", CAPATaskViewSet, basename="capa-task")

urlpatterns = [
    path("", include(router.urls)),
]
