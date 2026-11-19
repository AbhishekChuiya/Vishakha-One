"""Tests for registration (HR-approved activation), forgot password and the login page links."""
import io
import re
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import EmailDelivery, EmployeeProfile

User = get_user_model()
GOOD_PASSWORD = "Sunrise-Harbor-4821-xyz"


def link_in(message):
    return re.search(r"https?://\S+", message.body).group(0)


class LoginPageTests(TestCase):
    def test_need_help_replaced_by_forgot_password_link(self):
        html = self.client.get(reverse("accounts:login")).content.decode()
        self.assertNotIn("Need help?", html)
        self.assertIn("Forgot password?", html)
        self.assertIn(reverse("accounts:password_reset"), html)
        self.assertIn(reverse("accounts:register"), html)

    def test_sso_button_visible_by_default_and_can_be_hidden(self):
        sso = reverse("accounts:sso")
        self.assertIn(f'href="{sso}"', self.client.get(reverse("accounts:login")).content.decode())
        with override_settings(VONE_SSO_ENABLED=False):
            self.assertNotIn(f'href="{sso}"', self.client.get(reverse("accounts:login")).content.decode())

    def test_new_pages_are_public(self):
        for name in ("accounts:register", "accounts:register_done", "accounts:password_reset",
                     "accounts:password_reset_done", "accounts:password_reset_complete"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)


