"""Tiny per-key rate limiter (Django cache). Used to stop mail-bombing one employee."""
import hashlib

from django.core.cache import cache


def allow(action, key, limit=5, window=3600):
    """Return True while `key` has made <= `limit` attempts for `action` in `window` seconds."""
    digest = hashlib.sha256((key or "").strip().lower().encode("utf-8")).hexdigest()
    cache_key = f"vone:throttle:{action}:{digest}"
    cache.add(cache_key, 0, window)
    try:
        count = cache.incr(cache_key)
    except ValueError:  # expired between add() and incr()
        cache.set(cache_key, 1, window)
        count = 1
    return count <= limit
