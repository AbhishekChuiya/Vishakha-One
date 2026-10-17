from django.db.models import Q
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone
from .models import CompanyApplication
from contenthub.models import Announcement, Resource, JobOpening, NewJoiner, Event

NAV = [
    ('home', 'Home', '⌂'), ('apps', 'My Apps', '▦'),
    ('news', 'News & Events', '▤'), ('policies', 'Policies', '▧'),
    ('documents', 'Documents', '▣'), ('careers', 'Careers', '▥'),
    ('joiners', 'New Joiners', '👥'), ('services', 'Employee Services', '⚙'),
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
        announcements=Announcement.objects.visible()[:4],
        featured_policies=Resource.objects.visible().filter(kind='policy')[:3],
        new_joiners=NewJoiner.objects.visible()[:4],
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
    data['query'] = q
    if slug == 'apps':
        if q:
            data['apps'] = data['apps'].filter(Q(name__icontains=q) | Q(category__icontains=q))
    elif slug == 'news':
        data['items'] = Announcement.objects.visible()
        data['events'] = Event.objects.visible().filter(starts_at__gte=timezone.now()).order_by('starts_at')
        if q:
            data['items'] = data['items'].filter(Q(title__icontains=q) | Q(summary__icontains=q))
    elif slug in ('policies', 'documents'):
        data['items'] = Resource.objects.visible().filter(kind='policy' if slug == 'policies' else 'document')
        if slug == 'documents':
            data['items'] = Resource.objects.visible().filter(kind__in=['document', 'brochure'])
        if q:
            data['items'] = data['items'].filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(department__icontains=q))
    elif slug == 'careers':
        data['items'] = JobOpening.objects.visible().filter(Q(deadline__isnull=True) | Q(deadline__gte=timezone.localdate()))
        if q:
            data['items'] = data['items'].filter(Q(title__icontains=q) | Q(department__icontains=q) | Q(location__icontains=q))
    elif slug == 'joiners':
        data['items'] = NewJoiner.objects.visible()
        if q:
            data['items'] = data['items'].filter(Q(employee_name__icontains=q) | Q(department__icontains=q))
    return render(request, 'portal/section.html', data)
