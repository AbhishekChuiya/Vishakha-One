"""Daily canteen schedule: public employee view, permission-protected editor."""
from datetime import date, timedelta
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse
from django.urls import reverse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from . import canteen_import
from .models import CanteenDay
from .manager_views import manager_context
from portal.views import context as portal_context

PREFILL_KEY = 'canteen_prefill'  # menu read from an uploaded file, shown for review, not yet saved
FIELDS = ('is_holiday', 'lunch_veg_dal', 'lunch_roti', 'lunch_rice', 'lunch_curd', 'snack_type', 'snacks')


class CanteenDayForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['snack_type'].required = False

    def clean_snack_type(self):
        return self.cleaned_data.get('snack_type') or CanteenDay.SNACK_REGULAR

    class Meta:
        model = CanteenDay
        fields = FIELDS
        widgets = {key: forms.TextInput(attrs={'class': 'cm-input', 'placeholder': 'Leave blank if not served'}) for key in FIELDS if key not in ('is_holiday', 'snack_type')}
        widgets['snack_type'] = forms.Select(attrs={'class': 'cm-input'})
        widgets['snacks'] = forms.TextInput(attrs={'class': 'cm-input', 'placeholder': 'e.g. Maggie, Bhel, Sandwich - or the chef\'s special dish'})


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


def _week_label(monday):
    this = week_start(None)
    if monday == this:
        return 'This week'
    if monday == this + timedelta(days=7):
        return 'Next week'
    return f"Week of {monday:%d %b %Y}"


def _is_blank(form):
    data = form.cleaned_data
    return (not data.get('is_holiday') and not any((data.get(k) or '').strip() for k in
            ('lunch_veg_dal', 'lunch_roti', 'lunch_rice', 'lunch_curd', 'snacks')))


@never_cache
@login_required
@require_http_methods(['GET', 'POST'])
def edit_week(request):
    """Edit this week and next week together (Monday to Saturday each). ?week= moves the two-week window."""
    if not can_manage(request.user):
        raise PermissionDenied('You do not have permission to edit the canteen menu.')
    start = week_start(request.GET.get('week') or request.POST.get('week'))
    mondays = [start, start + timedelta(days=7)]
    dates = [m + timedelta(days=i) for m in mondays for i in range(6)]
    existing = {row.date: row for row in CanteenDay.objects.filter(date__in=dates)}
    prefill = None
    if request.method == 'GET':
        if request.GET.get('discard'):
            request.session.pop(PREFILL_KEY, None)
        else:
            stored = request.session.get(PREFILL_KEY)
            if stored and stored.get('week') == start.isoformat():
                prefill = stored
    loaded = (prefill or {}).get('rows', {})
    forms_by_day = {
        day: CanteenDayForm(
            request.POST if request.method == 'POST' else None,
            instance=existing.get(day, CanteenDay(date=day)),
            prefix=day.isoformat(),
            initial=loaded.get(day.isoformat()),
        ) for day in dates
    }
    if request.method == 'POST' and all(form.is_valid() for form in forms_by_day.values()):
        with transaction.atomic():
            for day, form in forms_by_day.items():
                if day not in existing and _is_blank(form):
                    continue                      # never create empty rows for days nobody filled in
                item = form.save(commit=False)
                item.date = day
                item.updated_by = request.user
                if item.is_holiday:
                    item.lunch_veg_dal = item.lunch_roti = item.lunch_rice = item.lunch_curd = item.snacks = ''
                    item.snack_type = CanteenDay.SNACK_REGULAR
                item.save()
        request.session.pop(PREFILL_KEY, None)
        messages.success(request, 'Canteen menu saved successfully.')
        return redirect(f'{request.path}?week={start.isoformat()}')
    weeks = [{'label': _week_label(m), 'monday': m, 'days': [(m + timedelta(days=i), forms_by_day[m + timedelta(days=i)]) for i in range(6)]}
             for m in mondays]
    data = manager_context(request)
    data.update(weeks=weeks, monday=start, previous=start - timedelta(days=7), following=start + timedelta(days=7),
                is_current_window=(start == week_start(None)), prefill=prefill,
                prefill_days=len(loaded), excel_ready=canteen_import.excel_available())
    return render(request, 'content_manager/canteen_week.html', data)


@never_cache
@login_required
@require_GET
def sample_file(request):
    """Download a ready-to-fill sample (Excel, or CSV if Excel support is not installed)."""
    if not can_manage(request.user):
        raise PermissionDenied('You do not have permission to edit the canteen menu.')
    content, filename, content_type = canteen_import.build_sample(week_start(request.GET.get('week')))   # defaults to this week + next week
    response = HttpResponse(content, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@never_cache
@login_required
@require_POST
def upload_week(request):
    """Read an uploaded menu file and fill the weekly form for review. Saves nothing by itself."""
    if not can_manage(request.user):
        raise PermissionDenied('You do not have permission to edit the canteen menu.')
    back = reverse('content_manager:canteen_menu')
    week = week_start(request.POST.get('week')).isoformat()
    upload = request.FILES.get('menu_file')
    if upload is None:
        messages.error(request, 'Please choose a file to upload.')
        return redirect(f'{back}?week={week}')
    if upload.size > canteen_import.MAX_UPLOAD_BYTES:
        messages.error(request, 'The file is larger than 1 MB. A menu file should be tiny; please check it.')
        return redirect(f'{back}?week={week}')
    try:
        result = canteen_import.parse_upload(upload.name, upload.read())
    except canteen_import.ImportProblem as exc:
        messages.error(request, str(exc))
        return redirect(f'{back}?week={week}')
    request.session[PREFILL_KEY] = {
        'week': result.monday.isoformat(),
        'filename': upload.name[:120],
        'rows': {day.isoformat(): values for day, values in result.rows.items()},
        'warnings': result.warnings,
    }
    return redirect(f'{back}?week={result.monday.isoformat()}')


@never_cache
def employee_week(request):
    monday = min(week_start(request.GET.get('week')), week_start(None))  # employees never see next week
    dates = [monday + timedelta(days=i) for i in range(6)]
    rows = {row.date: row for row in CanteenDay.objects.filter(date__in=dates)}
    days = [{'date': day, 'menu': rows.get(day), 'is_today': day == timezone.localdate()} for day in dates]
    data = portal_context()
    data.update(section='canteen', heading='Weekly Canteen Menu', days=days,
                monday=monday, previous=monday-timedelta(days=7))
    return render(request, 'portal/canteen_week.html', data)