class SignOutTests(TestCase):
    def test_account_without_employee_profile_can_still_sign_out(self):
        User.objects.create_user("just_admin", password=GOOD_PASSWORD)
        self.client.login(username="just_admin", password=GOOD_PASSWORD)
        denied = self.client.get(reverse("portal:home"))
        self.assertEqual(denied.status_code, 403)
        self.assertContains(denied, "just_admin", status_code=403)  # page names the signed-in account
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_switch_user_also_works_without_employee_profile(self):
        User.objects.create_user("just_admin2", password=GOOD_PASSWORD)
        self.client.login(username="just_admin2", password=GOOD_PASSWORD)
        self.assertRedirects(self.client.post(reverse("accounts:switch_user")), reverse("accounts:login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_still_requires_post(self):
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)


class RegistrationTests(TestCase):
    EID, EMAIL = "E1001", "asha.rao@vishakha.com"

    def setUp(self):
        cache.clear()

    def request_link(self, employee_id=None, email=None):
        return self.client.post(reverse("accounts:register"), {
            "employee_id": employee_id or self.EID, "company_email": email or self.EMAIL})

    def test_new_identity_receives_link_at_that_company_address(self):
        self.assertRedirects(self.request_link(), reverse("accounts:register_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.EMAIL])
        self.assertFalse(User.objects.exists())  # nothing is created until the link is used

    def test_registration_email_has_text_and_html_versions_with_the_same_link(self):
        self.request_link()
        message = mail.outbox[0]
        self.assertEqual(message.subject, "Complete your Vishakha One registration")
        html, mimetype = message.alternatives[0]
        self.assertEqual(mimetype, "text/html")
        link = link_in(message)
        self.assertIn(link, html)
        self.assertIn(self.EID, html)
        self.assertIn("Create my password", html)

    def test_bad_email_domain_or_employee_id_rejected_with_no_mail(self):
        for eid, email in (("E1001", "asha@gmail.com"), ("E1001", "a@sub.vishakha.com"),
                           ("x", self.EMAIL), ("bad id!", self.EMAIL)):
            self.assertEqual(self.request_link(eid, email).status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_existing_account_owner_gets_already_registered_email_and_no_link(self):
        user = User.objects.create_user("existing", password=GOOD_PASSWORD)
        EmployeeProfile.objects.create(user=user, employee_id=self.EID, company_email=self.EMAIL)
        self.assertRedirects(self.request_link(), reverse("accounts:register_done"))
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, [self.EMAIL])
        self.assertEqual(message.subject, "You already have a Vishakha One account")
        self.assertNotIn("/accounts/activate/", message.body)  # never a registration link
        self.assertIn(reverse("accounts:login"), message.body)
        self.assertIn(reverse("accounts:password_reset"), message.body)
        self.assertIn(self.EID, message.alternatives[0][0])

    def test_same_email_with_another_employee_id_still_only_mails_the_mailbox_owner(self):
        user = User.objects.create_user("existing", password=GOOD_PASSWORD)
        EmployeeProfile.objects.create(user=user, employee_id=self.EID, company_email=self.EMAIL)
        self.assertRedirects(self.request_link("E7777", self.EMAIL), reverse("accounts:register_done"))
        self.assertEqual([m.to for m in mail.outbox], [[self.EMAIL]])
        self.assertNotIn("/accounts/activate/", mail.outbox[0].body)

    def test_taken_employee_id_with_a_different_email_sends_nothing(self):
        user = User.objects.create_user("existing", password=GOOD_PASSWORD)
        EmployeeProfile.objects.create(user=user, employee_id=self.EID, company_email=self.EMAIL)
        self.assertRedirects(self.request_link(self.EID, "intruder@vishakha.com"), reverse("accounts:register_done"))
        self.assertEqual(len(mail.outbox), 0)

    def test_already_registered_emails_are_rate_limited(self):
        user = User.objects.create_user("existing", password=GOOD_PASSWORD)
        EmployeeProfile.objects.create(user=user, employee_id=self.EID, company_email=self.EMAIL)
        for _ in range(8):
            self.request_link()
        self.assertEqual(len(mail.outbox), 5)

    def test_full_registration_creates_plain_employee_and_login_works(self):
        self.request_link()
        link = link_in(mail.outbox[0])
        self.assertContains(self.client.get(link), self.EID)
        response = self.client.post(link, {"password1": GOOD_PASSWORD, "password2": GOOD_PASSWORD})
        self.assertRedirects(response, reverse("accounts:login"))
        user = EmployeeProfile.objects.get(employee_id=self.EID).user
        self.assertEqual(user.email, self.EMAIL)
        # Registration never grants Content Manager / admin access.
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertEqual(user.get_all_permissions(), set())
        self.assertEqual(user.groups.count(), 0)
        # The chosen password works on the employee login, by Employee ID and by e-mail.
        for identifier in (self.EID, self.EID.lower(), self.EMAIL):
            self.client.logout()
            response = self.client.post(reverse("accounts:login"),
                                        {"identifier": identifier, "password": GOOD_PASSWORD})
            self.assertEqual(response.status_code, 302, identifier)
            self.assertEqual(self.client.get(reverse("portal:profile")).status_code, 200)
        # ...but it does not open Content Manager.
        self.client.logout()
        response = self.client.post(reverse("content_manager:login"),
                                    {"username": user.username, "password": GOOD_PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_link_is_single_use(self):
        self.request_link()
        link = link_in(mail.outbox[0])
        self.client.post(link, {"password1": GOOD_PASSWORD, "password2": GOOD_PASSWORD})
        self.assertEqual(self.client.get(link).status_code, 400)
        response = self.client.post(link, {"password1": GOOD_PASSWORD, "password2": GOOD_PASSWORD})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.filter(email=self.EMAIL).count(), 1)

    def test_expired_and_tampered_links_rejected(self):
        self.request_link()
        link = link_in(mail.outbox[0])
        body = link.rstrip("/")
        tampered = body[:-1] + ("A" if body[-1] != "A" else "B") + "/"
        self.assertEqual(self.client.get(tampered).status_code, 400)
        self.assertEqual(self.client.get(reverse("accounts:activate", args=["garbage"])).status_code, 400)
        with mock.patch("django.core.signing.time.time", return_value=__import__("time").time() + 90000):
            self.assertEqual(self.client.get(link).status_code, 400)

    def test_weak_or_mismatched_password_rejected(self):
        self.request_link()
        link = link_in(mail.outbox[0])
        self.assertEqual(self.client.post(link, {"password1": "12345678", "password2": "12345678"}).status_code, 200)
        self.assertEqual(self.client.post(link, {"password1": GOOD_PASSWORD, "password2": GOOD_PASSWORD + "x"}).status_code, 200)
        self.assertFalse(EmployeeProfile.objects.exists())

    def test_identity_taken_after_link_was_sent_is_refused(self):
        self.request_link()
        link = link_in(mail.outbox[0])
        user = User.objects.create_user("someone_else", password=GOOD_PASSWORD)
        EmployeeProfile.objects.create(user=user, employee_id=self.EID, company_email="someone@vishakha.com")
        response = self.client.post(link, {"password1": GOOD_PASSWORD, "password2": GOOD_PASSWORD})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(EmployeeProfile.objects.count(), 1)

    def test_unrelated_user_with_same_username_blocks_registration_safely(self):
        User.objects.create_user("e1001", password=GOOD_PASSWORD)
        self.request_link()
        self.assertEqual(len(mail.outbox), 0)

    def test_link_emails_are_rate_limited_per_address(self):
        for _ in range(8):
            self.request_link()
        self.assertEqual(len(mail.outbox), 5)

    def test_mail_failure_still_gives_generic_response(self):
        with mock.patch("django.core.mail.EmailMultiAlternatives.send", side_effect=OSError("smtp down")), \
                mock.patch("employees.mailer.time.sleep"):
            self.assertRedirects(self.request_link(), reverse("accounts:register_done"))

    def test_registration_can_be_closed_with_a_setting(self):
        with override_settings(VONE_SELF_REGISTRATION_ENABLED=False):
            self.assertEqual(self.client.get(reverse("accounts:register")).status_code, 403)
            self.assertEqual(self.request_link().status_code, 403)
            self.assertEqual(len(mail.outbox), 0)


class PasswordResetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("ravi", password="Old-Password-7391-abc")
        EmployeeProfile.objects.create(user=self.user, employee_id="E2002", company_email="ravi.k@vishakha.com")

    def ask(self, identifier):
        return self.client.post(reverse("accounts:password_reset"), {"identifier": identifier})

    def test_reset_by_employee_id_and_by_email(self):
        for identifier in ("e2002", "RAVI.K@vishakha.com"):
            self.assertRedirects(self.ask(identifier), reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to, ["ravi.k@vishakha.com"])

    def test_identifiers_that_cannot_receive_mail_get_the_same_page_and_no_mail(self):
        for identifier in ("nobody", "ravi.k@gmail.com", "ZZ-UNKNOWN-ID"):   # unknown Employee ID / not a company address
            self.assertRedirects(self.ask(identifier), reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)

    def test_company_email_without_account_gets_a_create_account_email(self):
        self.assertRedirects(self.ask("ghost@vishakha.com"), reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["ghost@vishakha.com"])
        self.assertEqual(message.subject, "You do not have a Vishakha One account yet")
        self.assertIn(reverse("accounts:register"), message.body)
        self.assertNotIn("password-reset/", message.body)          # never a reset link
        self.assertIn(reverse("accounts:register"), message.alternatives[0][0])

    def test_inactive_or_inconsistent_account_gets_a_could_not_reset_email(self):
        self.user.is_active = False
        self.user.save()
        self.ask("E2002")
        self.assertEqual([m.subject for m in mail.outbox], ["Your Vishakha One password could not be reset"])
        self.assertEqual(mail.outbox[0].to, ["ravi.k@vishakha.com"])
        self.assertNotIn("password-reset/", mail.outbox[0].body)
        self.user.is_active = True
        self.user.save()
        User.objects.filter(pk=self.user.pk).update(email="different@vishakha.com")  # profile/user mismatch
        mail.outbox.clear()
        self.ask("ravi.k@vishakha.com")
        self.assertEqual([m.subject for m in mail.outbox], ["Your Vishakha One password could not be reset"])

    def test_account_without_employee_profile_is_told_to_create_one(self):
        User.objects.create_user("cm_only", email="cm@vishakha.com", password="Old-Password-7391-abc")
        self.ask("cm@vishakha.com")
        self.assertEqual([m.subject for m in mail.outbox], ["You do not have a Vishakha One account yet"])

    def test_every_request_is_written_to_the_delivery_log(self):
        self.ask("E2002")
        self.ask("ghost@vishakha.com")
        rows = {(r.purpose, r.recipient, r.status) for r in EmailDelivery.objects.all()}
        self.assertEqual(rows, {("password_reset", "ravi.k@vishakha.com", "sent"),
                                ("password_reset_no_account", "ghost@vishakha.com", "sent")})
        self.assertNotIn("password-reset/", " ".join(str(v) for r in EmailDelivery.objects.values() for v in r.values()))

    def test_full_reset_changes_password_and_link_is_one_time(self):
        self.ask("E2002")
        link = link_in(mail.outbox[0])
        response = self.client.get(link, follow=True)
        self.assertContains(response, "Set a new password")
        set_url = response.redirect_chain[-1][0]
        response = self.client.post(set_url, {"new_password1": GOOD_PASSWORD, "new_password2": GOOD_PASSWORD})
        self.assertRedirects(response, reverse("accounts:password_reset_complete"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(GOOD_PASSWORD))
        self.assertNotContains(self.client.get(link, follow=True), "Set a new password")

    def test_reset_email_has_text_and_html_versions_with_the_same_link(self):
        self.ask("E2002")
        message = mail.outbox[0]
        html, mimetype = message.alternatives[0]
        self.assertEqual(mimetype, "text/html")
        self.assertIn(link_in(message), html)
        self.assertIn("Choose a new password", html)

    def test_bad_token_shows_friendly_page(self):
        url = reverse("accounts:password_reset_confirm", args=["AA", "bad-token"])
        self.assertContains(self.client.get(url, follow=True), "expired or was already used")

    def test_reset_emails_are_rate_limited(self):
        for _ in range(8):
            self.ask("E2002")
        self.assertEqual(len(mail.outbox), 5)


class DiagnoseCommandTests(TestCase):
    def run_cmd(self, name, *args):
        out = io.StringIO()
        call_command(name, *args, stdout=out)
        return out.getvalue()

    def test_diagnose_reports_reasons(self):
        self.assertIn("must end with @vishakha.com", self.run_cmd("diagnose_registration", "DX001", "dx001@gmail.com"))
        self.assertIn("READY", self.run_cmd("diagnose_registration", "DX001", "dx001@vishakha.com"))
        user = User.objects.create_user("someone", password=GOOD_PASSWORD)
        EmployeeProfile.objects.create(user=user, employee_id="DX001", company_email="dx001@vishakha.com")
        self.assertIn("ALREADY has an account", self.run_cmd("diagnose_registration", "DX001", "dx001@vishakha.com"))

    def test_diagnose_send_and_show_link(self):
        output = self.run_cmd("diagnose_registration", "DX002", "dx002@vishakha.com", "--send", "--show-link",
                              "--base-url", "https://portal.example.test")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("https://portal.example.test/accounts/activate/", output)

    def test_email_setup_command_reports_success_and_failure(self):
        self.assertIn("Accepted", self.run_cmd("test_email_setup", "me@vishakha.com"))
        self.assertEqual(len(mail.outbox), 1)
        with mock.patch("employees.management.commands.test_email_setup.send_mail",
                        side_effect=OSError("535 authentication failed")):
            self.assertIn("FAILED: OSError", self.run_cmd("test_email_setup", "me@vishakha.com"))


class DiagnoseLoginCommandTests(TestCase):
    def run_cmd(self, *args):
        out = io.StringIO()
        call_command("diagnose_login", *args, stdout=out)
        return out.getvalue()

    def test_reports_missing_inactive_and_mismatched_accounts(self):
        self.assertIn("NO employee profile", self.run_cmd("NOPE123"))
        user = User.objects.create_user("lg1", password=GOOD_PASSWORD)
        profile = EmployeeProfile.objects.create(user=user, employee_id="LG001", company_email="lg1@vishakha.com")
        self.assertIn("account looks fine", self.run_cmd("lg001"))
        self.assertIn("account looks fine", self.run_cmd("lg1@vishakha.com"))
        User.objects.filter(pk=user.pk).update(email="different@vishakha.com")
        self.assertIn("differs from profile email", self.run_cmd("LG001"))
        User.objects.filter(pk=user.pk).update(email="lg1@vishakha.com", is_active=False)
        self.assertIn("login account is NOT active", self.run_cmd("LG001"))
        user.refresh_from_db(); user.set_unusable_password(); user.save()
        self.assertIn("NO usable password", self.run_cmd("LG001"))

    def test_check_password_prompt(self):
        user = User.objects.create_user("lg2", password=GOOD_PASSWORD)
        EmployeeProfile.objects.create(user=user, employee_id="LG002", company_email="lg2@vishakha.com")
        with mock.patch("employees.management.commands.diagnose_login.getpass", return_value=GOOD_PASSWORD):
            self.assertIn("password is CORRECT", self.run_cmd("LG002", "--check-password"))
        with mock.patch("employees.management.commands.diagnose_login.getpass", return_value="wrong-one"):
            self.assertIn("does NOT match", self.run_cmd("LG002", "--check-password"))


class MailerReliabilityTests(TestCase):
    def send(self, **kw):
        from employees import mailer
        defaults = dict(purpose="registration", recipient="who@vishakha.com", subject="S", text_body="T")
        defaults.update(kw)
        return mailer.send_tracked(**defaults)

    def test_transient_failures_are_retried_until_it_works(self):
        import smtplib
        from django.core.mail import EmailMultiAlternatives
        calls = {"n": 0}
        real_send = EmailMultiAlternatives.send

        def flaky(message, *a, **k):
            calls["n"] += 1
            if calls["n"] < 3:
                raise smtplib.SMTPServerDisconnected("connection lost")
            return real_send(message, *a, **k)

        with mock.patch("django.core.mail.EmailMultiAlternatives.send", flaky), mock.patch("employees.mailer.time.sleep") as nap:
            self.assertTrue(self.send())
        self.assertEqual(len(mail.outbox), 1)
        row = EmailDelivery.objects.get()
        self.assertEqual((row.status, row.attempts), ("sent", 3))
        self.assertEqual(nap.call_count, 2)

    def test_permanent_errors_are_not_retried_and_are_logged_with_the_reason(self):
        import smtplib
        error = smtplib.SMTPAuthenticationError(535, b"5.7.139 Authentication unsuccessful")
        with mock.patch("django.core.mail.EmailMultiAlternatives.send", side_effect=error) as send, \
                mock.patch("employees.mailer.time.sleep"):
            self.assertFalse(self.send())
        self.assertEqual(send.call_count, 1)
        row = EmailDelivery.objects.get()
        self.assertEqual((row.status, row.attempts), ("failed", 1))
        self.assertIn("535", row.error)

    def test_gives_up_after_three_attempts_and_logs_it(self):
        with mock.patch("django.core.mail.EmailMultiAlternatives.send", side_effect=TimeoutError("slow")) as send, \
                mock.patch("employees.mailer.time.sleep"):
            self.assertFalse(self.send())
        self.assertEqual(send.call_count, 3)
        self.assertEqual(EmailDelivery.objects.get().attempts, 3)

    def test_hourly_limit_is_counted_in_the_database_and_logged(self):
        results = [self.send() for _ in range(7)]
        self.assertEqual(results, [True] * 5 + [False] * 2)
        self.assertEqual(EmailDelivery.objects.filter(status="throttled").count(), 2)
        self.assertTrue(self.send(recipient="someone.else@vishakha.com"))            # other address unaffected
        self.assertTrue(self.send(purpose="password_reset"))                           # other kind unaffected

    def test_a_broken_log_table_never_blocks_the_mail(self):
        with mock.patch("employees.mailer.EmailDelivery.objects.create", side_effect=RuntimeError("no table")), \
                mock.patch("employees.mailer.EmailDelivery.objects.filter", side_effect=RuntimeError("no table")):
            self.assertTrue(self.send())
        self.assertEqual(len(mail.outbox), 1)


class EmailAdminAndCommandTests(TestCase):
    def test_delivery_log_is_visible_to_admins_but_read_only(self):
        admin_user = User.objects.create_superuser("log_admin", "log_admin@vishakha.com", GOOD_PASSWORD)
        self.client.force_login(admin_user)
        EmailDelivery.objects.create(purpose="registration", recipient="x@vishakha.com", status="failed", attempts=3, error="TimeoutError")
        page = self.client.get(reverse("admin:employees_emaildelivery_changelist"))
        self.assertContains(page, "x@vishakha.com")
        self.assertContains(page, "TimeoutError")
        self.assertEqual(self.client.get(reverse("admin:employees_emaildelivery_add")).status_code, 403)

    def test_email_log_command(self):
        EmailDelivery.objects.create(purpose="password_reset", recipient="y@vishakha.com", status="sent", attempts=1)
        out = io.StringIO()
        call_command("email_log", "--recipient", "y@vishakha.com", stdout=out)
        self.assertIn("Password reset link", out.getvalue())
        self.assertIn("sent", out.getvalue())

    def test_diagnose_login_explains_and_can_send_the_reset_mail(self):
        user = User.objects.create_user("dg1", password=GOOD_PASSWORD)
        EmployeeProfile.objects.create(user=user, employee_id="DG001", company_email="dg1@vishakha.com")
        out = io.StringIO()
        call_command("diagnose_login", "DG001", "--send-reset", "--base-url", "https://portal.example.test", stdout=out)
        text = out.getvalue()
        self.assertIn("a reset link WOULD be sent to dg1@vishakha.com", text)
        self.assertIn("send result: sent", text)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("https://portal.example.test/accounts/password-reset/", mail.outbox[0].body)
        out = io.StringIO()
        call_command("diagnose_login", "NOPE-ID", stdout=out)
        self.assertIn("NOTHING can be sent", out.getvalue())
