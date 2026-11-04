from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import reverse

from employees import activation
from employees.models import is_company_email


class Command(BaseCommand):
    help = (
        "Explain why a registration link is (not) sent for an Employee ID + email. "
        "Read-only unless --send is given. Output is for administrators only."
    )

    def add_arguments(self, parser):
        parser.add_argument("employee_id")
        parser.add_argument("company_email")
        parser.add_argument("--send", action="store_true", help="Actually send the registration e-mail now.")
        parser.add_argument("--show-link", action="store_true",
                            help="Print the registration link in this terminal (treat it like a password).")
        parser.add_argument("--base-url", default="http://127.0.0.1:8000",
                            help="Site address used inside the link, e.g. https://portal.example.com")

    def handle(self, *args, **options):
        out = self.stdout.write
        eid = options["employee_id"].strip()
        email = options["company_email"].strip().lower()

        backend = settings.EMAIL_BACKEND.rsplit(".", 2)[-2]
        out(f"Environment e-mail backend : {backend}")
        if backend == "console":
            out("   -> e-mails are NOT delivered; they are printed in the terminal running 'runserver'.")
        elif backend == "dummy":
            out(self.style.WARNING("   -> no SMTP configured: e-mails are silently discarded. "
                                   "Set DJANGO_EMAIL_HOST etc. in the .env file."))
        else:
            out(f"   -> SMTP host: {settings.EMAIL_HOST or '(not set)'}, port {settings.EMAIL_PORT}")
        out(f"Sender address             : {settings.DEFAULT_FROM_EMAIL}")
        out(f"Self-registration enabled  : {activation.registration_enabled()}")
        out("")

        problems = 0
        def check(ok, good, bad):
            nonlocal problems
            if ok:
                out(self.style.SUCCESS("  OK   " + good))
            else:
                problems += 1
                out(self.style.ERROR("  FAIL " + bad))
            return ok

        check(activation.registration_enabled(), "registration is open",
              "registration is closed (VONE_SELF_REGISTRATION_ENABLED=false)")
        check(bool(activation.EMPLOYEE_ID_RE.match(eid)), "Employee ID format is valid",
              "Employee ID must be 3-32 characters: letters, numbers, dot, dash or underscore")
        check(is_company_email(email), "email ends with @vishakha.com", "email must end with @vishakha.com")
        free = not activation.identity_taken(eid.upper(), email)
        check(free, "no existing account uses this Employee ID / email / username",
              "this Employee ID, email or username ALREADY has an account "
              "(e.g. a test account) - use Forgot password, or register a NEW ID and email")

        identity = activation.registrable_identity(eid, email) if activation.registration_enabled() else None
        out("")
        if identity is None:
            if activation.profile_for_email(email):
                out(self.style.WARNING("RESULT: this email already owns an employee account, so NO registration link "
                                       "is sent. An 'already registered' e-mail (with Sign in / Forgot password "
                                       "buttons) is sent to that mailbox instead."))
            else:
                out(self.style.ERROR("RESULT: the registration page would NOT send an e-mail for these details."))
            return
        out(self.style.SUCCESS("RESULT: READY - the registration page WOULD send an e-mail for these details."))
        out("        (It also sends at most 5 per hour per email; wait or restart runserver if you tested a lot.)")
        if options["send"]:
            link = options["base_url"].rstrip("/") + reverse("accounts:activate", args=[activation.make_token(*identity)])
            sent = activation.send_activation_email(identity[0], identity[1], link)
            out(self.style.SUCCESS("E-mail handed to the mail backend.") if sent else
                self.style.ERROR("E-mail FAILED - run 'manage.py test_email_setup <address>' to see the exact error."))
            if options["show_link"]:
                out("Registration link: " + link)
