"""
QualityGate URL Configuration.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    # Admin
    path("api/admin/", admin.site.urls),

    # JWT Authentication
    path("api/v1/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # App URLs
    path("api/v1/accounts/", include("apps.accounts.urls")),
    path("api/v1/inspections/", include("apps.inspections.urls")),
    path("api/v1/defects/", include("apps.defects.urls")),
    path("api/v1/capa/", include("apps.capa.urls")),
    path("api/v1/audits/", include("apps.audits.urls")),
    path("api/v1/metrics/", include("apps.metrics.urls")),
    path("api/v1/compliance/", include("apps.compliance.urls")),

    # API Schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "QualityGate Administration"
admin.site.site_title = "QualityGate Admin"
admin.site.index_title = "Quality Control & Assurance System"
