from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from datetime import timedelta
from statistics import mean
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import Http404, HttpResponseNotAllowed, HttpResponse
from django.core.paginator import Paginator
import csv
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from .models import Announcement, Resource, JobOpening, NewJoiner, Event, ContentNotification, ContentAuditEvent
from .manager_forms import AnnouncementForm, ResourceForm, JobOpeningForm, NewJoinerForm, EventForm

SECTIONS = {
    'announcements': {'model': Announcement, 'form': AnnouncementForm, 'title': 'News & Announcements', 'icon': '📣', 'description': 'Share company news and employee recognition'},
    'resources': {'model': Resource, 'form': ResourceForm, 'title': 'Policies & Documents', 'icon': '📄', 'description': 'Publish policies, forms and brochures'},
    'jobs': {'model': JobOpening, 'form': JobOpeningForm, 'title': 'Job Openings', 'icon': '💼', 'description': 'Post internal vacancies'},
    'joiners': {'model': NewJoiner, 'form': NewJoinerForm, 'title': 'New Joiners', 'icon': '👋', 'description': 'Welcome new colleagues'},
    'events': {'model': Event, 'form': EventForm, 'title': 'Events', 'icon': '📅', 'description': 'Share events and activities'},
}


def is_policy_editor(user):
    # A dedicated role. Never grant this group full Resource access by accident.
    return (not user.is_superuser and user.groups.filter(name='Policy Editors').exists()
            and not user.groups.filter(name='Administration').exists())


def scoped_queryset(user, model):
    qs = model.objects.all()
    if model is Resource and is_policy_editor(user):
        qs = qs.filter(kind='policy')
    return qs


def get_scoped_object(user, model, pk):
    return get_object_or_404(scoped_queryset(user, model), pk=pk)


def can_approve(user, model):
    return (user.is_active and (user.is_superuser or
            user.has_perm(f'contenthub.approve_{model._meta.model_name}')))


def may_publish(user, model):
    # Only approvers can bypass the approval queue.
    return allowed(user, model, 'change') and can_approve(user, model)


def section_or_404(slug):
    config = SECTIONS.get(slug)
    if config is None:
        raise Http404('Unknown content section')
    return config


def allowed(user, model, action='view'):
    return user.is_active and (user.is_superuser or user.has_perm(f'{model._meta.app_label}.{action}_{model._meta.model_name}'))


def require(user, model, action):
    if not allowed(user, model, action):
        raise PermissionDenied('You do not have permission to perform this action.')


def audit(actor, slug, record, action, note=''):
    ContentAuditEvent.objects.create(section=slug, object_id=record.pk, actor=actor,
        actor_label=actor.get_username() if actor else '', action=action, note=note[:4000])


def notify(recipient, actor, slug, record, kind, message):
    if recipient and recipient.is_active:
        ContentNotification.objects.create(
            recipient=recipient, actor=actor, section=slug, object_id=record.pk,
            title=record.title, kind=kind, message=message,
        )


def notify_approvers(actor, slug, model, record, kind='pending'):
    perm = f'contenthub.approve_{model._meta.model_name}'
    User = get_user_model()
    # Django's has_perm supports group and direct user permissions.
    for user in User.objects.filter(is_active=True).exclude(pk=actor.pk):
        if can_approve(user, model) and (model is not Resource or scoped_queryset(user, model).filter(pk=record.pk).exists()):
            notify(user, actor, slug, record, kind, f'{actor.get_username()} submitted this item for your review.')


def manager_context(request):
    return {
        'notifications': ContentNotification.objects.filter(recipient=request.user)[:8],
        'unread_count': ContentNotification.objects.filter(recipient=request.user, is_read=False).count(),
        'sections': [{**config, 'slug': slug, 'can_view': any(allowed(request.user, config['model'], a) for a in ('view', 'add', 'change'))} for slug, config in SECTIONS.items()],
        'employee_portal_url': reverse('portal:home'),
    }


