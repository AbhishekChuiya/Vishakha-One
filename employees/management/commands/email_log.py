from django.core.management.base import BaseCommand

from employees.models import EmailDelivery


class Command(BaseCommand):
    help = "Show the most recent e-mails the portal tried to send, and whether each one went out."

    def add_arguments(self, parser):
        parser.add_argument("--recipient", help="Only this address")
        parser.add_argument("--limit", type=int, default=20)

    def handle(self, *args, **options):
        rows = EmailDelivery.objects.all()
        if options["recipient"]:
            rows = rows.filter(recipient__iexact=options["recipient"].strip())
        rows = list(rows[:options["limit"]])
        if not rows:
            self.stdout.write("No e-mails recorded yet.")
            return
        for row in rows:
            style = {"sent": self.style.SUCCESS, "failed": self.style.ERROR}.get(row.status, self.style.WARNING)
            self.stdout.write(style(
                f"{row.created_at:%d %b %H:%M:%S}  {row.status:<9} x{row.attempts}  {row.get_purpose_display():<34} "
                f"{row.recipient}" + (f"  [{row.error}]" if row.error else "")))
