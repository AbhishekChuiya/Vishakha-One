from django.db.models import Q, Case, When, Value, IntegerField
from django.http import Http404
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import CompanyApplication
from contenthub.models import Announcement, Resource, JobOpening, NewJoiner, Event, AnnouncementReceipt, CanteenDay, DailyThought, ResourceBookmark
from employees.models import EmployeeProfile

NAV = [
    ('home', 'Home', '⌂'), ('apps', 'My Apps', '▦'),
    ('news', 'News & Events', '▤'), ('policies', 'Policies', '▧'),
    ('documents', 'Documents', '▣'), ('videos', 'Video Library', '▶'), ('collateral', 'Brochures & Brand', '▤'), ('careers', 'Careers', '▥'),
    ('joiners', 'New Joiners', '♧'), ('services', 'Employee Services', '⚙'),
    ('help', 'Help', '?'),
]


def by_priority(qs):
    """Urgent first, then important, then the rest; newest first inside each group."""
    return qs.annotate(_prio=Case(When(priority='urgent', then=Value(0)), When(priority='important', then=Value(1)),
                                  default=Value(2), output_field=IntegerField())).order_by('_prio', '-published_at', '-pk')


def context():
    return {
        'nav': [{'slug': s, 'label': label, 'icon': icon} for s, label, icon in NAV],
        'apps': CompanyApplication.objects.filter(is_active=True),
    }


def _thought_for_today():
    today = timezone.localdate()
    item = DailyThought.objects.visible().filter(show_on__lte=today).order_by('-show_on', '-published_at').first()
    if item and (today - item.show_on).days > 7:        # a stale thought is worse than none
        return None
    return item


