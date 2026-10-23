"""A1.15 regression tests. Uses Django's isolated test database; never production data."""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from contenthub.models import Announcement, AnnouncementReceipt, CanteenDay

User = get_user_model()


class AnnouncementWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="a115_employee", password="test-password-not-for-production")
        cls.notice = Announcement.objects.create(
            title="A1.15 Notice", summary="UAT announcement", category="announcement",
            approval_status="approved", is_published=True, published_at=timezone.now() - timedelta(minutes=1),
        )

    def test_homepage_and_feed_show_unread_notice(self):
        self.assertContains(self.client.get(reverse("portal:home")), self.notice.title)
        payload = self.client.get(reverse("portal:notification_feed")).json()
        self.assertEqual(payload["unread_count"], 1)

    def test_anonymous_dismiss_persists_in_browser_session(self):
        url = reverse("portal:notification_read", args=[self.notice.pk])
        response = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(self.client.get(reverse("portal:notification_feed")).json()["unread_count"], 0)
        # Reading a notification does not unpublish it from Latest updates.
        self.assertContains(self.client.get(reverse("portal:home")), "A1.15 Notice")
        # Different anonymous browser: dismissal is not shared.
        self.assertEqual(Client().get(reverse("portal:notification_feed")).json()["unread_count"], 1)

    def test_signed_in_read_receipt_and_count(self):
        self.client.force_login(self.user)
        url = reverse("portal:notification_read", args=[self.notice.pk])
        response = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AnnouncementReceipt.objects.filter(
            recipient=self.user, announcement=self.notice).exists())
        self.assertEqual(self.client.get(reverse("portal:notification_feed")).json()["unread_count"], 0)
        # Reading a notification does not unpublish it from Latest updates.
        self.assertContains(self.client.get(reverse("portal:home")), "A1.15 Notice")
        self.assertContains(self.client.get(reverse("portal:notifications")), "A1.15 Notice")

    def test_read_endpoint_is_post_only_and_csrf_protected(self):
        url = reverse("portal:notification_read", args=[self.notice.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        csrf_client = Client(enforce_csrf_checks=True)
        self.assertEqual(csrf_client.post(url).status_code, 403)

    def test_unpublished_notice_disappears_everywhere(self):
        self.notice.is_published = False
        self.notice.save()
        self.assertEqual(self.client.get(reverse("portal:notification_feed")).json()["unread_count"], 0)
        self.assertNotContains(self.client.get(reverse("portal:notifications")), "A1.15 Notice")
        self.assertNotContains(self.client.get(reverse("portal:home")), "A1.15 Notice")

    def test_expired_notice_not_in_feed(self):
        self.notice.expires_at = timezone.now() - timedelta(minutes=1)
        self.notice.save()
        self.assertEqual(self.client.get(reverse("portal:notification_feed")).json()["unread_count"], 0)


class CanteenWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.employee = User.objects.create_user(username="a115_canteen_user", password="test-password-not-for-production")
        cls.manager = User.objects.create_superuser(username="a115_manager", email="a115@example.invalid",
                                                    password="test-password-not-for-production")

    def test_menu_is_visible_to_employee_and_anonymous(self):
        today = timezone.localdate()
        monday = today - timedelta(days=today.weekday())
        CanteenDay.objects.create(date=monday, lunch_veg_dal="A1.15 Special Lunch")
        url = reverse("portal:canteen_menu") + "?week=" + monday.isoformat()
        self.assertContains(self.client.get(url), "A1.15 Special Lunch")
        self.client.force_login(self.employee)
        self.assertContains(self.client.get(url), "A1.15 Special Lunch")

    def test_closed_canteen_day_does_not_mean_office_holiday(self):
        today = timezone.localdate()
        monday = today - timedelta(days=today.weekday())
        CanteenDay.objects.create(date=monday, is_holiday=True)
        response = self.client.get(reverse("portal:canteen_menu") + "?week=" + monday.isoformat())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Canteen closed")

    def test_employee_cannot_edit_canteen(self):
        url = reverse("content_manager:canteen_menu")
        self.client.force_login(self.employee)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_superuser_can_open_canteen_editor(self):
        url = reverse("content_manager:canteen_menu")
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(url).status_code, 200)


class PortalSmokeTests(TestCase):
    def test_important_employee_pages_render(self):
        for name in ("portal:home", "portal:profile", "portal:notifications",
                     "portal:canteen_menu"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)
