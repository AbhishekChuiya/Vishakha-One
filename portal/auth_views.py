from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods, require_POST
from django.utils.http import url_has_allowed_host_and_scheme


def _safe_next_url(request, fallback="/"):
    """
    Accept a redirect destination only when it points to this host.
    """
    candidate = request.POST.get("next") or request.GET.get("next") or fallback

    if url_has_allowed_host_and_scheme(
        url=candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate

    return fallback


@require_http_methods(["GET", "POST"])
def employee_login(request):
    """
    Employee login, separate from the Content Manager login.
    """
    if request.user.is_authenticated:
        return redirect("portal:home")

    next_url = _safe_next_url(request)

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, "You have signed in successfully.")
            return redirect(_safe_next_url(request, fallback="/"))
    else:
        form = AuthenticationForm(request)

    return render(
        request,
        "accounts/login.html",
        {
            "form": form,
            "next": next_url,
        },
    )


@require_http_methods(["GET", "POST"])
def employee_signup(request):
    """
    Self-service account creation for the pilot phase.
    Registration can be restricted when corporate SSO is introduced.
    """
    if request.user.is_authenticated:
        return redirect("portal:home")

    if request.method == "POST":
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                "Your account has been created successfully.",
            )
            return redirect("portal:home")
    else:
        form = UserCreationForm()

    return render(
        request,
        "accounts/signup.html",
        {"form": form},
    )


@require_POST
def employee_logout(request):
    """
    End the current employee session.
    Logout uses POST to prevent accidental or cross-site GET logouts.
    """
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("accounts:login")


@login_required
@require_POST
def switch_user(request):
    """
    End the current session and return to the employee login page.
    The next employee must authenticate with their own credentials.
    """
    logout(request)
    messages.success(
        request,
        "You have been signed out. Sign in with another account.",
    )
    return redirect("accounts:login")


def employee_sso(request):
    """
    Temporary SSO landing page.

    Real SSO must be configured with IT using an identity provider.
    This endpoint deliberately does not authenticate anyone.
    """
    if request.user.is_authenticated:
        return redirect("portal:home")

    return render(request, "accounts/sso_unavailable.html")