def home(request):
    from datetime import timedelta
    data = context()
    now = timezone.localdate()
    monday = now - timedelta(days=now.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(6)]
    menus = {item.date: item for item in CanteenDay.objects.filter(date__in=week_dates)}
    data['homepage_canteen_days'] = [
        {'date': day, 'menu': menus.get(day), 'is_today': day == now}
        for day in week_dates
    ]
    notices = list(Announcement.objects.visible().filter(category='announcement').order_by('-published_at', '-pk')[:30])
    if request.user.is_authenticated:
        read = dict(AnnouncementReceipt.objects.filter(
            recipient=request.user, announcement__in=notices
        ).values_list('announcement_id', 'seen_revision'))
        notices = [notice for notice in notices if read.get(notice.pk) != notice.updated_at]
    else:
        # Public homepage: anonymous visitors can dismiss notices for their session.
        dismissed = set(request.session.get('vone_dismissed_notices', []))
        notices = [notice for notice in notices if f'{notice.pk}:{notice.updated_at.isoformat()}' not in dismissed]
    data.update(
        section='home', heading='Home',
        announcements=by_priority(Announcement.objects.visible().exclude(category='gallery'))[:4],
        thought=_thought_for_today(),
        recognitions=Announcement.objects.visible().filter(category='recognition')[:6],
        portal_notices=notices,
        featured_policies=Resource.objects.visible().filter(kind='policy')[:3],
        gallery_photos=(list(Announcement.objects.visible().filter(category='gallery').exclude(image='').order_by('-published_at')[:8]) or
                        (list(Event.objects.visible().exclude(image='').order_by('-published_at')[:8]) +
                         list(Announcement.objects.visible().exclude(image='').order_by('-published_at')[:8]))[:8]),
        homepage_brochures=Resource.objects.visible().filter(kind='brochure')[:6],
        homepage_insiders=Resource.objects.visible().filter(kind='insider')[:20],
        homepage_bank_benefits=Resource.objects.visible().filter(kind='bank_benefit')[:20],
        homepage_canteen=Resource.objects.visible().filter(kind='canteen_menu').first(),
        homepage_videos=Resource.objects.visible().filter(kind__in=Resource.VIDEO_KINDS)[:12],
        csr_cover=Resource.objects.visible().filter(kind='csr_cover').exclude(cover_image='').first(),
        new_joiners=NewJoiner.objects.visible()[:12],
        upcoming_events=Event.objects.visible().filter(starts_at__gte=timezone.now()).order_by('starts_at')[:3],
        today_menu=menus.get(now),
        upcoming_count=Event.objects.visible().filter(starts_at__gte=timezone.now()).count(),
        joiners_count=NewJoiner.objects.visible().count(),
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
        data['app_categories'] = sorted({a.category for a in data['apps'] if a.category}, key=str.lower)
        if category and category != 'all':
            data['apps'] = data['apps'].filter(category__iexact=category)
        if q:
            data['apps'] = data['apps'].filter(Q(name__icontains=q) | Q(category__icontains=q))
    elif slug == 'news':
        data['items'] = by_priority(Announcement.objects.visible())
        data['events'] = Event.objects.visible().filter(starts_at__gte=timezone.now()).order_by('starts_at')
        if category in ('news', 'announcement', 'leadership', 'circular', 'recognition', 'gallery'):
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
    elif slug == 'videos':
        data['video_kinds'] = [(k, l) for k, l in Resource.KIND_CHOICES if k in Resource.VIDEO_KINDS]
        data['items'] = Resource.objects.visible().filter(kind__in=Resource.VIDEO_KINDS)
        if category in Resource.VIDEO_KINDS:
            data['items'] = data['items'].filter(kind=category)
        if q:
            data['items'] = data['items'].filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(department__icontains=q))
    elif slug == 'collateral':
        data['collateral_kinds'] = [(k, l) for k, l in Resource.KIND_CHOICES if k in Resource.COLLATERAL_KINDS]
        data['items'] = Resource.objects.visible().filter(kind__in=Resource.COLLATERAL_KINDS)
        if category in Resource.COLLATERAL_KINDS:
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
    """My profile: shows account details and lets the employee change name, photo and password."""
    from django.contrib import messages
    from django.contrib.auth import update_session_auth_hash
    from django.contrib.auth.forms import PasswordChangeForm
    from django.shortcuts import redirect
    from .profile_forms import NameForm, PhotoForm
    from .names import display_name

    user = request.user
    if not user.is_authenticated:
        return redirect('accounts:login')
    employee_profile = EmployeeProfile.objects.filter(user=user).first()
    name_form = NameForm(initial={'first_name': user.first_name, 'last_name': user.last_name})
    photo_form = PhotoForm()
    password_form = PasswordChangeForm(user)
    open_panel = ''
    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'name':
            name_form = NameForm(request.POST)
            if name_form.is_valid():
                user.first_name = name_form.cleaned_data['first_name']
                user.last_name = name_form.cleaned_data['last_name']
                user.save(update_fields=['first_name', 'last_name'])
                messages.success(request, 'Your name has been updated.')
                return redirect('portal:profile')
            open_panel = 'name'
        elif action == 'photo' and employee_profile:
            photo_form = PhotoForm(request.POST, request.FILES)
            if photo_form.is_valid():
                if employee_profile.photo:
                    employee_profile.photo.delete(save=False)
                employee_profile.photo.save('photo.jpg', photo_form.processed(), save=True)
                messages.success(request, 'Your photo has been updated.')
                return redirect('portal:profile')
            open_panel = 'photo'
        elif action == 'remove_photo' and employee_profile:
            if employee_profile.photo:
                employee_profile.photo.delete(save=False)
                employee_profile.photo = None
                employee_profile.save(update_fields=['photo'])
            messages.success(request, 'Your photo has been removed.')
            return redirect('portal:profile')
        elif action == 'password':
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, password_form.user)
                messages.success(request, 'Your password has been changed.')
                return redirect('portal:profile')
            open_panel = 'password'
    data = context()
    data.update(section='profile', heading='My Profile', subtitle='Your employee workspace',
                profile_signed_in=True, profile_name=display_name(user),
                profile_email=getattr(user, 'email', '') or '',
                profile_username=user.get_username(),
                profile_employee_id=employee_profile.employee_id if employee_profile else '',
                profile_joined=getattr(user, 'date_joined', None),
                profile_photo=(employee_profile.photo.url if employee_profile and employee_profile.photo else ''),
                can_set_photo=bool(employee_profile),
                name_form=name_form, photo_form=photo_form, password_form=password_form,
                open_panel=open_panel)
    return render(request, 'portal/profile.html', data)


