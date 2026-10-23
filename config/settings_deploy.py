"""Opt-in Linux staging/production settings. Existing development settings remain unchanged.
Use DJANGO_SETTINGS_MODULE=config.settings_deploy and VONE_ENV=staging|production.
"""
import os
from pathlib import Path
from .settings import *  # noqa: F401,F403

if VONE_ENV not in {"staging", "production"}:
    raise RuntimeError("Deployment settings require VONE_ENV=staging or production")

DEBUG = False
if not SECRET_KEY or len(SECRET_KEY) < 40:
    raise RuntimeError("Provide a unique production DJANGO_SECRET_KEY (at least 40 characters)")
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise RuntimeError("Set explicit DJANGO_ALLOWED_HOSTS for this environment")

required_db = ["PGDATABASE", "PGUSER", "PGPASSWORD", "PGHOST"]
missing = [name for name in required_db if not os.getenv(name)]
if missing:
    raise RuntimeError("Missing PostgreSQL environment variables: " + ", ".join(missing))
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["PGDATABASE"],
        "USER": os.environ["PGUSER"],
        "PASSWORD": os.environ["PGPASSWORD"],
        "HOST": os.environ["PGHOST"],
        "PORT": os.getenv("PGPORT", "5432"),
        "CONN_MAX_AGE": int(os.getenv("PG_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {"connect_timeout": 10},
    }
}
STATIC_ROOT = Path(os.getenv("VONE_STATIC_ROOT", "/srv/vishakha-one/staticfiles"))
MEDIA_ROOT = Path(os.getenv("VONE_MEDIA_ROOT", "/srv/vishakha-one/media"))
CSRF_TRUSTED_ORIGINS = [v.strip() for v in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if v.strip()]

# Enable only after HTTPS is working end-to-end and the proxy is trusted.
_https = os.getenv("VONE_HTTPS_READY", "false").lower() == "true"
SECURE_SSL_REDIRECT = _https
SESSION_COOKIE_SECURE = _https
CSRF_COOKIE_SECURE = _https
SECURE_HSTS_SECONDS = int(os.getenv("VONE_HSTS_SECONDS", "0")) if _https else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Never trust forwarded protocol headers unless Nginx is the only reachable proxy.
if os.getenv("VONE_TRUST_PROXY_HTTPS", "false").lower() == "true":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Prevent cookie collisions when multiple Django sites share a hostname.
SESSION_COOKIE_NAME = os.getenv("VONE_SESSION_COOKIE_NAME", "vone_sessionid")
CSRF_COOKIE_NAME = os.getenv("VONE_CSRF_COOKIE_NAME", "vone_csrftoken")

# Django should not serve static or uploaded media in production; Nginx serves them.