@never_cache
@login_required
def dashboard(request):
    cards = []
    for slug, config in SECTIONS.items():
        model = config['model']
        if any(allowed(request.user, model, a) for a in ('view', 'add', 'change')):
            cards.append({**config, 'slug': slug, 'total': scoped_queryset(request.user, model).count(), 'drafts': scoped_queryset(request.user, model).filter(is_published=False).count(), 'can_add': allowed(request.user, model, 'add'), 'pending_reviews': scoped_queryset(request.user, model).filter(approval_status='pending').count() if can_approve(request.user, model) else 0, 'overdue_reviews': scoped_queryset(request.user, model).filter(approval_status='pending', submitted_at__lte=timezone.now()-timedelta(hours=48)).count() if can_approve(request.user, model) else 0})
    if not cards:
        raise PermissionDenied('Your account has not been given Content Manager access. Please contact IT.')
    data = manager_context(request)
    data['cards'] = cards
    data['approval_queue_access'] = any(can_approve(request.user, cfg['model']) for cfg in SECTIONS.values())
    return render(request, 'content_manager/dashboard.html', data)


@never_cache
@login_required
def listing(request, slug):
    config = section_or_404(slug)
    model = config['model']
    if not any(allowed(request.user, model, a) for a in ('view', 'add', 'change')):
        raise PermissionDenied('You do not have access to this module.')
    query = request.GET.get('q', '').strip()[:100]
    status = request.GET.get('status', 'all')
    records = scoped_queryset(request.user, model).order_by('-updated_at')
    if query:
        filters = Q(title__icontains=query) | Q(summary__icontains=query)
        if slug == 'joiners':
            filters |= Q(employee_name__icontains=query)
        records = records.filter(filters)
    if status == 'published':
        records = records.filter(is_published=True, approval_status='approved', published_at__lte=timezone.now())
    elif status == 'draft':
        records = records.filter(approval_status='draft')
    elif status == 'scheduled':
        records = records.filter(is_published=True, approval_status='approved', published_at__gt=timezone.now())
    if status == 'pending':
        records = records.filter(approval_status='pending')
    elif status == 'rejected':
        records = records.filter(approval_status='rejected')
    data = manager_context(request)
    data.update(config=config, slug=slug, can_approve=can_approve(request.user, model), records=records[:150], query=query, status=status,
                can_add=allowed(request.user, model, 'add'), can_change=allowed(request.user, model, 'change'),
                can_delete=allowed(request.user, model, 'delete'), now=timezone.now())
    return render(request, 'content_manager/list.html', data)


@never_cache
@login_required
def edit(request, slug, pk=None):
    config = section_or_404(slug)
    model = config['model']
    action = 'change' if pk else 'add'
    require(request.user, model, action)
    obj = get_scoped_object(request.user, model, pk) if pk else None
    form = config['form'](request.POST or None, request.FILES or None, instance=obj)
    if model is Resource and is_policy_editor(request.user):
        form.fields['kind'].choices = [('policy', 'Policy')]
        form.fields['kind'].initial = 'policy'
    if request.method == 'POST' and form.is_valid():
        intent = request.POST.get('save_action', 'draft')
        if intent not in ('draft', 'submit', 'publish', 'schedule'):
            raise PermissionDenied('Invalid content action.')
        if intent == 'submit' and can_approve(request.user, model):
            raise PermissionDenied('Approvers cannot submit content for approval. Use the approval review actions instead.')
        if intent in ('publish', 'schedule') and not may_publish(request.user, model):
            raise PermissionDenied('Only an authorized approver may publish content.')
        previous_status = obj.approval_status if obj else None
        record = form.save(commit=False)
        if model is Resource and is_policy_editor(request.user):
            record.kind = 'policy'
        # Edits must never leave an unreviewed version publicly visible.
        record.is_published = False
        record.reviewed_by = None
        record.reviewed_at = None
        record.review_note = ''
        if intent == 'draft':
            record.approval_status = 'draft'
        elif intent == 'submit':
            record.approval_status = 'pending'
            record.submitted_by = request.user
            record.submitted_at = timezone.now()
        elif intent == 'publish':
            record.approval_status = 'approved'
            record.is_published = True
            record.published_at = timezone.now()
            record.reviewed_by = request.user
            record.reviewed_at = timezone.now()
        else:
            scheduled = form.cleaned_data.get('published_at')
            if not scheduled or scheduled <= timezone.now():
                form.add_error('published_at', 'Choose a future date and time in IST.')
            else:
                record.approval_status = 'approved'
                record.is_published = True
                record.published_at = scheduled
                record.reviewed_by = request.user
                record.reviewed_at = timezone.now()
        if not form.errors:
            with transaction.atomic():
                record.save()
                form.save_m2m()
                audit(request.user, slug, record, {'draft':'draft_saved', 'submit':'submitted', 'publish':'published', 'schedule':'scheduled'}[intent])
                if intent == 'submit':
                    notify_approvers(request.user, slug, model, record, 'resubmitted' if previous_status == 'rejected' else 'pending')
            messages.success(request, {
                'draft': 'Saved as draft.',
                'submit': 'Submitted for approval. It is not visible to employees yet.',
                'publish': 'Published to the employee portal.',
                'schedule': 'Approved and scheduled for the selected IST date and time.',
            }[intent])
            return redirect('content_manager:list', slug=slug)
    data = manager_context(request)
    data.update(audit_events=ContentAuditEvent.objects.filter(section=slug, object_id=obj.pk).select_related('actor')[:100] if obj else [], config=config, slug=slug, form=form, editing=bool(pk), record=obj, can_publish=may_publish(request.user, model), can_submit=allowed(request.user, model, 'change') and not can_approve(request.user, model))
    return render(request, 'content_manager/form.html', data)


