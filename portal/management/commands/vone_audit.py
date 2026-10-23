"""Read-only deployment audit for Vishakha One. No secrets or live values printed."""
import json
import os
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connections


class Command(BaseCommand):
    help = "A1.16 read-only security and deployment audit; --json for structured output"

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", dest="as_json")

    def handle(self, *args, **options):
        results = []
        def add(category, name, status, detail, action=""):
            results.append(dict(category=category, check=name, status=status, detail=detail, recommendation=action))

        env = str(os.getenv("VONE_ENV", "development")).lower()
        prod = env in ("production", "staging")
        add("environment", "mode", "INFO", env)
        add("security", "debug", "FAIL" if prod and settings.DEBUG else "WARN" if settings.DEBUG else "PASS",
            "Enabled" if settings.DEBUG else "Disabled", "Set DJANGO_DEBUG=false for staging/production" if settings.DEBUG else "")
        allowed = list(getattr(settings, "ALLOWED_HOSTS", []))
        wildcards = any(h in ("*", ".*") for h in allowed)
        add("security", "allowed_hosts", "FAIL" if wildcards else "PASS" if allowed else "WARN",
            "Wildcard present" if wildcards else f"{len(allowed)} configured host(s)", "Use explicit company hostnames" if wildcards or not allowed else "")
        key = getattr(settings, "SECRET_KEY", "")
        add("security", "secret_key", "PASS" if len(key) >= 50 and not key.startswith("django-insecure-") else "WARN",
            "Configured (value hidden)" if key else "Missing", "Use a unique, strong production secret stored outside source control")
        for setting in ("SECURE_SSL_REDIRECT", "SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE"):
            value = bool(getattr(settings, setting, False))
            add("security", setting.lower(), "WARN" if prod and not value else "PASS" if value else "INFO",
                "Enabled" if value else "Disabled (local HTTP)", "Enable only after production HTTPS and proxy configuration" if not value else "")
        hsts = int(getattr(settings, "SECURE_HSTS_SECONDS", 0) or 0)
        add("security", "hsts", "WARN" if prod and not hsts else "PASS" if hsts else "INFO",
            "Configured" if hsts else "Disabled", "Enable only after HTTPS works for the entire intended hostname")
        trusted = getattr(settings, "CSRF_TRUSTED_ORIGINS", [])
        add("security", "csrf_trusted_origins", "INFO", f"{len(trusted)} configured origin(s)")
        db = settings.DATABASES.get("default", {})
        engine = str(db.get("ENGINE", ""))
        add("database", "engine", "WARN" if prod and "sqlite" in engine else "INFO" if "sqlite" in engine else "PASS",
            engine.rsplit(".", 1)[-1], "Consider PostgreSQL for concurrent production traffic" if "sqlite" in engine else "")
        try:
            with connections["default"].cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            add("database", "connection", "PASS", "Read-only SELECT 1 succeeded")
        except Exception as exc:
            add("database", "connection", "FAIL", f"Connection failed ({type(exc).__name__}); credentials hidden")
        static_root = Path(getattr(settings, "STATIC_ROOT", "") or settings.BASE_DIR / "staticfiles")
        static_dirs = getattr(settings, "STATICFILES_DIRS", [])
        add("assets", "static_root", "PASS" if static_root.is_dir() else "WARN", "Directory exists" if static_root.is_dir() else "Directory absent", "Run collectstatic as part of deployment" if not static_root.is_dir() else "")
        add("assets", "static_sources", "PASS" if all(Path(d).is_dir() for d in static_dirs) else "WARN", f"{len(static_dirs)} static source director(ies)")
        media = Path(getattr(settings, "MEDIA_ROOT", "") or settings.BASE_DIR / "media")
        add("assets", "media_root", "PASS" if media.is_dir() else "WARN", "Directory exists" if media.is_dir() else "Directory absent", "Provision persistent storage and backups for uploads")
        add("deployment", "reverse_proxy", "INFO", "Not detectable from Django settings", "Ask IT for hostname, TLS termination, forwarded headers and port allocation")
        add("deployment", "worker_capacity", "INFO", "Requires load testing", "Start with a dedicated WSGI service and measure concurrency, memory, CPU and response latency")
        add("deployment", "backups", "INFO", "Not verifiable from settings", "Schedule encrypted database and media backups; test restoration on staging")
        add("deployment", "ai_integration", "INFO", "Separate capacity planning needed", "Size LLM inference separately from Django; check GPU/RAM and API timeouts")
        if options["as_json"]:
            self.stdout.write(json.dumps({"environment":env,"results":results,"failures":sum(x["status"]=="FAIL" for x in results),"warnings":sum(x["status"]=="WARN" for x in results)},indent=2))
        else:
            self.stdout.write("=== Vishakha One A1.16 deployment audit (read-only) ===")
            for item in results:
                self.stdout.write(f"[{item['status']}] {item['category']}.{item['check']}: {item['detail']}")
                if item["recommendation"]:
                    self.stdout.write(f"    Next: {item['recommendation']}")
            self.stdout.write(f"Summary: {sum(x['status']=='FAIL' for x in results)} failure(s), {sum(x['status']=='WARN' for x in results)} warning(s)")
