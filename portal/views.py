from django.db.models import Q
from django.http import Http404
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import CompanyApplication
from contenthub.models import Announcement, Resource, JobOpening, NewJoiner, Event

NAV = [
    ('home', 'Home', '⌂'), ('apps', 'My Apps', '▦'),
    ('news', 'News & Events', '▤'), ('policies', 'Policies', '▧'),
    ('documents', 'Documents', '▣'), ('careers', 'Careers', '▥'),
    ('joiners', 'New Joiners', '♧'), ('services', 'Employee Services', '⚙'),
    ('help', 'Help', '?'),
]


def context():
    return {
        'nav': [{'slug': s, 'label': label, 'icon': icon} for s, label, icon in NAV],
        'apps': CompanyApplication.objects.filter(is_active=True),
    }


def home(request):
    data = context()
    data.update(
        section='home', heading='Home',
        announcements=Announcement.objects.visible().exclude(category='gallery')[:4],
        recognitions=Announcement.objects.visible().filter(category='recognition')[:6],
        portal_notices=Announcement.objects.visible().filter(category='announcement').order_by('-published_at', '-pk')[:30],
        featured_policies=Resource.objects.visible().filter(kind='policy')[:3],
        gallery_photos=(list(Announcement.objects.visible().filter(category='gallery').exclude(image='').order_by('-published_at')[:8]) or
                        (list(Event.objects.visible().exclude(image='').order_by('-published_at')[:8]) +
                         list(Announcement.objects.visible().exclude(image='').order_by('-published_at')[:8]))[:8]),
        homepage_brochures=Resource.objects.visible().filter(kind='brochure')[:6],
        homepage_insiders=Resource.objects.visible().filter(kind='insider')[:20],
        homepage_bank_benefits=Resource.objects.visible().filter(kind='bank_benefit')[:20],
        homepage_canteen=Resource.objects.visible().filter(kind='canteen_menu').first(),
        homepage_videos=Resource.objects.visible().filter(kind='video')[:12],
        csr_cover=Resource.objects.visible().filter(kind='csr_cover').exclude(cover_image='').first(),
        new_joiners=NewJoiner.objects.visible()[:12],
        upcoming_events=Event.objects.visible().filter(starts_at__gte=timezone.now()).order_by('starts_at')[:3],
        jobs=JobOpening.objects.visible().filter(Q(deadline__isnull=True) | Q(deadline__gte=timezone.localdate()))[:3],
    )
    return render(request, 'portal/home.html', data)


def section(request, slug):
    if slug == 'home':
        return home(request)
    labels = {s: label for s, label, _ in NAV}
    if slug not in labels:
        raise Http404('Unknown page')
    data = context()
    data.update(section=slug, heading=labels[slug], subtitle='Your Vishakha One workspace')
    q = request.GET.get('q', '').strip()[:120]
    category = request.GET.get('category', 'all').strip()[:40]
    data['selected_category'] = category
    data['query'] = q
    if slug == 'apps':
        if q:
            data['apps'] = data['apps'].filter(Q(name__icontains=q) | Q(category__icontains=q))
    elif slug == 'news':
        data['items'] = Announcement.objects.visible()
        data['events'] = Event.objects.visible().filter(starts_at__gte=timezone.now()).order_by('starts_at')
        if category in ('news', 'announcement', 'recognition', 'gallery'):
            data['items'] = data['items'].filter(category=category)
        if q:
            data['items'] = data['items'].filter(Q(title__icontains=q) | Q(summary__icontains=q))
    elif slug in ('policies', 'documents'):
        data['items'] = Resource.objects.visible().filter(kind='policy' if slug == 'policies' else 'document')
        if slug == 'documents':
            data['items'] = Resource.objects.visible().filter(kind__in=['document', 'brochure', 'insider', 'bank_benefit', 'canteen_menu', 'video'])
        if category in ('policy', 'document', 'brochure', 'insider', 'bank_benefit', 'canteen_menu', 'video'):
            data['items'] = data['items'].filter(kind=category)
        if q:
            data['items'] = data['items'].filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(department__icontains=q))
    elif slug == 'careers':
        data['items'] = JobOpening.objects.visible().filter(Q(deadline__isnull=True) | Q(deadline__gte=timezone.localdate()))
        if q:
            data['items'] = data['items'].filter(Q(title__icontains=q) | Q(department__icontains=q) | Q(location__icontains=q))
    elif slug == 'joiners':
        all_joiners = NewJoiner.objects.visible()
        department = request.GET.get('department', '').strip()[:120]
        location = request.GET.get('location', '').strip()[:120]
        departments = list(all_joiners.exclude(department='').order_by('department').values_list('department', flat=True).distinct())
        locations = list(all_joiners.exclude(location='').order_by('location').values_list('location', flat=True).distinct())
        if department and department in departments:
            all_joiners = all_joiners.filter(department=department)
        else:
            department = ''
        if location and location in locations:
            all_joiners = all_joiners.filter(location=location)
        else:
            location = ''
        if q:
            all_joiners = all_joiners.filter(
                Q(employee_name__icontains=q) | Q(department__icontains=q)
                | Q(designation__icontains=q) | Q(location__icontains=q)
            )
        data.update(items=all_joiners.order_by('-joining_date', 'employee_name')[:150],
                    departments=departments, locations=locations,
                    selected_department=department, selected_location=location)
        return render(request, 'portal/joiners_directory.html', data)
    return render(request, 'portal/section.html', data)


