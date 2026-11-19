"""Content Manager pages for site settings: applications (name, order, logo) and helpful links."""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from portal.models import CompanyApplication, HelpfulLink
from .manager_views import manager_context

MAX_BYTES = 3 * 1024 * 1024


def _can(user, perm):
    return bool(user.is_authenticated and user.is_active and (user.is_superuser or user.has_perm(perm)))


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = CompanyApplication
        fields = ["name", "url", "category", "description", "display_order", "is_active", "logo"]

    def clean_logo(self):
        f = self.cleaned_data.get("logo")
        if f and hasattr(f, "size") and f.size > MAX_BYTES:
            raise forms.ValidationError("Logo must be smaller than 3 MB.")
        return f


class LinkForm(forms.ModelForm):
    class Meta:
        model = HelpfulLink
        fields = ["title", "url", "icon", "display_order", "is_active"]


def _flash_errors(request, label, form):
    for field, errs in form.errors.items():
        messages.error(request, f"{label}: {field} - " + " ".join(errs))


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def applications(request):
    if not _can(request.user, "portal.change_companyapplication"):
        raise PermissionDenied("You do not have permission to manage applications.")
    if request.method == "POST":
        action = request.POST.get("action", "save")
        if action == "add":
            if not _can(request.user, "portal.add_companyapplication"):
                raise PermissionDenied("You do not have permission to add applications.")
            form = ApplicationForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, f"Added {form.instance.name}.")
            else:
                _flash_errors(request, "New application", form)
            return redirect("content_manager:applications")
        app = CompanyApplication.objects.filter(pk=request.POST.get("app_id") or 0).first()
        if app is None:
            messages.error(request, "Application not found.")
        elif action == "remove_logo":
            if app.logo:
                app.logo.delete(save=False)
                app.logo = None
                app.save(update_fields=["logo"])
            messages.success(request, f"Removed the uploaded logo for {app.name}.")
        else:
            old_logo = app.logo.name if app.logo else ""
            form = ApplicationForm(request.POST, request.FILES, instance=app)
            if form.is_valid():
                if request.FILES.get("logo") and old_logo:
                    app.logo.storage.delete(old_logo)
                form.save()
                messages.success(request, f"Saved {app.name}.")
            else:
                _flash_errors(request, app.name, form)
        return redirect("content_manager:applications")
    q = (request.GET.get("q") or "").strip()
    apps = CompanyApplication.objects.all().order_by("display_order", "name")
    if q:
        apps = apps.filter(name__icontains=q)
    return render(request, "content_manager/applications.html", {
        **manager_context(request), "apps": apps, "query": q,
        "can_add": _can(request.user, "portal.add_companyapplication")})


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def helpful_links(request):
    if not _can(request.user, "portal.change_helpfullink"):
        raise PermissionDenied("You do not have permission to manage helpful links.")
    if request.method == "POST":
        action = request.POST.get("action", "save")
        if action == "add":
            if not _can(request.user, "portal.add_helpfullink"):
                raise PermissionDenied("You do not have permission to add links.")
            form = LinkForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, f"Added the link {form.instance.title}.")
            else:
                _flash_errors(request, "New link", form)
        else:
            link = HelpfulLink.objects.filter(pk=request.POST.get("link_id") or 0).first()
            if link is None:
                messages.error(request, "Link not found.")
            elif action == "delete":
                if not _can(request.user, "portal.delete_helpfullink"):
                    raise PermissionDenied("You do not have permission to delete links.")
                link.delete()
                messages.success(request, "Link deleted.")
            else:
                form = LinkForm(request.POST, instance=link)
                if form.is_valid():
                    form.save()
                    messages.success(request, f"Saved {link.title}.")
                else:
                    _flash_errors(request, link.title, form)
        return redirect("content_manager:helpful_links")
    from portal.models import LINK_ICONS
    return render(request, "content_manager/helpful_links.html", {
        **manager_context(request), "links": HelpfulLink.objects.all(), "icons": LINK_ICONS,
        "can_add": _can(request.user, "portal.add_helpfullink"),
        "can_delete": _can(request.user, "portal.delete_helpfullink")})