@never_cache
@login_required
def delete(request, slug, pk):
    config = section_or_404(slug)
    model = config['model']
    require(request.user, model, 'delete')
    record = get_scoped_object(request.user, model, pk)
    if request.method == 'POST':
        with transaction.atomic():
            audit(request.user, slug, record, 'deleted')
            record.delete()
        messages.success(request, 'Content deleted.')
        return redirect('content_manager:list', slug=slug)
    data = manager_context(request)
    data.update(config=config, slug=slug, record=record)
    return render(request, 'content_manager/delete.html', data)


@never_cache
@login_required
@require_POST
def toggle_publish(request, slug, pk):
    config = section_or_404(slug)
    model = config['model']
    require(request.user, model, 'change')
    if not can_approve(request.user, model):
        raise PermissionDenied('Submit this item for approval instead.')
    record = get_scoped_object(request.user, model, pk)
    record.is_published = not record.is_published
    if record.is_published:
        record.approval_status = 'approved'
        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.published_at = timezone.now()
    else:
        record.approval_status = 'draft'
    with transaction.atomic():
        record.save(update_fields=['is_published', 'approval_status', 'reviewed_by', 'reviewed_at', 'published_at', 'updated_at'])
        audit(request.user, slug, record, 'published' if record.is_published else 'unpublished')
    messages.success(request, 'Published on the employee portal.' if record.is_published else 'Moved back to drafts.')
    return redirect('content_manager:list', slug=slug)


@never_cache
@login_required
@require_POST
def review(request, slug, pk):
    config = section_or_404(slug)
    model = config['model']
    if not can_approve(request.user, model):
        raise PermissionDenied('Only designated approvers can review submissions.')
    record = get_scoped_object(request.user, model, pk)
    if record.approval_status != 'pending':
        messages.error(request, 'This item is not awaiting approval.')
        return redirect('content_manager:list', slug=slug)
    action = request.POST.get('decision')
    if action not in ('approve', 'reject'):
        raise PermissionDenied('Invalid review decision.')
    note = request.POST.get('review_note', '').strip()[:2000]
    if action == 'reject' and not note:
        messages.error(request, 'Please explain what needs to be changed.')
        return redirect('content_manager:list', slug=slug)
    record.approval_status = 'approved' if action == 'approve' else 'rejected'
    record.is_published = action == 'approve'
    if action == 'approve' and record.published_at <= timezone.now():
        record.published_at = timezone.now()
    record.reviewed_by = request.user
    record.reviewed_at = timezone.now()
    record.review_note = note
    with transaction.atomic():
        record.save()
        audit(request.user, slug, record, 'approved' if action == 'approve' else 'changes_requested', note)
        notify(record.submitted_by, request.user, slug, record, 'approved' if action == 'approve' else 'changes',
               'Your content was approved.' if action == 'approve' else note)
    messages.success(request, 'Approved for publication.' if action == 'approve' else 'Returned to creator with feedback.')
    return redirect('content_manager:list', slug=slug)


@never_cache
@login_required
@require_POST
def mark_notification_read(request, pk):
    notification = get_object_or_404(ContentNotification, pk=pk, recipient=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    config = SECTIONS.get(notification.section)
    if config and any(allowed(request.user, config['model'], a) for a in ('view', 'add', 'change')):
        if scoped_queryset(request.user, config['model']).filter(pk=notification.object_id).exists():
            if allowed(request.user, config['model'], 'change'):
                return redirect('content_manager:edit', slug=notification.section, pk=notification.object_id)
            return redirect('content_manager:list', slug=notification.section)
    return redirect('content_manager:dashboard')


@never_cache
@login_required
def notification_center(request):
    # Recipient-filtered: employees cannot read another employee's notifications.
    data = manager_context(request)
    status = request.GET.get('status', 'all')
    notifications = ContentNotification.objects.filter(recipient=request.user).select_related('actor')
    if status == 'unread':
        notifications = notifications.filter(is_read=False)
    elif status not in ('all', 'unread'):
        status = 'all'
    data.update(notification_records=notifications[:100], notification_status=status)
    return render(request, 'content_manager/notifications.html', data)


@never_cache
@login_required
@require_POST
def mark_all_notifications_read(request):
    updated = ContentNotification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, f'{updated} notification(s) marked as read.')
    return redirect('content_manager:notification_center')