def profile(request):
    """Read-only profile: display authenticated Django user fields only."""
    data = context()
    data.update(section='profile', heading='My Profile', subtitle='Your employee workspace')
    user = request.user
    data['profile_signed_in'] = bool(user.is_authenticated)
    if user.is_authenticated:
        name = user.get_full_name().strip() if callable(getattr(user, 'get_full_name', None)) else ''
        data['profile_name'] = name or user.get_username()
        data['profile_email'] = getattr(user, 'email', '') or ''
        data['profile_username'] = user.get_username()
        data['profile_joined'] = getattr(user, 'date_joined', None)
    return render(request, 'portal/profile.html', data)


def search(request):
    """Employee-visible unified search; no drafts or unpublished content."""
    query = request.GET.get('q', '').strip()[:120]
    scope = request.GET.get('type', 'all')
    allowed = {'all', 'apps', 'policies', 'documents', 'news', 'joiners'}
    if scope not in allowed:
        scope = 'all'
    data = context()
    data.update(section='search', heading='Search Vishakha One', query=query,
                selected_type=scope, search_groups=[])
    if len(query) < 2:
        return render(request, 'portal/search.html', data)
    groups = []
    if scope in ('all', 'apps'):
        qs = CompanyApplication.objects.filter(is_active=True).filter(
            Q(name__icontains=query) | Q(description__icontains=query) | Q(category__icontains=query))[:25]
        groups.append(('Applications', 'apps', [(o.name, o.description, o.url or '/apps/') for o in qs]))
    if scope in ('all', 'policies', 'documents'):
        qs = Resource.objects.visible().filter(
            Q(title__icontains=query) | Q(summary__icontains=query) | Q(department__icontains=query))
        if scope == 'policies':
            qs = qs.filter(kind='policy')
        elif scope == 'documents':
            qs = qs.exclude(kind='policy')
        for label, kind in [('Policies', 'policies'), ('Documents & Resources', 'documents')]:
            if scope != 'all' and scope != kind:
                continue
            subset = qs.filter(kind='policy') if kind == 'policies' else qs.exclude(kind='policy')
            groups.append((label, kind, [(o.title, o.summary, o.access_url or ('/'+kind+'/'),) for o in subset[:25]]))
    if scope in ('all', 'news'):
        qs = Announcement.objects.visible().filter(Q(title__icontains=query) | Q(summary__icontains=query))[:25]
        groups.append(('News & Announcements', 'news', [(o.title, o.summary, '/news/') for o in qs]))
    if scope in ('all', 'joiners'):
        qs = NewJoiner.objects.visible().filter(Q(employee_name__icontains=query) | Q(department__icontains=query) | Q(designation__icontains=query))[:25]
        groups.append(('New Joiners', 'joiners', [(o.employee_name, (o.designation or '') + ' · ' + (o.department or ''), '/joiners/') for o in qs]))
    data['search_groups'] = groups
    data['result_count'] = sum(len(items) for _, _, items in groups)
    return render(request, 'portal/search.html', data)


@login_required
def notifications(request):
    """Employee-facing published announcements with optional unread filter."""
    data = context()
    notices = list(Announcement.objects.visible().filter(category='announcement')
                   .order_by('-published_at', '-pk')[:100])
    receipts = AnnouncementReceipt.objects.filter(
        recipient=request.user, announcement__in=notices
    ).values_list('announcement_id', 'seen_revision')
    seen = dict(receipts)
    for item in notices:
        item.employee_read = seen.get(item.pk) == item.updated_at
    unread_count = sum(not item.employee_read for item in notices)
    selected_filter = request.GET.get('filter', 'all')
    if selected_filter not in ('all', 'unread'):
        selected_filter = 'all'
    data.update(section='notifications', heading='Company Notifications',
                portal_notices=[n for n in notices if not n.employee_read]
                if selected_filter == 'unread' else notices,
                selected_notification_filter=selected_filter,
                notification_unread_count=unread_count,
                notification_total_count=len(notices))
    return render(request, 'portal/notifications.html', data)


from django.views.decorators.http import require_GET, require_POST
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from contenthub.models import AnnouncementReceipt

@login_required
@require_GET
def announcement_notification_feed(request):
    """Unread published announcements, scoped to the logged-in employee."""
    notices = list(Announcement.objects.visible().filter(category='announcement').order_by('-published_at')[:30])
    read = dict(AnnouncementReceipt.objects.filter(recipient=request.user, announcement__in=notices).values_list('announcement_id', 'seen_revision'))
    unread = [n for n in notices if read.get(n.pk) != n.updated_at]
    return JsonResponse({'unread_count':len(unread), 'items':[{'id':n.pk, 'title':n.title, 'summary':n.summary or '', 'event_at':timezone.localtime(n.event_at).strftime('%d %b %Y, %I:%M %p') if n.event_at else '', 'location':n.event_location or '', 'published_at':timezone.localtime(n.published_at).strftime('%d %b %Y') if n.published_at else ''} for n in unread[:8]]})

@login_required
@require_POST
def mark_announcement_read(request, pk):
    notice = get_object_or_404(Announcement.objects.visible().filter(category='announcement'), pk=pk)
    AnnouncementReceipt.objects.update_or_create(recipient=request.user, announcement=notice, defaults={'seen_revision':notice.updated_at})
    return redirect('portal:notifications')


@login_required
@require_POST
def mark_all_announcements_read(request):
    """Mark the latest 100 visible announcements as read for this employee."""
    notices = list(Announcement.objects.visible().filter(category='announcement')
                   .order_by('-published_at', '-pk')[:100])
    from django.db import transaction
    with transaction.atomic():
        for notice in notices:
            AnnouncementReceipt.objects.update_or_create(
                recipient=request.user, announcement=notice,
                defaults={'seen_revision': notice.updated_at})
    return redirect('portal:notifications')
