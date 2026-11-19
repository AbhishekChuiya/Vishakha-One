"""Browser push: subscribe safely, send on approval events and new company notices, never break the workflow."""
import json
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from contenthub.models import Announcement, ContentNotification
from employees.models import EmployeeProfile
from portal.models import PushSubscription
from portal import push

User = get_user_model()
PW = "Push-Test-Pass-6612-x"
GOOD = "https://fcm.googleapis.com/fcm/send/abc123"


def keys():
    from io import StringIO
    out = StringIO(); call_command("generate_vapid_keys", stdout=out)
    lines = dict(l.split("=", 1) for l in out.getvalue().splitlines() if l.startswith("VONE_VAPID_"))
    return lines["VONE_VAPID_PUBLIC_KEY"], lines["VONE_VAPID_PRIVATE_KEY"]


PUB, PRIV = keys()
ON = dict(VONE_VAPID_PUBLIC_KEY=PUB, VONE_VAPID_PRIVATE_KEY=PRIV, VONE_VAPID_SUBJECT="mailto:it@vishakha.com", VONE_PUSH_SYNC=True)


def emp(username):
    u = User.objects.create_user(username, password=PW, email=f"{username}@vishakha.com")
    EmployeeProfile.objects.create(user=u, employee_id=username, company_email=f"{username}@vishakha.com")
    return u


def sub_body(endpoint=GOOD):
    return json.dumps({"subscription": {"endpoint": endpoint, "keys": {"p256dh": "BPk" + "x" * 40, "auth": "a" * 16}}})