@never_cache
@login_required
def approval_history(request, slug, pk):
    config = section_or_404(slug)
    model = config['model']
    if not any(allowed(request.user, model, action) for action in ('view', 'add', 'change')) and not can_approve(request.user, model):
        raise PermissionDenied('You cannot view this content.')
    record = get_scoped_object(request.user, model, pk)
    data = manager_context(request)
    data.update(config=config, slug=slug, record=record,
        audit_events=ContentAuditEvent.objects.filter(section=slug, object_id=pk).select_related('actor')[:200])
    return render(request, 'content_manager/approval_history.html', data)


@never_cache
@login_required
def approval_queue(request):
    """Cross-module queue, scoped to modules this reviewer may approve."""
    permitted = [(slug, config) for slug, config in SECTIONS.items()
                 if can_approve(request.user, config['model'])]
    if not permitted:
        raise PermissionDenied('You do not have approval permissions.')
    section = request.GET.get('section', 'all')
    if section not in ('all', *(slug for slug, _ in permitted)):
        raise Http404('Unknown or unauthorized approval section')
    status = request.GET.get('status', 'pending')
    if status not in ('pending', 'approved', 'rejected', 'all'):
        status = 'pending'
    query = request.GET.get('q', '').strip()[:100]
    rows = []
    counts = {'pending': 0, 'approved': 0, 'rejected': 0}
    for slug, config in permitted:
        model = config['model']
        base = scoped_queryset(request.user, model)
        for key in counts:
            counts[key] += base.filter(approval_status=key).count()
        if section != 'all' and section != slug:
            continue
        items = base.select_related('submitted_by', 'reviewed_by')
        if status != 'all':
            items = items.filter(approval_status=status)
        if query:
            items = items.filter(Q(title__icontains=query) | Q(summary__icontains=query))
        for obj in items.order_by('-updated_at')[:250]:
            rows.append({'slug': slug, 'section_title': config['title'], 'record': obj,
                         'submitted_by': obj.submitted_by, 'updated_at': obj.updated_at})
    rows.sort(key=lambda row: (row['updated_at'], row['record'].pk), reverse=True)
    page = Paginator(rows, 25).get_page(request.GET.get('page'))
    data = manager_context(request)
    data.update(queue_rows=page, queue_sections=permitted, selected_section=section,
                selected_status=status, query=query, queue_counts=counts)
    return render(request, 'content_manager/approval_queue.html', data)


@never_cache
@login_required
def approval_queue_export(request):
    """CSV export uses the same permission and policy-only scoping as the queue."""
    permitted = [(slug, config) for slug, config in SECTIONS.items()
                 if can_approve(request.user, config['model'])]
    if not permitted:
        raise PermissionDenied('You do not have approval permissions.')
    section = request.GET.get('section', 'all')
    if section not in ('all', *(slug for slug, _ in permitted)):
        raise Http404('Unknown or unauthorized approval section')
    status = request.GET.get('status', 'pending')
    if status not in ('pending', 'approved', 'rejected', 'all'):
        status = 'pending'
    query = request.GET.get('q', '').strip()[:100]
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="vishakha_approval_queue.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['Module', 'ID', 'Title', 'Status', 'Submitted By', 'Submitted At (IST)', 'Reviewed By', 'Reviewed At (IST)', 'Last Updated (IST)'])
    def safe(value):
        text = str(value or '')
        return "'" + text if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else text
    def local(value):
        return timezone.localtime(value).strftime('%Y-%m-%d %H:%M') if value else ''
    for slug, config in permitted:
        if section != 'all' and section != slug:
            continue
        qs = scoped_queryset(request.user, config['model']).select_related('submitted_by', 'reviewed_by')
        if status != 'all':
            qs = qs.filter(approval_status=status)
        if query:
            qs = qs.filter(Q(title__icontains=query) | Q(summary__icontains=query))
        for obj in qs.order_by('-updated_at')[:1000]:
            writer.writerow([config['title'], obj.pk, safe(obj.title), obj.get_approval_status_display(),
                             safe(obj.submitted_by.get_username() if obj.submitted_by else ''), local(obj.submitted_at),
                             safe(obj.reviewed_by.get_username() if obj.reviewed_by else ''), local(obj.reviewed_at), local(obj.updated_at)])
    return response


