"""Portal regression tests for the login-required portal (Option A). Uses Django's isolated test database."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from contenthub.models import Announcement, AnnouncementReceipt, CanteenDay
from employees.models import EmployeeProfile

User = get_user_model()
PASSWORD = "test-password-not-for-production-7391"


def make_employee(username, employee_id, email):
    user = User.objects.create_user(username=username, password=PASSWORD)
    EmployeeProfile.objects.create(user=user, employee_id=employee_id, company_email=email)
    return user


class AnnouncementWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_employee("a115_employee", "A115001", "a115.employee@vishakha.com")
        cls.notice = Announcement.objects.create(
            title="A1.15 Notice", summary="UAT announcement", category="announcement",
            approval_status="approved", is_published=True, published_at=timezone.now() - timedelta(minutes=1),
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_homepage_and_feed_show_unread_notice(self):
        self.assertContains(self.client.get(reverse("portal:home")), self.notice.title)
        self.assertEqual(self.client.get(reverse("portal:notification_feed")).json()["unread_count"], 1)

    def test_anonymous_visitors_are_sent_to_sign_in(self):
        anonymous = Client()
        for url in (reverse("portal:home"), reverse("portal:notification_feed"), reverse("portal:notifications")):
            response = anonymous.get(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertIn(reverse("accounts:login"), response["Location"])
        post = anonymous.post(reverse("portal:notification_read", args=[self.notice.pk]))
        self.assertEqual(post.status_code, 302)
        self.assertFalse(AnnouncementReceipt.objects.exists())

    def test_signed_in_read_receipt_and_count(self):
        url = reverse("portal:notification_read", args=[self.notice.pk])
        response = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AnnouncementReceipt.objects.filter(recipient=self.user, announcement=self.notice).exists())
        self.assertEqual(self.client.get(reverse("portal:notification_feed")).json()["unread_count"], 0)
        # Reading a notification does not unpublish it from Latest updates.
        self.assertContains(self.client.get(reverse("portal:home")), "A1.15 Notice")
        self.assertContains(self.client.get(reverse("portal:notifications")), "A1.15 Notice")

    def test_read_state_is_per_employee(self):
        self.client.post(reverse("portal:notification_read", args=[self.notice.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        other = Client()
        other.force_login(make_employee("a115_other", "A115002", "a115.other@vishakha.com"))
        self.assertEqual(other.get(reverse("portal:notification_feed")).json()["unread_count"], 1)

    def test_read_endpoint_is_post_only_and_csrf_protected(self):
        url = reverse("portal:notification_read", args=[self.notice.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
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
        cls.employee = make_employee("a115_canteen_user", "A115003", "a115.canteen@vishakha.com")
        cls.manager = User.objects.create_superuser(username="a115_manager", email="a115@vishakha.com", password=PASSWORD)

    def monday(self):
        today = timezone.localdate()
        return today - timedelta(days=today.weekday())

    def test_menu_is_visible_to_signed_in_employees_only(self):
        monday = self.monday()
        CanteenDay.objects.create(date=monday, lunch_veg_dal="A1.15 Special Lunch")
        url = reverse("portal:canteen_menu") + "?week=" + monday.isoformat()
        self.assertEqual(self.client.get(url).status_code, 302)  # anonymous -> sign in
        self.client.force_login(self.employee)
        self.assertContains(self.client.get(url), "A1.15 Special Lunch")

    def test_closed_canteen_day_does_not_mean_office_holiday(self):
        monday = self.monday()
        CanteenDay.objects.create(date=monday, is_holiday=True)
        self.client.force_login(self.employee)
        response = self.client.get(reverse("portal:canteen_menu") + "?week=" + monday.isoformat())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Canteen closed")

    def test_employee_cannot_edit_canteen(self):
        self.client.force_login(self.employee)
        self.assertEqual(self.client.get(reverse("content_manager:canteen_menu")).status_code, 403)

    def test_superuser_can_open_canteen_editor(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(reverse("content_manager:canteen_menu")).status_code, 200)


class PortalSmokeTests(TestCase):
    def test_important_employee_pages_render_when_signed_in(self):
        self.client.force_login(make_employee("a115_smoke", "A115004", "a115.smoke@vishakha.com"))
        for name in ("portal:home", "portal:profile", "portal:notifications", "portal:canteen_menu"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_pages_require_sign_in(self):
        for name in ("portal:home", "portal:profile", "portal:notifications", "portal:canteen_menu"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 302)
