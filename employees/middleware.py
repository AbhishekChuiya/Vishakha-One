from django.contrib.auth.views import redirect_to_login
from django.shortcuts import render
from django.urls import reverse

from .models import EmployeeProfile, is_company_email


class EmployeePortalAccessMiddleware:
    """Require a valid, active Vishakha employee profile for portal pages."""

    PUBLIC_PREFIXES = (
        "/accounts/login/",
        "/accounts/sso/",
        "/sso/saml/",
        "/saml/metadata/",
        # Sign-out must work even for a signed-in account that has no employee profile
        # (e.g. an admin), otherwise that person is stuck on the "access not enabled" page.
        "/accounts/logout/",
        "/accounts/switch-user/",
        "/accounts/register/",
        "/accounts/activate/",
        "/accounts/password-reset/",
        "/content-manager/",
        "/admin/",
        "/static/",
        "/media/",
    )
    PUBLIC_PATHS = {
        "/admin",  # Allow CommonMiddleware to add the trailing slash.
        "/manifest.webmanifest",
        "/service-worker.js",
        "/pwa-check/",
        "/healthz/",
        "/favicon.ico",
        "/robots.txt",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        is_public = path in self.PUBLIC_PATHS or any(
            path.startswith(prefix) for prefix in self.PUBLIC_PREFIXES
        )

        if not is_public:
            if not request.user.is_authenticated:
                return redirect_to_login(
                    request.get_full_path(),
                    login_url=reverse("accounts:login"),
                )

            profile = EmployeeProfile.objects.filter(
                user_id=request.user.pk,
                is_active=True,
            ).first()
            if (
                profile is None
                or not request.user.is_active
                or not is_company_email(profile.company_email)
                or (request.user.email or "").strip().lower() != profile.company_email
            ):
                return render(request, "accounts/access_denied.html", status=403)

        return self.get_response(request)