# Step 14: approver-only operational analytics. All queries use existing role-scoped
# models; no personal or cross-department data is exposed to unauthorized users.
def _analytics_data(request):
    permitted = [(slug, cfg) for slug, cfg in SECTIONS.items()
                 if can_approve(request.user, cfg['model'])]
    if not permitted:
        raise PermissionDenied('Only department approvers may view approval analytics.')
    section = request.GET.get('section', 'all')
    if section not in ('all', *(slug for slug, _ in permitted)):
        raise Http404('Unknown or unauthorized module')
    try:
        overdue_hours = int(request.GET.get('hours', '48'))
    except (TypeError, ValueError):
        overdue_hours = 48
    if overdue_hours not in (24, 48, 72):
        overdue_hours = 48
    now = timezone.now()
    cutoff = now - timedelta(hours=overdue_hours)
    rows = []
    overdue_rows = []
    total_pending = total_approved = total_rejected = total_draft = 0
    durations = []
    for slug, cfg in permitted:
        if section != 'all' and section != slug:
            continue
        qs = scoped_queryset(request.user, cfg['model'])
        counts = {key: qs.filter(approval_status=key).count()
                  for key in ('pending', 'approved', 'rejected', 'draft')}
        pending = qs.filter(approval_status='pending')
        overdue = pending.filter(submitted_at__isnull=False, submitted_at__lt=cutoff)
        # Records lacking a submission timestamp cannot be classified as overdue.
        overdue_count = overdue.count()
        module_durations = []
        for item in qs.filter(approval_status='approved', submitted_at__isnull=False,
                              reviewed_at__isnull=False).values('submitted_at','reviewed_at').iterator():
            seconds = (item['reviewed_at'] - item['submitted_at']).total_seconds()
            if seconds >= 0:
                module_durations.append(seconds / 3600)
        durations.extend(module_durations)
        rows.append({'slug':slug, 'name':cfg['title'], 'pending':counts['pending'],
                     'approved':counts['approved'], 'rejected':counts['rejected'],
                     'draft':counts['draft'], 'overdue':overdue_count,
                     'average_hours':round(mean(module_durations), 1) if module_durations else None,
                     'measured':len(module_durations)})
        for record in overdue.order_by('submitted_at')[:100]:
            overdue_rows.append({'slug':slug, 'module':cfg['title'], 'record':record,
                                 'hours_waiting':round((now-record.submitted_at).total_seconds()/3600,1)})
        total_pending += counts['pending']; total_approved += counts['approved']
        total_rejected += counts['rejected']; total_draft += counts['draft']
    overdue_rows.sort(key=lambda x:x['hours_waiting'], reverse=True)
    return {'analytics_modules':rows, 'overdue_rows':overdue_rows[:100],
            'selected_section':section, 'analytics_sections':permitted,
            'overdue_hours':overdue_hours,
            'analytics_totals':{'pending':total_pending, 'approved':total_approved,
                                'rejected':total_rejected, 'draft':total_draft,
                                'overdue':sum(r['overdue'] for r in rows),
                                'average_hours':round(mean(durations),1) if durations else None,
                                'measured':len(durations)}}


@never_cache
@login_required
def approval_analytics(request):
    data = manager_context(request)
    data.update(_analytics_data(request))
    return render(request, 'content_manager/approval_analytics.html', data)


@never_cache
@login_required
def approval_analytics_export(request):
    data = _analytics_data(request)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="vishakha_approval_analytics.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['Module','Pending','Approved','Changes Requested','Drafts',
                     f'Overdue (>{data["overdue_hours"]}h)', 'Average Review Hours', 'Measured Approvals'])
    def safe(value):
        value = str(value or '')
        return "'" + value if value.lstrip().startswith(('=','+','-','@','\t','\r')) else value
    for row in data['analytics_modules']:
        writer.writerow([safe(row['name']), row['pending'], row['approved'], row['rejected'],
                         row['draft'], row['overdue'], row['average_hours'] if row['average_hours'] is not None else '', row['measured']])
    return response
