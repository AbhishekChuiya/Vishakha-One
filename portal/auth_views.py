import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth import views as django_auth_views
from django.urls import reverse, reverse_lazy
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.views.decorators.cache import never_cache
from django.utils.http import url_has_allowed_host_and_scheme

from employees import activation, sso
from employees.models import EmployeeProfile, SsoLoginState, is_company_email
from . import saml_support
from .auth_forms import (
    ActivationSetPasswordForm, EmployeeLoginForm, EmployeePasswordResetForm,
    RegistrationRequestForm, SsoEmployeeIdForm,
)

logger = logging.getLogger(__name__)


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


SSO_GENERIC_ERROR = (
    "Company sign-in did not work. Please try again, or sign in with your Employee ID and password."
)


def _sso_failure(request, message=None, detail=None):
    text = message or SSO_GENERIC_ERROR
    if detail and settings.DEBUG and getattr(settings, "VONE_SSO_DEBUG", False):
        text = f"{text} [debug: {detail}]"
    messages.error(request, text)
    return redirect("accounts:login")


def _sso_state_cutoff():
    return timezone.now() - timedelta(minutes=settings.VONE_SSO_STATE_MINUTES)


@never_cache
def employee_sso(request):
    """Start company sign-in: send the browser to Microsoft Entra ID (SAML)."""
    if request.user.is_authenticated:
        if EmployeeProfile.objects.filter(user=request.user, is_active=True).exists():
            return redirect("portal:home")
        return render(request, "accounts/access_denied.html", status=403)
    if not saml_support.is_configured():
        return render(request, "accounts/sso_unavailable.html")

    SsoLoginState.objects.filter(created_at__lt=timezone.now() - timedelta(days=1)).delete()
    state = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(24)
    try:
        redirect_url, request_id = saml_support.start_login(request, state)
    except Exception as exc:
        logger.error("SSO could not start (%s).", type(exc).__name__)
        return _sso_failure(request)
    SsoLoginState.objects.create(
        state=state, request_id=request_id, nonce=nonce, next_url=_safe_next_url(request))
    request.session["vone_sso_nonce"] = nonce  # binds the result to THIS browser
    return redirect(redirect_url)


@csrf_exempt  # Microsoft posts here from another site; the signed response + single-use state protect it
@never_cache
@require_POST
def sso_acs(request):
    """Receive and verify Microsoft's signed response. Nothing is signed in until sso_complete."""
    state = request.POST.get("RelayState", "")
    claimed = SsoLoginState.objects.filter(
        state=state, used_at__isnull=True, created_at__gte=_sso_state_cutoff()
    ).update(used_at=timezone.now())
    if claimed != 1:
        if not SsoLoginState.objects.filter(state=state).exists() and (
                not state or state.startswith(("http://", "https://"))):
            # Unsolicited response (e.g. the app tile in Microsoft "My Apps"). Never trusted:
            # start a proper sign-in instead; Microsoft already knows the person, so it is instant.
            return redirect("accounts:sso")
        logger.warning("SSO response rejected: unknown, expired or already used state.")
        return _sso_failure(request)
    row = SsoLoginState.objects.get(state=state)
    try:
        result = saml_support.validate_response(request, row.request_id)
    except Exception as exc:
        logger.error("SSO response could not be processed (%s).", type(exc).__name__)
        return _sso_failure(request)
    if not result.ok:
        logger.warning("SSO response rejected: %s", result.reason[:300])
        return _sso_failure(request, detail=result.reason[:200])

    identity = sso.identity_from_attributes(result.attributes, result.name_id)
    complete_url = f"{reverse('accounts:sso_complete')}?state={state}"
    try:
        user, created = sso.resolve_user(identity)
    except sso.SsoDenied as exc:
        if exc.code == "no_employee_id":
            # Verified company user, no account yet, no Employee ID from Microsoft: ask once.
            row.email, row.first_name, row.last_name = identity.email, identity.first_name, identity.last_name
            row.save(update_fields=["email", "first_name", "last_name"])
            return redirect(complete_url)
        logger.warning("SSO sign-in denied (%s).", exc.code)
        names = ", ".join(sorted(result.attributes)) or "none"
        return _sso_failure(request, exc.user_message, detail=f"attributes received: {names}")
    if created:
        logger.info("SSO created employee account for profile %s.", user.employee_profile.pk)
    row.user = user
    row.save(update_fields=["user"])
    return redirect(complete_url)


@never_cache
@require_http_methods(["GET", "POST"])
def sso_complete(request):
    """Second step, same browser: only the browser that started the sign-in can finish it."""
    state = request.GET.get("state") or request.POST.get("state", "")
    nonce = request.session.get("vone_sso_nonce")
    if not nonce or not state:
        return _sso_failure(request)
    row = SsoLoginState.objects.filter(
        state=state, nonce=nonce, completed_at__isnull=True, created_at__gte=_sso_state_cutoff()
    ).select_related("user").first()
    if row is None:
        logger.warning("SSO completion rejected: state/browser mismatch.")
        return _sso_failure(request)

    if row.user_id is None:
        if not row.email:
            return _sso_failure(request)
        form = SsoEmployeeIdForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            identity = sso.Identity(email=row.email, employee_id=form.cleaned_data["employee_id"],
                                    first_name=row.first_name, last_name=row.last_name)
            try:
                row.user = sso.provision(identity)
            except sso.SsoDenied as exc:
                form.add_error("employee_id", exc.user_message)
            else:
                row.save(update_fields=["user"])
        if row.user_id is None:
            return render(request, "accounts/sso_employee_id.html",
                          {"form": form, "state": state, "email": row.email})

    claimed = SsoLoginState.objects.filter(pk=row.pk, completed_at__isnull=True).update(
        completed_at=timezone.now())
    if claimed != 1:
        return _sso_failure(request)
    request.session.pop("vone_sso_nonce", None)
    login(request, row.user, backend="django.contrib.auth.backends.ModelBackend")
    messages.success(request, "You have signed in with company SSO.")
    next_url = row.next_url if url_has_allowed_host_and_scheme(
        row.next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()) else "/"
    return redirect(next_url or "/")


@never_cache
@require_GET
def sso_metadata(request):
    """Service Provider metadata: what IT / Entra needs to know about this application."""
    if not saml_support.is_configured():
        return HttpResponse("SSO is not configured.", status=404, content_type="text/plain")
    try:
        xml = saml_support.sp_metadata_xml(request)
    except Exception as exc:
        logger.error("SSO metadata could not be built (%s).", type(exc).__name__)
        return HttpResponse("SSO metadata unavailable.", status=500, content_type="text/plain")
    return HttpResponse(xml, content_type="text/xml")


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
            link = request.build_absolute_uri(
                reverse("accounts:activate", args=[activation.make_token(*identity)]))
            activation.send_activation_email(identity[0], identity[1], link)
        else:
            # Not registrable. If this mailbox already owns an account, tell its owner (by
            # e-mail only) how to sign in or reset the password. The page reply stays neutral.
            existing = activation.profile_for_email(form.cleaned_data["company_email"])
            if existing:
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
