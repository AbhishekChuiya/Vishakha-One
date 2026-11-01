from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from portal import pwa_views

urlpatterns = [
    # PWA and readiness endpoints
    path("pwa-check/", pwa_views.readiness, name="pwa_readiness"),
    path(
        "manifest.webmanifest",
        pwa_views.manifest,
        name="pwa_manifest",
    ),
    path(
        "service-worker.js",
        pwa_views.service_worker,
        name="pwa_service_worker",
    ),

    # Django administration
    path("admin/", admin.site.urls),

    # Employee authentication
    path("accounts/", include("portal.auth_urls")),

    # Existing Content Manager: kept separate
    path(
        "content-manager/",
        include("contenthub.manager_urls"),
    ),

    # Existing Vishakha One portal
    path("", include("portal.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )