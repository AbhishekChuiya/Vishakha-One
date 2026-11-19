"""Browser push notifications (Web Push + VAPID).

Everything here is best-effort: a failed push must never break saving content or approving it.
"""
import json
import logging
import threading

from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone

logger = logging.getLogger("vone.push")

# Push services the browsers use. Subscriptions pointing anywhere else are refused (no server-side calls to arbitrary hosts).
ALLOWED_ENDPOINT_SUFFIXES = (
    ".googleapis.com", ".push.services.mozilla.com", ".push.apple.com",
    ".notify.windows.com", ".windows.com", ".mozilla.com",
)


def enabled():
    return bool(getattr(settings, "VONE_VAPID_PUBLIC_KEY", "") and getattr(settings, "VONE_VAPID_PRIVATE_KEY", ""))


def endpoint_allowed(endpoint):
    from urllib.parse import urlparse
    try:
        parts = urlparse(endpoint)
    except ValueError:
        return False
    host = (parts.hostname or "").lower()
    return parts.scheme == "https" and bool(host) and any(host.endswith(s) for s in ALLOWED_ENDPOINT_SUFFIXES)


def _deliver(subscription_ids, payload):
    """Send one payload to the given subscriptions. Runs in a worker thread (or inline when VONE_PUSH_SYNC)."""
    from .models import PushSubscription
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:  # library not installed on this machine
        logger.warning("Push skipped: pywebpush is not installed.")
        return 0
    sent = 0
    data = json.dumps(payload, ensure_ascii=False)
    for sub in PushSubscription.objects.filter(pk__in=subscription_ids):
        try:
            webpush(
                subscription_info={"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}},
                data=data,
                vapid_private_key=settings.VONE_VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VONE_VAPID_SUBJECT},
                ttl=60 * 60 * 24,
                timeout=10,
            )
            sub.last_success_at = timezone.now()
            sub.save(update_fields=["last_success_at"])
            sent += 1
        except WebPushException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (404, 410):          # the browser dropped this subscription
                sub.delete()
            else:
                logger.warning("Push failed for subscription %s: %s", sub.pk, exc)
        except Exception as exc:               # never let one bad device stop the rest
            logger.warning("Push error for subscription %s: %s", sub.pk, exc)
    return sent


def _run(subscription_ids, payload):
    if not subscription_ids:
        return
    if getattr(settings, "VONE_PUSH_SYNC", False):
        _deliver(subscription_ids, payload)
        return

    def worker():
        try:
            _deliver(subscription_ids, payload)
        finally:
            close_old_connections()
    threading.Thread(target=worker, name="vone-push", daemon=True).start()


def send_to_users(users, title, body, url="/", tag=""):
    """Push to every device of the given users."""
    if not enabled():
        return 0
    from .models import PushSubscription
    ids = list(PushSubscription.objects.filter(user__in=list(users), user__is_active=True).values_list("pk", flat=True))
    _run(ids, {"title": title[:120], "body": body[:240], "url": url, "tag": tag})
    return len(ids)


def send_to_everyone(title, body, url="/", tag=""):
    if not enabled():
        return 0
    from .models import PushSubscription
    ids = list(PushSubscription.objects.filter(user__is_active=True).values_list("pk", flat=True))
    _run(ids, {"title": title[:120], "body": body[:240], "url": url, "tag": tag})
    return len(ids)


def push_company_notice(announcement):
    """Tell every employee about a newly visible company notice - once only."""
    from contenthub.models import Announcement
    now = timezone.now()
    claimed = Announcement.objects.filter(pk=announcement.pk, push_sent_at__isnull=True).update(push_sent_at=now)
    announcement.push_sent_at = now          # keep the in-memory copy in step so a later save() cannot reset it
    if not claimed:
        return 0
    prefix = {"leadership": "Leadership message", "circular": "Circular", "news": "Company news"}.get(announcement.category)
    if announcement.category == "announcement" or prefix is None:
        prefix = {"urgent": "Urgent notice", "important": "Important notice"}.get(announcement.priority, "Company notice")
    elif announcement.priority in ("urgent", "important"):
        prefix = f"{announcement.get_priority_display()}: {prefix}"
    url = "/notifications/" if announcement.category == "announcement" else "/news/"
    return send_to_everyone(f"{prefix}: {announcement.title}", announcement.summary or announcement.body or "Tap to read it.",
                            url=url, tag=f"notice-{announcement.pk}")


def notice_is_due(a, now=None):
    now = now or timezone.now()
    """Company news, leadership messages and circulars always notify; a plain announcement only when it is
    marked Important or Urgent."""
    wanted = a.category in ("news", "leadership", "circular") or (a.category == "announcement" and a.priority in ("important", "urgent"))
    return (wanted and a.is_published and a.approval_status == "approved" and not a.is_archived
            and a.published_at <= now and (a.expires_at is None or a.expires_at > now) and a.push_sent_at is None)


def send_due_notices():
    """For scheduled notices whose time has come (run by cron through a management command)."""
    from contenthub.models import Announcement
    total = 0
    for a in Announcement.objects.filter(category__in=Announcement.PUSH_CATEGORIES, is_published=True, approval_status="approved", push_sent_at__isnull=True):
        if notice_is_due(a):
            total += 1 if push_company_notice(a) else 0
    return total
