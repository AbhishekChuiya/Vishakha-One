"""Values every employee page needs in its header/sidebar. Lazy: queries run only if the template uses them."""
from django.utils import timezone
from django.utils.functional import SimpleLazyObject

from contenthub.models import Announcement, AnnouncementReceipt
from portal.models import HelpfulLink


def _unread_count(user):
    notices = list(Announcement.objects.visible().filter(category="announcement").order_by("-published_at")[:30])
    if not notices:
        return 0
    seen = dict(AnnouncementReceipt.objects.filter(recipient=user, announcement__in=notices)
                .values_list("announcement_id", "seen_revision"))
    return sum(seen.get(n.pk) != n.updated_at for n in notices)


def _employee_id(user):
    profile = getattr(user, "employee_profile", None)
    return profile.employee_id if profile else ""


def _photo_url(user):
    profile = getattr(user, "employee_profile", None)
    try:
        return profile.photo.url if profile and profile.photo else ""
    except ValueError:
        return ""


def _bookmarked_ids(user):
    from contenthub.models import ResourceBookmark
    return set(ResourceBookmark.objects.filter(user=user).values_list("resource_id", flat=True))


def shell(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    can_manage = user.is_superuser or any(user.has_perm(p) for p in (
        "contenthub.add_announcement", "contenthub.add_resource", "contenthub.approve_announcement",
        "contenthub.approve_resource", "contenthub.manage_canteen_menu",
        "portal.change_companyapplication", "portal.change_helpfullink"))
    return {
        "shell_unread": SimpleLazyObject(lambda: _unread_count(user)),
        "shell_employee_id": SimpleLazyObject(lambda: _employee_id(user)),
        "shell_can_manage": can_manage,
        "shell_photo": SimpleLazyObject(lambda: _photo_url(user)),
        "shell_today": timezone.localdate(),
        "shell_bookmarks": SimpleLazyObject(lambda: _bookmarked_ids(user)),
        "shell_links": SimpleLazyObject(lambda: list(HelpfulLink.objects.filter(is_active=True))),
    }
