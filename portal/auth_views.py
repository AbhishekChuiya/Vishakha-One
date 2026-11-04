from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth import views as django_auth_views
from django.urls import reverse, reverse_lazy
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.cache import never_cache
from django.utils.http import url_has_allowed_host_and_scheme

from employees import activation
from employees.models import EmployeeProfile, is_company_email
from . import auth_throttle
from .auth_forms import (
    ActivationSetPasswordForm, EmployeeLoginForm, EmployeePasswordResetForm,
    RegistrationRequestForm,
)


def _safe_next_url(request, fallback="/"):
    candidate = request.POST.get("next") or request.GET.get("next") or fallback
    if url_has_allowed_host_and_scheme(
        url=candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return fallback


@never_cache
@require_http_methods(["GET", "POST"])
def employee_login(request):
    """Authenticate an employee by Employee ID or @vishakha.com email."""
    if request.user.is_authenticated:
        profile = EmployeeProfile.objects.filter(
            user=request.user, is_active=True
        ).first()
        if (
            profile
            and request.user.is_active
            and is_company_email(profile.company_email)
            and (request.user.email or "").strip().lower() == profile.company_email
        ):
            return redirect("portal:home")
        return render(request, "accounts/access_denied.html", status=403)

    next_url = _safe_next_url(request)
    if request.method == "POST":
        form = EmployeeLoginForm(request, request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, "You have signed in successfully.")
            return redirect(_safe_next_url(request, fallback="/"))
    else:
        form = EmployeeLoginForm(request)

    return render(request, "accounts/login.html", {
        "form": form,
        "next": next_url,
        "sso_enabled": getattr(settings, "VONE_SSO_ENABLED", False),
    })


@never_cache
@require_POST
def employee_logout(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("accounts:login")


@never_cache
@require_POST
def switch_user(request):
    logout(request)
    messages.success(request, "You have been signed out. Sign in with another account.")
    return redirect("accounts:login")


@never_cache
def employee_sso(request):
    """Placeholder until Vishakha's identity provider details are supplied by IT."""
    if request.user.is_authenticated:
        profile = EmployeeProfile.objects.filter(user=request.user, is_active=True).first()
        if profile:
            return redirect("portal:home")
    return render(request, "accounts/sso_unavailable.html")



# ---------------------------------------------------------------- registration
@never_cache
@require_http_methods(["GET", "POST"])
def register(request):
    """Step 1: employee enters Employee ID + company email. A link is e-mailed to that mailbox
    when the identity is free. The reply is identical either way (no account enumeration)."""
    if request.user.is_authenticated:
        return redirect("portal:home")
    if not activation.registration_enabled():
        return render(request, "accounts/register_closed.html", status=403)
    form = RegistrationRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        identity = activation.registrable_identity(
            form.cleaned_data["employee_id"], form.cleaned_data["company_email"])
        if identity:
            if auth_throttle.allow("activation", identity[1]):
                link = request.build_absolute_uri(
                    reverse("accounts:activate", args=[activation.make_token(*identity)]))
                activation.send_activation_email(identity[0], identity[1], link)
        else:
            # Not registrable. If this mailbox already owns an account, tell its owner (by
            # e-mail only) how to sign in or reset the password. The page reply stays neutral.
            existing = activation.profile_for_email(form.cleaned_data["company_email"])
            if existing and auth_throttle.allow("activation", existing.company_email):
                activation.send_already_registered_email(
                    existing,
                    request.build_absolute_uri(reverse("accounts:login")),
                    request.build_absolute_uri(reverse("accounts:password_reset")),
                )
        return redirect("accounts:register_done")
    return render(request, "accounts/register.html", {"form": form})


@never_cache
def register_done(request):
    return render(request, "accounts/register_done.html")


@never_cache
@require_http_methods(["GET", "POST"])
def activate(request, token):
    """Step 2: from the e-mailed link, choose a password and create the account."""
    if request.user.is_authenticated:
        return redirect("portal:home")
    if not activation.registration_enabled():
        return render(request, "accounts/register_closed.html", status=403)
    identity = activation.identity_from_token(token)
    if identity is None:
        return render(request, "accounts/activation_invalid.html", status=400)
    form = ActivationSetPasswordForm(
        request.POST or None, user=activation.unsaved_user_for(*identity))
    if request.method == "POST" and form.is_valid():
        try:
            activation.activate(identity[0], identity[1], form.cleaned_data["password1"])
        except activation.ActivationError:
            return render(request, "accounts/activation_invalid.html", status=400)
        messages.success(
            request, "Your account is ready. Sign in with your Employee ID or company email.")
        return redirect("accounts:login")
    return render(request, "accounts/activate.html", {
        "form": form, "employee_id": identity[0], "company_email": identity[1]})


# -------------------------------------------------------------- password reset
class EmployeePasswordResetView(django_auth_views.PasswordResetView):
    form_class = EmployeePasswordResetForm
    template_name = "accounts/password_reset_form.html"
    email_template_name = "accounts/email/password_reset_email.txt"
    subject_template_name = "accounts/email/password_reset_subject.txt"
    html_email_template_name = "accounts/email/password_reset_email.html"
    success_url = reverse_lazy("accounts:password_reset_done")


class EmployeePasswordResetDoneView(django_auth_views.PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class EmployeePasswordResetConfirmView(django_auth_views.PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class EmployeePasswordResetCompleteView(django_auth_views.PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"
