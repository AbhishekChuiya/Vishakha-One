"""Content Manager page to upload or replace the logo of each company application."""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from portal.models import CompanyApplication
from .manager_views import manager_context

MAX_BYTES = 3 * 1024 * 1024


class LogoForm(forms.Form):
    logo = forms.ImageField(required=True)

    def clean_logo(self):
        f = self.cleaned_data["logo"]
        if f.size > MAX_BYTES:
            raise forms.ValidationError("Logo must be smaller than 3 MB.")
        return f


def can_manage_logos(user):
    return bool(user.is_authenticated and user.is_active and (user.is_superuser or user.has_perm("portal.change_companyapplication")))


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def app_logos(request):
    if not can_manage_logos(request.user):
        raise PermissionDenied("You do not have permission to change application logos.")
    if request.method == "POST":
        app = CompanyApplication.objects.filter(pk=request.POST.get("app_id") or 0).first()
        if app is None:
            messages.error(request, "Application not found.")
        elif request.POST.get("remove"):
            if app.logo:
                app.logo.delete(save=False)
                app.logo = None
                app.save(update_fields=["logo"])
            messages.success(request, f"Removed the uploaded logo for {app.name}.")
        else:
            form = LogoForm(request.POST, request.FILES)
            if form.is_valid():
                if app.logo:
                    app.logo.delete(save=False)
                app.logo = form.cleaned_data["logo"]
                app.save(update_fields=["logo"])
                messages.success(request, f"Logo updated for {app.name}.")
            else:
                messages.error(request, f"{app.name}: " + " ".join(form.errors["logo"]))
        return redirect("content_manager:app_logos")
    q = (request.GET.get("q") or "").strip()
    apps = CompanyApplication.objects.all().order_by("display_order", "name")
    if q:
        apps = apps.filter(name__icontains=q)
    return render(request, "content_manager/app_logos.html", {**manager_context(request), "apps": apps, "query": q})
