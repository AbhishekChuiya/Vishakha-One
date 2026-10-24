"""Read-only Vishakha One deployment preflight. Usage: python manage.py vone_preflight"""
import json
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.migrations.executor import MigrationExecutor
from django.urls import reverse, resolve


class Command(BaseCommand):
    help = "Read-only application, database, routes, migrations and security preflight"

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", dest="as_json", help="Machine-readable results")
        parser.add_argument("--strict", action="store_true", help="Exit with failure on warnings as well as failures")

    def handle(self, *args, **options):
        results = []

        def add(name, status, detail):
            results.append({"check": name, "status": status, "detail": str(detail)})

        env = getattr(settings, "VONE_ENV", None)
        if env is None:
            env = "not exposed by settings"
        add("environment", "INFO", env)
        add("debug", "WARN" if settings.DEBUG else "PASS", "DEBUG is ON (local only)" if settings.DEBUG else "DEBUG is OFF")
        hosts = list(settings.ALLOWED_HOSTS)
        add("allowed_hosts", "FAIL" if not hosts or "*" in hosts else "PASS", ", ".join(hosts) or "Empty")
        engine = settings.DATABASES["default"]["ENGINE"]
        add("database_engine", "WARN" if "sqlite3" in engine else "PASS", engine + (" (suitable for local UAT; evaluate PostgreSQL for production)" if "sqlite3" in engine else ""))
        for setting in ("SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE", "SECURE_SSL_REDIRECT"):
            enabled = bool(getattr(settings, setting, False))
            status = "PASS" if enabled else ("INFO" if settings.DEBUG else "WARN")
            add(setting.lower(), status, "enabled" if enabled else "disabled" + (" (expected for local HTTP)" if settings.DEBUG else ""))
        add("clickjacking", "PASS" if "django.middleware.clickjacking.XFrameOptionsMiddleware" in settings.MIDDLEWARE else "WARN", "XFrameOptionsMiddleware " + ("enabled" if "django.middleware.clickjacking.XFrameOptionsMiddleware" in settings.MIDDLEWARE else "missing"))
        for route in ("portal:home", "portal:canteen_menu", "portal:notifications", "portal:profile"):
            try:
                url = reverse(route)
                resolved = resolve(url)
                add("route:" + route, "PASS", url + " -> " + str(resolved.view_name))
            except Exception as exc:
                add("route:" + route, "FAIL", type(exc).__name__ + ": " + str(exc))
        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            add("database_connectivity", "PASS", "Read-only SELECT 1 succeeded")
        except Exception as exc:
            add("database_connectivity", "FAIL", type(exc).__name__ + ": " + str(exc))
        try:
            executor = MigrationExecutor(connections["default"])
            targets = executor.loader.graph.leaf_nodes()
            pending = executor.migration_plan(targets)
            add("migrations", "WARN" if pending else "PASS", (str(len(pending)) + " pending migration(s): " + ", ".join(str(node) for node, backwards in pending[:5])) if pending else "All recorded migrations applied")
        except Exception as exc:
            add("migrations", "FAIL", type(exc).__name__ + ": " + str(exc))
        for label, folder in (("static", getattr(settings, "STATIC_ROOT", None)), ("media", getattr(settings, "MEDIA_ROOT", None))):
            if folder:
                path = Path(folder)
                add(label + "_directory", "PASS" if path.is_dir() else "INFO", "present" if path.is_dir() else "not created yet (normal before collectstatic/uploads)")
        fails = sum(r["status"] == "FAIL" for r in results)
        warns = sum(r["status"] == "WARN" for r in results)
        if options["as_json"]:
            self.stdout.write(json.dumps({"results": results, "failures": fails, "warnings": warns}, indent=2))
        else:
            self.stdout.write("=== Vishakha One A1.14 preflight (read-only) ===")
            for item in results:
                self.stdout.write("[{status}] {check}: {detail}".format(**item))
            self.stdout.write("Summary: {} failure(s), {} warning(s)".format(fails, warns))
        if fails or (warns and options["strict"]):
            raise SystemExit(1)
