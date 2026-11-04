from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Send one plain test e-mail to check the SMTP settings. Shows the exact error if it fails."

    def add_arguments(self, parser):
        parser.add_argument("to_address")

    def handle(self, *args, **options):
        backend = settings.EMAIL_BACKEND.rsplit(".", 2)[-2]
        self.stdout.write(f"Backend: {backend} | host: {settings.EMAIL_HOST or '(none)'}:{settings.EMAIL_PORT} "
                          f"| TLS: {settings.EMAIL_USE_TLS} | from: {settings.DEFAULT_FROM_EMAIL} "
                          f"| login user set: {bool(settings.EMAIL_HOST_USER)} | password set: {bool(settings.EMAIL_HOST_PASSWORD)}")
        try:
            sent = send_mail("Vishakha One e-mail test",
                             "This is a test message from Vishakha One. If you can read it, e-mail sending works.",
                             None, [options["to_address"]], fail_silently=False)
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"FAILED: {type(exc).__name__}: {exc}"))
            return
        self.stdout.write(self.style.SUCCESS(f"Accepted by the mail server ({sent} message). Now check the inbox and spam folder."))
