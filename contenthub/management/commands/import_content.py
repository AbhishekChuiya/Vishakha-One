from django.core.management.base import BaseCommand, CommandError

from contenthub.content_transfer import BundleError, MODELS, import_bundle


class Command(BaseCommand):
    help = ("Import a ZIP made by export_content. Records are matched by title/date/name, so running it again "
            "updates rather than duplicates. Use --dry-run first to see what would change.")

    def add_arguments(self, parser):
        parser.add_argument("bundle", help="ZIP file made by export_content")
        parser.add_argument("--dry-run", action="store_true", help="Show what would happen; change nothing.")
        parser.add_argument("--no-media", action="store_true", help="Do not copy uploaded files.")
        parser.add_argument("--skip-existing", action="store_true", help="Leave records that already exist untouched.")
        parser.add_argument("--only", nargs="+", choices=sorted(MODELS), help="Import just these parts.")

    def handle(self, *args, **opts):
        try:
            result = import_bundle(opts["bundle"], dry_run=opts["dry_run"], include_media=not opts["no_media"],
                                   skip_existing=opts["skip_existing"], only=opts["only"])
        except BundleError as exc:
            raise CommandError(str(exc))
        self.stdout.write(f"  {'part':<14} created updated skipped")
        for label, s in result["summary"].items():
            self.stdout.write(f"  {label:<14} {s['created']:>7} {s['updated']:>7} {s['skipped']:>7}")
        verb = "would be copied" if opts["dry_run"] else "copied"
        self.stdout.write(self.style.SUCCESS(("DRY RUN - nothing was changed. " if opts["dry_run"] else "Done. ") + f"{result['files']} uploaded file(s) {verb}."))
