import json

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from . import push
from .models import PushSubscription


@never_cache
@require_GET
def push_key(request):
    return JsonResponse({"enabled": push.enabled(), "publicKey": settings.VONE_VAPID_PUBLIC_KEY if push.enabled() else ""})


def _body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return None


@require_POST
def push_subscribe(request):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False}, status=401)
    if not push.enabled():
        return JsonResponse({"ok": False, "error": "disabled"}, status=503)
    data = _body(request)
    sub = (data or {}).get("subscription") or {}
    endpoint = str(sub.get("endpoint") or "")
    keys = sub.get("keys") or {}
    p256dh, auth = str(keys.get("p256dh") or ""), str(keys.get("auth") or "")
    if not (endpoint and p256dh and auth) or len(endpoint) > 600 or len(p256dh) > 200 or len(auth) > 100 or not push.endpoint_allowed(endpoint):
        return JsonResponse({"ok": False, "error": "invalid"}, status=400)
    # One browser belongs to whoever is signed in on it now.
    PushSubscription.objects.update_or_create(
        endpoint=endpoint, defaults={"user": request.user, "p256dh": p256dh, "auth": auth,
                                     "user_agent": request.META.get("HTTP_USER_AGENT", "")[:300]})
    return JsonResponse({"ok": True})


@require_POST
def push_unsubscribe(request):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": True})
    data = _body(request) or {}
    endpoint = str(data.get("endpoint") or "")
    PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
    return JsonResponse({"ok": True})
