"""Read-only overview for company announcements. Uses existing Content Manager permissions."""
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from .models import Announcement
from .manager_views import allowed, manager_context


@never_cache
@login_required
def announcement_overview(request):
    if not any(allowed(request.user, Announcement, action) for action in ('view', 'add', 'change')):
        raise PermissionDenied('You do not have access to announcements.')
    now = timezone.now()
    qs = Announcement.objects.filter(category='announcement')
    live = Q(is_published=True, approval_status='approved', published_at__lte=now)
    active = live & (Q(expires_at__isnull=True) | Q(expires_at__gt=now))
    expired = live & Q(expires_at__lte=now)
    scheduled = Q(is_published=True, approval_status='approved', published_at__gt=now)
    unpublished = Q(is_published=False) | ~Q(approval_status='approved')
    status = request.GET.get('status', 'active')
    options = {
        'active': active, 'scheduled': scheduled, 'expired': expired,
        'unpublished': unpublished,
    }
    if status not in options:
        status = 'active'
    selected = qs.filter(options[status]).order_by('-updated_at')[:200]
    data = manager_context(request)
    data.update({
        'status': status,
        'items': selected,
        'counts': {name: qs.filter(rule).count() for name, rule in options.items()},
        'total_count': qs.count(),
        'now': now,
        'section_title': 'Announcement Status',
    })
    return render(request, 'content_manager/announcement_overview.html', data)