@override_settings(**ON)
class PushTests(TestCase):
    def setUp(self):
        self.u = emp("90004001"); self.v = emp("90004002")
        self.c = Client(); self.c.force_login(self.u)

    def test_generated_keys_are_valid_for_the_push_library(self):
        from py_vapid import Vapid
        Vapid.from_string(PRIV)          # raises if the key is not usable

    def test_key_endpoint_reports_state(self):
        data = self.c.get(reverse("portal:push_key")).json()
        self.assertTrue(data["enabled"]); self.assertEqual(data["publicKey"], PUB)
        with override_settings(VONE_VAPID_PRIVATE_KEY=""):
            self.assertFalse(self.c.get(reverse("portal:push_key")).json()["enabled"])

    def test_subscribe_saves_and_moves_to_the_signed_in_user(self):
        r = self.c.post(reverse("portal:push_subscribe"), sub_body(), content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(PushSubscription.objects.get().user, self.u)
        other = Client(); other.force_login(self.v)               # same browser, another person signs in
        other.post(reverse("portal:push_subscribe"), sub_body(), content_type="application/json")
        self.assertEqual(PushSubscription.objects.count(), 1)
        self.assertEqual(PushSubscription.objects.get().user, self.v)

    def test_unknown_push_host_is_refused(self):
        for bad in ("https://169.254.169.254/x", "http://fcm.googleapis.com/x", "https://evil.example.com/x", "javascript:alert(1)"):
            r = self.c.post(reverse("portal:push_subscribe"), sub_body(bad), content_type="application/json")
            self.assertEqual(r.status_code, 400, bad)
        self.assertEqual(PushSubscription.objects.count(), 0)

    def test_unsubscribe_only_removes_own_subscription(self):
        self.c.post(reverse("portal:push_subscribe"), sub_body(), content_type="application/json")
        other = Client(); other.force_login(self.v)
        other.post(reverse("portal:push_unsubscribe"), json.dumps({"endpoint": GOOD}), content_type="application/json")
        self.assertEqual(PushSubscription.objects.count(), 1)
        self.c.post(reverse("portal:push_unsubscribe"), json.dumps({"endpoint": GOOD}), content_type="application/json")
        self.assertEqual(PushSubscription.objects.count(), 0)

    def test_anonymous_cannot_subscribe(self):
        r = Client().post(reverse("portal:push_subscribe"), sub_body(), content_type="application/json")
        self.assertIn(r.status_code, (302, 401))

    def test_service_worker_handles_push_and_clicks(self):
        code = Client().get("/service-worker.js").content.decode()
        self.assertIn("addEventListener('push'", code)
        self.assertIn("notificationclick", code)

    def _subscribe(self, user, endpoint):
        PushSubscription.objects.create(user=user, endpoint=endpoint, p256dh="p" * 20, auth="a" * 16)

    @mock.patch("pywebpush.webpush")
    def test_approval_request_approval_and_changes_are_pushed(self, wp):
        from contenthub.manager_views import notify
        self._subscribe(self.v, GOOD + "/v")
        rec = Announcement.objects.create(title="Diwali party", category="news")
        for kind, expect in (("pending", "Approval requested"), ("approved", "Content approved"), ("changes", "Changes requested")):
            wp.reset_mock()
            notify(self.v, self.u, "announcements", rec, kind, "msg")
            self.assertEqual(wp.call_count, 1, kind)
            payload = json.loads(wp.call_args.kwargs["data"])
            self.assertIn(expect, payload["title"]); self.assertIn("Diwali party", payload["title"])
        self.assertEqual(ContentNotification.objects.filter(recipient=self.v).count(), 3)

    @mock.patch("pywebpush.webpush")
    def test_company_notice_is_pushed_once_to_everyone(self, wp):
        self._subscribe(self.u, GOOD + "/u"); self._subscribe(self.v, GOOD + "/v")
        a = Announcement.objects.create(title="Plant shutdown", category="announcement", priority="urgent", is_published=True,
                                        approval_status="approved", published_at=timezone.now() - timedelta(minutes=1))
        self.assertEqual(wp.call_count, 2)
        self.assertIn("Urgent notice", json.loads(wp.call_args.kwargs["data"])["title"])
        a.summary = "edited"; a.save()                       # editing does not push again
        self.assertEqual(wp.call_count, 2)

    @mock.patch("pywebpush.webpush")
    def test_drafts_and_news_do_not_push(self, wp):
        self._subscribe(self.u, GOOD + "/u")
        Announcement.objects.create(title="Draft", category="announcement", is_published=False, approval_status="approved")
        Announcement.objects.create(title="Pending", category="announcement", is_published=True, approval_status="pending")
        Announcement.objects.create(title="Normal notice", category="announcement", priority="normal", is_published=True, approval_status="approved")
        Announcement.objects.create(title="Photos", category="gallery", is_published=True, approval_status="approved")
        self.assertEqual(wp.call_count, 0)

    @mock.patch("pywebpush.webpush")
    def test_news_leadership_circular_and_important_announcements_push(self, wp):
        self._subscribe(self.u, GOOD + "/u")
        now = timezone.now() - timedelta(minutes=1)
        for cat, prio, expect in (("news", "normal", "Company news"), ("leadership", "normal", "Leadership message"),
                                  ("circular", "normal", "Circular"), ("announcement", "important", "Important notice")):
            wp.reset_mock()
            Announcement.objects.create(title=f"T {cat}", category=cat, priority=prio, is_published=True, approval_status="approved", published_at=now)
            self.assertEqual(wp.call_count, 1, cat)
            self.assertIn(expect, json.loads(wp.call_args.kwargs["data"])["title"])

    @mock.patch("pywebpush.webpush")
    def test_archived_content_does_not_push(self, wp):
        self._subscribe(self.u, GOOD + "/u")
        Announcement.objects.create(title="Old", category="news", is_published=True, approval_status="approved", is_archived=True)
        self.assertEqual(wp.call_count, 0)

    @mock.patch("pywebpush.webpush")
    def test_scheduled_notice_is_sent_by_the_cron_command(self, wp):
        self._subscribe(self.u, GOOD + "/u")
        a = Announcement.objects.create(title="Scheduled", category="announcement", priority="important", is_published=True, approval_status="approved",
                                        published_at=timezone.now() + timedelta(hours=1))
        self.assertEqual(wp.call_count, 0)
        Announcement.objects.filter(pk=a.pk).update(published_at=timezone.now() - timedelta(minutes=1))
        call_command("send_due_notice_pushes")
        self.assertEqual(wp.call_count, 1)
        call_command("send_due_notice_pushes")
        self.assertEqual(wp.call_count, 1)

    @mock.patch("pywebpush.webpush", side_effect=Exception("push service down"))
    def test_a_failing_push_never_breaks_saving_or_approving(self, wp):
        from contenthub.manager_views import notify
        self._subscribe(self.v, GOOD + "/v")
        rec = Announcement.objects.create(title="Safe", category="news")
        notify(self.v, self.u, "announcements", rec, "approved", "msg")      # must not raise
        self.assertEqual(ContentNotification.objects.count(), 1)

    def test_gone_subscription_is_removed(self):
        from pywebpush import WebPushException
        self._subscribe(self.v, GOOD + "/gone")
        resp = mock.Mock(status_code=410)
        with mock.patch("pywebpush.webpush", side_effect=WebPushException("gone", response=resp)):
            push.send_to_users([self.v], "t", "b")
        self.assertEqual(PushSubscription.objects.count(), 0)

    @override_settings(VONE_VAPID_PUBLIC_KEY="", VONE_VAPID_PRIVATE_KEY="")
    def test_everything_is_a_quiet_no_op_without_keys(self):
        self._subscribe(self.v, GOOD + "/v")
        with mock.patch("pywebpush.webpush") as wp:
            Announcement.objects.create(title="Quiet", category="announcement", is_published=True, approval_status="approved",
                                        published_at=timezone.now() - timedelta(minutes=1))
        self.assertEqual(wp.call_count, 0)

    def test_pages_load_the_push_script_for_signed_in_users(self):
        self.assertContains(self.c.get("/"), "pwa/push.js")
        self.assertContains(self.c.get("/profile/"), "data-push-toggle")
