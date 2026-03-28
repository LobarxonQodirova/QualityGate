"""
URL configuration for accounts app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import InspectorViewSet, QualityTeamViewSet, UserViewSet

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"inspectors", InspectorViewSet, basename="inspector")
router.register(r"teams", QualityTeamViewSet, basename="quality-team")

urlpatterns = [
    path("", include(router.urls)),
]
