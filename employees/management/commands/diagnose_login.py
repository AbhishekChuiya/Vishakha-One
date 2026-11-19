from getpass import getpass

from django.contrib.auth import authenticate, get_user_model
from django.core.management.base import BaseCommand

from employees.models import EmailDelivery, EmployeeProfile, is_company_email


class Command(BaseCommand):
    help = (
        "Explain why an employee cannot sign in. Read-only. Never prints password hashes. "
        "Add --check-password to type the password (hidden) and test it the same way the login page does."
    )

    def add_arguments(self, parser):
        parser.add_argument("identifier", help="Employee ID or company email, as typed on the login page")
        parser.add_argument("--check-password", action="store_true",
                            help="Prompt for the password (not shown, not stored) and test it.")
        parser.add_argument("--send-reset", action="store_true",
                            help="Actually send the 'forgot password' e-mail now and show the result.")
        parser.add_argument("--base-url", default="http://127.0.0.1:8000",
                            help="Site address used inside e-mailed links, e.g. https://portal.example.com")

    def handle(self, *args, **options):
        out = self.stdout.write
        User = get_user_model()
        identifier = options["identifier"].strip()

        def line(ok, good, bad):
            out(self.style.SUCCESS("  OK   " + good) if ok else self.style.ERROR("  FAIL " + bad))
            return ok

        out(f"Looking up: {identifier}\n")
        self._reset_section(identifier, options)
        if "@" in identifier:
            line(is_company_email(identifier.lower()), "email ends with @vishakha.com",
                 "email must end with @vishakha.com (login rejects other domains)")
            profile = EmployeeProfile.objects.select_related("user").filter(
                company_email__iexact=identifier).first()
        else:
            profile = EmployeeProfile.objects.select_related("user").filter(
                employee_id__iexact=identifier).first()

        if not line(profile is not None, "employee profile found",
                    "NO employee profile for this Employee ID / email - the account was not created "
                    "(registration not finished, or a different ID/email was used)"):
            out("\nMost recently created employee accounts (to spot typos):")
            for p in EmployeeProfile.objects.order_by("-created_at")[:5]:
                out(f"   {p.employee_id:<14} {p.company_email:<40} created {p.created_at:%d %b %H:%M}")
            return

        user = profile.user
        ok = True
        ok &= line(profile.is_active, "employee profile is active", "employee profile is NOT active (Admin > Employee profiles)")
        ok &= line(user.is_active, "login account is active", "login account is NOT active (Admin > Users)")
        ok &= line(is_company_email(profile.company_email), "profile email is @vishakha.com",
                   "profile email is not @vishakha.com")
        ok &= line((user.email or "").strip().lower() == profile.company_email,
                   "login account email matches the profile email",
                   f"login account email ({user.email or 'empty'}) differs from profile email "
                   f"({profile.company_email}) - login is refused until they match")
        ok &= line(user.has_usable_password(), "a password is set", "NO usable password is set - use Forgot password")
        out(f"\n  Username: {user.get_username()} | created: {user.date_joined:%d %b %Y %H:%M} | "
            f"last login: {user.last_login:%d %b %Y %H:%M}" if user.last_login else
            f"\n  Username: {user.get_username()} | created: {user.date_joined:%d %b %Y %H:%M} | last login: never")

        if options["check_password"]:
            password = getpass("\nType the password to test (hidden): ")
            result = authenticate(None, username=user.get_username(), password=password)
            out("")
            line(result is not None, "password is CORRECT for this account",
                 "password does NOT match (check typing/caps lock, or use Forgot password)")
        out("")
        out(self.style.SUCCESS("RESULT: account looks fine for sign-in.") if ok else
            self.style.ERROR("RESULT: fix the FAIL lines above and sign-in will work."))


    def _reset_section(self, identifier, options):
        from portal.auth_forms import EmployeePasswordResetForm, classify_reset_request

        out = self.stdout.write
        kind, value = classify_reset_request(identifier)
        out("Forgot-password e-mail:")
        explain = {
            "reset": f"a reset link WOULD be sent to {getattr(value, 'email', value)}",
            "attention": f"the account is inactive or inconsistent; a 'could not reset' notice WOULD go to {value}",
            "no_account": f"no account for this company e-mail; a 'create your account' e-mail WOULD go to {value}",
            "none": "NOTHING can be sent: an unknown Employee ID has no stored mailbox, or the address is not @vishakha.com",
        }[kind]
        out(("  " + explain))
        recipient = getattr(value, "email", value)
        if recipient:
            rows = list(EmailDelivery.objects.filter(recipient__iexact=recipient)[:3])
            for row in rows:
                out(f"  recent: {row.created_at:%d %b %H:%M} {row.get_purpose_display()} -> {row.status}"
                    + (f" [{row.error}]" if row.error else ""))
        if options["send_reset"]:
            base = options["base_url"].rstrip("/")
            host = base.split("://", 1)[-1]

            class AdminRequest:  # stands in for a web request: only supplies the site address for the links
                def get_host(self):
                    return host

                def is_secure(self):
                    return base.startswith("https")

                def build_absolute_uri(self, path="/"):
                    return base + path

            request = AdminRequest()
            form = EmployeePasswordResetForm({"identifier": identifier})
            if form.is_valid():
                form.save(
                    request=request, use_https=base.startswith("https"),
                    subject_template_name="accounts/email/password_reset_subject.txt",
                    email_template_name="accounts/email/password_reset_email.txt",
                    html_email_template_name="accounts/email/password_reset_email.html")
            latest = EmailDelivery.objects.filter(recipient__iexact=recipient).first() if recipient else None
            out("  send result: " + (f"{latest.status} (attempts {latest.attempts})" + (f" [{latest.error}]" if latest and latest.error else "")
                                      if latest else "nothing was sent"))
        out("")
