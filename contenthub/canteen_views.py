"""Daily canteen schedule: public employee view, permission-protected editor."""
from datetime import date, timedelta
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .models import CanteenDay
from .manager_views import manager_context
from portal.views import context as portal_context

FIELDS = ('is_holiday', 'lunch_veg_dal', 'lunch_roti', 'lunch_rice', 'lunch_curd', 'snacks')


class CanteenDayForm(forms.ModelForm):
    class Meta:
        model = CanteenDay
        fields = FIELDS
        widgets = {key: forms.TextInput(attrs={'class': 'cm-input', 'placeholder': 'Leave blank if not served'}) for key in FIELDS if key != 'is_holiday'}


def week_start(raw):
    if raw:
        try:
            d = date.fromisoformat(raw)
        except ValueError:
            d = timezone.localdate()
    else:
        d = timezone.localdate()
    return d - timedelta(days=d.weekday())


def can_manage(user):
    return bool(user.is_authenticated and (user.is_superuser or user.has_perm('contenthub.manage_canteen_menu')))


@never_cache
@login_required
@require_http_methods(['GET', 'POST'])
def edit_week(request):
    if not can_manage(request.user):
        raise PermissionDenied('You do not have permission to edit the canteen menu.')
    monday = week_start(request.GET.get('week') or request.POST.get('week'))
    dates = [monday + timedelta(days=i) for i in range(6)]  # Monday through Saturday
    existing = {row.date: row for row in CanteenDay.objects.filter(date__in=dates)}
    forms_by_day = [
        (day, CanteenDayForm(
            request.POST if request.method == 'POST' else None,
            instance=existing.get(day, CanteenDay(date=day)),
            prefix=day.isoformat()
        )) for day in dates
    ]
    if request.method == 'POST' and all(form.is_valid() for _, form in forms_by_day):
        with transaction.atomic():
            for day, form in forms_by_day:
                item = form.save(commit=False)
                item.date = day
                item.updated_by = request.user
                if item.is_holiday:
                    item.lunch_veg_dal = ''
                    item.lunch_roti = ''
                    item.lunch_rice = ''
                    item.lunch_curd = ''
                    item.snacks = ''
                item.save()
        messages.success(request, 'Canteen menu saved successfully.')
        return redirect(f'{request.path}?week={monday.isoformat()}')
    data = manager_context(request)
    data.update(days=forms_by_day, monday=monday, previous=monday-timedelta(days=7),
                following=monday+timedelta(days=7))
    return render(request, 'content_manager/canteen_week.html', data)


@never_cache
def employee_week(request):
    monday = week_start(request.GET.get('week'))
    dates = [monday + timedelta(days=i) for i in range(6)]
    rows = {row.date: row for row in CanteenDay.objects.filter(date__in=dates)}
    days = [{'date': day, 'menu': rows.get(day), 'is_today': day == timezone.localdate()} for day in dates]
    data = portal_context()
    data.update(section='canteen', heading='Weekly Canteen Menu', days=days,
                monday=monday, previous=monday-timedelta(days=7),
                following=monday+timedelta(days=7))
    return render(request, 'portal/canteen_week.html', data)
