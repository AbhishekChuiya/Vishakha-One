from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from contenthub.models import Announcement, Resource


class Command(BaseCommand):
    help = ("Move announcements and documents that expired more than N days ago into the Archive, so Content Manager lists stay tidy. "
            "Expired items are already hidden from employees; this only files them away. Run daily from cron.")

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30, help="Archive items expired for at least this many days (default 30).")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        cutoff = timezone.now() - timedelta(days=opts["days"])
        total = 0
        for model in (Announcement, Resource):
            qs = model.objects.filter(is_archived=False, expires_at__isnull=False, expires_at__lte=cutoff)
            n = qs.count()
            total += n
            if not opts["dry_run"]:
                qs.update(is_archived=True, archived_at=timezone.now(), is_published=False)
            self.stdout.write(f"{model.__name__}: {n}")
        self.stdout.write(self.style.SUCCESS(("Would archive " if opts["dry_run"] else "Archived ") + f"{total} item(s)."))