def search(request):
    """Employee-visible unified search; no drafts or unpublished content. Tolerates typos."""
    from . import fuzzy
    query = request.GET.get('q', '').strip()[:120]
    scope = request.GET.get('type', 'all')
    allowed = {'all', 'apps', 'policies', 'documents', 'news', 'joiners'}
    if scope not in allowed:
        scope = 'all'
    data = context()
    data.update(section='search', heading='Search Vishakha One', query=query,
                selected_type=scope, search_groups=[], did_you_mean='',
                search_scopes=[('all', 'Everything'), ('apps', 'Applications'), ('policies', 'Policies'), ('documents', 'Documents'), ('news', 'News'), ('joiners', 'People')])
    if len(query) < 2:
        return render(request, 'portal/search.html', data)
    CAP = 2000  # candidates per content type; the portal's content is far smaller than this
    suggestions = []
    groups = []
    if scope in ('all', 'apps'):
        apps, sug = fuzzy.rank(query, CompanyApplication.objects.filter(is_active=True)[:CAP],
                               [('name', 1.0), ('description', 0.5), ('category', 0.5)])
        suggestions.append(sug)
        groups.append(('Applications', 'apps', [(o.name, o.description, o.url or '/apps/') for o in apps]))
    if scope in ('all', 'policies', 'documents'):
        qs = Resource.objects.visible()
        if scope == 'policies':
            qs = qs.filter(kind='policy')
        elif scope == 'documents':
            qs = qs.exclude(kind='policy')
        pool = list(qs[:CAP])
        for label, kind in [('Policies', 'policies'), ('Documents & Resources', 'documents')]:
            if scope != 'all' and scope != kind:
                continue
            subset = [o for o in pool if (o.kind == 'policy') == (kind == 'policies')]
            found, sug = fuzzy.rank(query, subset, [('title', 1.0), ('summary', 0.5), ('department', 0.5)])
            suggestions.append(sug)
            groups.append((label, kind, [(o.title, o.summary, o.access_url or ('/' + kind + '/'),) for o in found]))
    if scope in ('all', 'news'):
        news, sug = fuzzy.rank(query, Announcement.objects.visible()[:CAP], [('title', 1.0), ('summary', 0.5)])
        suggestions.append(sug)
        groups.append(('News & Announcements', 'news', [(o.title, o.summary, '/news/') for o in news]))
    if scope in ('all', 'joiners'):
        people, sug = fuzzy.rank(query, NewJoiner.objects.visible()[:CAP],
                                 [('employee_name', 1.0), ('department', 0.5), ('designation', 0.5)])
        suggestions.append(sug)
        groups.append(('New Joiners', 'joiners', [(o.employee_name, (o.designation or '') + ' \u00b7 ' + (o.department or ''), '/joiners/') for o in people]))
    data['search_scopes'] = [('all', 'Everything'), ('apps', 'Applications'), ('policies', 'Policies'), ('documents', 'Documents'), ('news', 'News'), ('joiners', 'People')]
    data['search_groups'] = groups
    data['result_count'] = sum(len(items) for _, _, items in groups)
    data['did_you_mean'] = next((s for s in suggestions if s), '')
    return render(request, 'portal/search.html', data)


def search_suggest(request):
    """Live suggestions for the header search: a few best matches per kind, typo tolerant."""
    from django.http import JsonResponse
    from . import fuzzy
    from .templatetags.vone_ui import _ICONS
    query = request.GET.get('q', '').strip()[:120]
    if len(query) < 2:
        return JsonResponse({'groups': []})
    pages = [
        ('Home', '/', 'home', 'Your dashboard'), ('My Apps', '/apps/', 'grid', 'Application directory'),
        ('News & Events', '/news/', 'news', 'Company news, announcements and events'),
        ('Policies', '/policies/', 'file', 'Company policies'), ('Documents', '/documents/', 'folder', 'Documents, brochures and videos'),
        ('Careers', '/careers/', 'briefcase', 'Internal job openings'), ('New Joiners', '/joiners/', 'users', 'Meet new colleagues'),
        ('Canteen Menu', '/canteen-menu/', 'utensils', 'Weekly lunch and snacks'), ('Employee Services', '/services/', 'sliders', 'Employee services'),
        ('Help', '/help/', 'lifebuoy', 'Help and support'), ('My profile', '/profile/', 'user', 'Your account details'),
        ('Notifications', '/notifications/', 'bell', 'Company notifications'),
    ]
    rows = [{'title': t, 'url': u, 'icon': i, 'sub': d} for t, u, i, d in pages]
    groups = []

    def add(title, items):
        if items:
            groups.append({'title': title, 'items': items})

    found, _ = fuzzy.rank(query, rows, [('title', 1.0), ('sub', 0.4)], limit=3)
    add('Pages', [{'title': r['title'], 'sub': r['sub'], 'url': r['url'], 'icon': _ICONS[r['icon']]} for r in found])
    apps, _ = fuzzy.rank(query, CompanyApplication.objects.filter(is_active=True)[:500],
                         [('name', 1.0), ('description', 0.5), ('category', 0.5)], limit=4)
    add('Applications', [{'title': a.name, 'sub': a.category or a.description, 'url': a.url or '/apps/', 'icon': _ICONS['grid']} for a in apps])
    docs, _ = fuzzy.rank(query, Resource.objects.visible()[:1000], [('title', 1.0), ('summary', 0.5), ('department', 0.5)], limit=3)
    add('Policies & documents', [{'title': d.title, 'sub': d.get_kind_display(), 'url': d.access_url or ('/policies/' if d.kind == 'policy' else '/documents/'),
                                  'icon': _ICONS['file']} for d in docs])
    news, _ = fuzzy.rank(query, Announcement.objects.visible()[:1000], [('title', 1.0), ('summary', 0.5)], limit=3)
    add('News', [{'title': n.title, 'sub': n.get_category_display(), 'url': '/news/', 'icon': _ICONS['news']} for n in news])
    people, _ = fuzzy.rank(query, NewJoiner.objects.visible()[:1000], [('employee_name', 1.0), ('department', 0.5), ('designation', 0.5)], limit=3)
    add('People', [{'title': p.employee_name, 'sub': ' · '.join(x for x in (p.designation, p.department) if x), 'url': '/joiners/', 'icon': _ICONS['users']} for p in people])
    return JsonResponse({'groups': groups})


