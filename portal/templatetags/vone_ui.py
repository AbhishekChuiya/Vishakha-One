"""Small helpers for the employee portal templates: inline icons, greeting, initials, app colours."""
from django import template
from django.utils import timezone
from django.utils.translation import gettext
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from portal import names

register = template.Library()

# Line icons (24x24, drawn with currentColor strokes). Inline so no extra request and no web font.
_ICONS = {
    "bookmark": '<path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3z"/>',
    "list": '<path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01"/>',
    "pencil": '<path d="M4 20l4-1 11-11a2.1 2.1 0 0 0-3-3L5 16l-1 4z"/><path d="M14 7l3 3"/>',
    "arrow-up": '<path d="M12 19V5M6 11l6-6 6 6"/>',
    "chevron-right": '<path d="M9 6l6 6-6 6"/>',
    "chart": '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    "home": '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h5v-6h4v6h5V10"/>',
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1.6"/><rect x="14" y="3" width="7" height="7" rx="1.6"/><rect x="3" y="14" width="7" height="7" rx="1.6"/><rect x="14" y="14" width="7" height="7" rx="1.6"/>',
    "news": '<path d="M4 5h13a2 2 0 0 1 2 2v12a1 1 0 0 1-1 1H6a2 2 0 0 1-2-2z"/><path d="M19 9h2v9a2 2 0 0 1-2 2"/><path d="M8 9h7M8 13h7M8 17h4"/>',
    "file": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "briefcase": '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 13h18"/>',
    "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20v-1a6.5 6.5 0 0 1 13 0v1"/><path d="M16 4.6a3.5 3.5 0 0 1 0 6.8M18.5 14.6a6.5 6.5 0 0 1 3 5.4"/>',
    "sliders": '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    "lifebuoy": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3.5"/><path d="M5.6 5.6l3.9 3.9M14.5 14.5l3.9 3.9M18.4 5.6l-3.9 3.9M9.5 14.5l-3.9 3.9"/>',
    "utensils": '<path d="M6 3v7a2 2 0 0 0 2 2v9M10 3v7M6 7h4"/><path d="M17 3c-1.7 1.5-3 4-3 7 0 1.7 1.3 3 3 3v8"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    "bell": '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 8-3 8h18s-3-1-3-8"/><path d="M10.3 20a2 2 0 0 0 3.4 0"/>',
    "moon": '<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "star": '<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
    "external": '<path d="M7 17 17 7M8 7h9v9"/>',
    "arrow-right": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "arrow-left": '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    "chevron-left": '<path d="m15 6-6 6 6 6"/>',
    "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
    "x": '<path d="M6 6l12 12M18 6 6 18"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1"/>',
    "logout": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>',
    "switch": '<path d="M17 2l4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14M7 22l-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/>',
    "pin": '<path d="M12 21s7-5.6 7-11a7 7 0 1 0-14 0c0 5.4 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "play": '<circle cx="12" cy="12" r="9"/><path d="m10 8.5 6 3.5-6 3.5z"/>',
    "image": '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="1.8"/><path d="m21 16-5-5-8 8"/>',
    "award": '<circle cx="12" cy="9" r="6"/><path d="m8.5 14-1.5 7 5-3 5 3-1.5-7"/>',
    "heart": '<path d="M12 20s-7.5-4.6-9.2-9.4A4.8 4.8 0 0 1 12 6.8a4.8 4.8 0 0 1 9.2 3.8C19.5 15.4 12 20 12 20z"/>',
    "card": '<rect x="2.5" y="5" width="19" height="14" rx="2"/><path d="M2.5 10h19M6.5 15h4"/>',
    "book": '<path d="M12 6.5C10.5 5 8 4.5 4 4.5v13c4 0 6.5.5 8 2 1.5-1.5 4-2 8-2v-13c-4 0-6.5.5-8 2z"/><path d="M12 6.5v13"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
    "check": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    "check-circle": '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
    "alert": '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16.5v.01"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.01"/>',
    "sparkles": '<path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 16l.7 1.8 1.8.7-1.8.7L19 21l-.7-1.8-1.8-.7 1.8-.7z"/>',
    "download": '<path d="M12 3v12M7 11l5 5 5-5M5 21h14"/>',
    "link": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.4 8-8 9-4.6-1-8-4-8-9V6z"/><path d="m9 12 2 2 4-4"/>',
    "id": '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="11" r="2.2"/><path d="M5.5 17a3.5 3.5 0 0 1 7 0M14 9h4M14 13h4"/>',
    "lock": '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    "megaphone": '<path d="M3 11v2a1 1 0 0 0 1 1h3l8 4V6L7 10H4a1 1 0 0 0-1 1z"/><path d="M18 9a4 4 0 0 1 0 6"/>',
    "settings": '<path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6 7 7M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4"/><circle cx="12" cy="12" r="3.5"/>',
}


@register.simple_tag
def icon(name, extra=""):
    paths = _ICONS.get(name, _ICONS["info"])
    return format_html(
        '<svg class="vi {}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">{}</svg>',
        extra, mark_safe(paths))


@register.simple_tag
def greeting():
    hour = timezone.localtime().hour
    return gettext("Good morning") if hour < 12 else gettext("Good afternoon") if hour < 17 else gettext("Good evening")


@register.filter
def initials(value, count=1):
    words = [w for w in str(value or "").replace(".", " ").split() if w]
    return "".join(w[0] for w in words[: int(count)]).upper() or "?"


@register.filter
def hue(value):
    """A stable colour slot 1-6 for a name, so each application/person keeps its own colour."""
    return sum(ord(c) for c in str(value or "")) % 6 + 1


@register.filter
def dname(user):
    """Friendly full name for a user."""
    return names.display_name(user)


@register.filter
def dfirst(user):
    """Friendly first name for a user."""
    return names.first_name(user)


_ASSET_HASHES = {}


def _asset_hash(path):
    """Short fingerprint of a static file, so browsers fetch a changed file straight away and never mix old CSS with new pages."""
    import hashlib
    import os
    from django.conf import settings
    from django.contrib.staticfiles import finders
    found = finders.find(path)
    if not found and getattr(settings, "STATIC_ROOT", None):
        candidate = os.path.join(str(settings.STATIC_ROOT), path)
        found = candidate if os.path.exists(candidate) else None
    if not found or isinstance(found, (list, tuple)):
        return "0"
    st = os.stat(found)
    key = (found, st.st_mtime_ns, st.st_size)
    cached = _ASSET_HASHES.get(path)
    if cached and cached[0] == key:
        return cached[1]
    with open(found, "rb") as fh:
        digest = hashlib.md5(fh.read()).hexdigest()[:10]
    _ASSET_HASHES[path] = (key, digest)
    return digest


@register.simple_tag
def vstatic(path):
    """{% vstatic 'css/x.css' %} -> /static/css/x.css?v=<fingerprint>"""
    from django.templatetags.static import static
    return "%s?v=%s" % (static(path), _asset_hash(path))
