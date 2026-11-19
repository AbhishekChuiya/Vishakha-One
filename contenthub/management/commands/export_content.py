from django.core.management.base import BaseCommand, CommandError

from contenthub.content_transfer import MODELS, export_bundle


class Command(BaseCommand):
    help = ("Export all portal content (applications, news, policies/documents, jobs, joiners, events, canteen menu) "
            "and the uploaded files they use into one ZIP. Employees, passwords and notifications are NOT included.")

    def add_arguments(self, parser):
        parser.add_argument("output", help="ZIP file to create, e.g. vone_content.zip")
        parser.add_argument("--no-media", action="store_true", help="Records only, without uploaded files.")
        parser.add_argument("--only", nargs="+", choices=sorted(MODELS), help="Export just these parts.")

    def handle(self, *args, **opts):
        try:
            result = export_bundle(opts["output"], include_media=not opts["no_media"], only=opts["only"])
        except OSError as exc:
            raise CommandError(str(exc))
        for label, n in result["counts"].items():
            self.stdout.write(f"  {label:<14} {n}")
        self.stdout.write(self.style.SUCCESS(f"Wrote {opts['output']} ({result['files']} uploaded files)."))
        if result["missing"]:
            self.stdout.write(self.style.WARNING(f"{len(result['missing'])} file(s) referenced by records were not found on disk:"))
            for m in result["missing"][:20]:
                self.stdout.write("   - " + m)