def notifications(request):
    """Employee-facing published announcements with optional unread filter."""
    data = context()
    notices = list(Announcement.objects.visible().filter(category='announcement')
                   .order_by('-published_at', '-pk')[:100])
    if request.user.is_authenticated:
        seen = dict(AnnouncementReceipt.objects.filter(
            recipient=request.user, announcement__in=notices
        ).values_list('announcement_id', 'seen_revision'))
    else:
        dismissed = set(request.session.get('vone_dismissed_notices', []))
        seen = {n.pk: n.updated_at for n in notices
                if f'{n.pk}:{n.updated_at.isoformat()}' in dismissed}
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

@require_GET
def announcement_notification_feed(request):
    """Unread published announcements, scoped to the logged-in employee."""
    notices = list(Announcement.objects.visible().filter(category='announcement').order_by('-published_at')[:30])
    if request.user.is_authenticated:
        read = dict(AnnouncementReceipt.objects.filter(
            recipient=request.user, announcement__in=notices
        ).values_list('announcement_id', 'seen_revision'))
    else:
        dismissed = set(request.session.get('vone_dismissed_notices', []))
        read = {n.pk: n.updated_at for n in notices
                if f'{n.pk}:{n.updated_at.isoformat()}' in dismissed}
    unread = [n for n in notices if read.get(n.pk) != n.updated_at]
    return JsonResponse({'unread_count':len(unread), 'items':[{'id':n.pk, 'title':n.title, 'summary':n.summary or '', 'event_at':timezone.localtime(n.event_at).strftime('%d %b %Y, %I:%M %p') if n.event_at else '', 'location':n.event_location or '', 'published_at':timezone.localtime(n.published_at).strftime('%d %b %Y') if n.published_at else ''} for n in unread[:8]]})

@require_POST
def mark_announcement_read(request, pk):
    notice = get_object_or_404(Announcement.objects.visible().filter(category='announcement'), pk=pk)
    if request.user.is_authenticated:
        AnnouncementReceipt.objects.update_or_create(
            recipient=request.user, announcement=notice,
            defaults={'seen_revision': notice.updated_at})
    else:
        # Anonymous homepage visitors have no employee identity: session only.
        key = f'{notice.pk}:{notice.updated_at.isoformat()}'
        dismissed = list(request.session.get('vone_dismissed_notices', []))
        if key not in dismissed:
            dismissed.append(key)
        request.session['vone_dismissed_notices'] = dismissed[-100:]
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'id': notice.pk})
    return redirect('portal:home' if request.POST.get('next') == 'home' else 'portal:notifications')


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


def bookmarks(request):
    """My bookmarks: the documents, videos and brochures this employee saved."""
    ids = list(ResourceBookmark.objects.filter(user=request.user).values_list('resource_id', flat=True))
    items = list(Resource.objects.visible().filter(pk__in=ids))
    order = {pk: i for i, pk in enumerate(ids)}
    items.sort(key=lambda r: order.get(r.pk, 0))
    data = context()
    data.update(section='bookmarks', heading='My Bookmarks', items=items)
    return render(request, 'portal/bookmarks.html', data)


@require_POST
def bookmark_toggle(request, pk):
    resource = get_object_or_404(Resource.objects.visible(), pk=pk)
    obj, created = ResourceBookmark.objects.get_or_create(user=request.user, resource=resource)
    if not created:
        obj.delete()
    return JsonResponse({'ok': True, 'bookmarked': created})
