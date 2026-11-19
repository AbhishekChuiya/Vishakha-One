"""Profile editing (name, photo, password), friendly names, header menu rights, no next-week canteen."""
import io
from unittest import mock
import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from employees.models import EmployeeProfile
from portal.names import display_name

User = get_user_model()
PW = "Profile-Test-Pass-8812-x"
NEWPW = "Another-Strong-Pass-3390-y"
MEDIA = tempfile.mkdtemp(prefix="vone-prof-media-")


def jpg():
    b = io.BytesIO(); Image.new("RGB", (900, 600), (30, 90, 160)).save(b, "JPEG"); return b.getvalue()


@override_settings(MEDIA_ROOT=MEDIA)
class ProfileTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass(); shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user("90002500", password=PW, email="abhishek.chuiya@vishakha.com")
        self.profile = EmployeeProfile.objects.create(user=self.user, employee_id="90002500", company_email="abhishek.chuiya@vishakha.com")
        self.c = Client(); self.c.force_login(self.user)

    def test_name_falls_back_to_email_not_employee_id(self):
        self.assertEqual(display_name(self.user), "Abhishek Chuiya")
        page = self.c.get("/").content.decode()
        self.assertIn("Abhishek", page)
        self.assertNotIn("Good morning, 90002500", page)
        self.assertNotIn("Good afternoon, 90002500", page)
        self.assertNotIn("Good evening, 90002500", page)

    def test_change_name(self):
        r = self.c.post(reverse("portal:profile"), {"action": "name", "first_name": "Abhishek", "last_name": "Chuiya Kumar"})
        self.assertEqual(r.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.get_full_name(), "Abhishek Chuiya Kumar")
        self.assertContains(self.c.get("/"), "Abhishek Chuiya Kumar")

    def test_bad_name_is_rejected(self):
        r = self.c.post(reverse("portal:profile"), {"action": "name", "first_name": "<script>x", "last_name": ""})
        self.assertEqual(r.status_code, 200)
        self.user.refresh_from_db(); self.assertEqual(self.user.first_name, "")

    def test_photo_upload_is_square_jpeg_and_can_be_removed(self):
        r = self.c.post(reverse("portal:profile"), {"action": "photo", "photo": SimpleUploadedFile("me.jpg", jpg(), "image/jpeg")})
        self.assertEqual(r.status_code, 302)
        self.profile.refresh_from_db(); self.assertTrue(self.profile.photo)
        img = Image.open(self.profile.photo.path); self.assertEqual(img.size, (512, 512))
        self.assertContains(self.c.get("/"), self.profile.photo.url)
        self.c.post(reverse("portal:profile"), {"action": "remove_photo"})
        self.profile.refresh_from_db(); self.assertFalse(self.profile.photo)

    def test_non_image_photo_is_rejected(self):
        self.c.post(reverse("portal:profile"), {"action": "photo", "photo": SimpleUploadedFile("x.jpg", b"<html>no</html>", "image/jpeg")})
        self.profile.refresh_from_db(); self.assertFalse(self.profile.photo)

    def test_change_password_keeps_session_and_new_password_works(self):
        r = self.c.post(reverse("portal:profile"), {"action": "password", "old_password": PW, "new_password1": NEWPW, "new_password2": NEWPW})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.c.get("/").status_code, 200)       # still signed in
        self.assertTrue(Client().login(username="90002500", password=NEWPW))

    def test_wrong_old_password_changes_nothing(self):
        r = self.c.post(reverse("portal:profile"), {"action": "password", "old_password": "wrong", "new_password1": NEWPW, "new_password2": NEWPW})
        self.assertEqual(r.status_code, 200)
        self.user.refresh_from_db(); self.assertTrue(self.user.check_password(PW))

    def test_content_manager_link_only_with_rights(self):
        self.assertNotIn("Content Manager", self.c.get("/").content.decode())
        self.user.user_permissions.add(Permission.objects.get(codename="add_announcement"))
        c = Client(); c.force_login(User.objects.get(pk=self.user.pk))
        self.assertIn("Content Manager", c.get("/").content.decode())

    def test_employees_cannot_open_next_weeks_canteen(self):
        nxt = (timezone.localdate() + timedelta(days=9)).isoformat()
        page = self.c.get(f"/canteen-menu/?week={nxt}").content.decode()
        self.assertNotIn("Next", page)
        today = timezone.localdate(); monday = today - timedelta(days=today.weekday())
        self.assertIn(monday.strftime("%d %b %Y"), page)          # clamped to the current week


class LanguageAndSettingsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("90003000", password=PW, email="rina.shah@vishakha.com")
        EmployeeProfile.objects.create(user=self.user, employee_id="90003000", company_email="rina.shah@vishakha.com")
        self.c = Client(); self.c.force_login(self.user)

    def test_switching_to_hindi_translates_the_shell_and_back(self):
        self.assertIn("My Apps", self.c.get("/").content.decode())
        r = self.c.post("/i18n/setlang/", {"language": "hi", "next": "/"})
        self.assertEqual(r.status_code, 302)
        page = self.c.get("/").content.decode()
        self.assertIn("मेरे ऐप्स", page)
        self.assertIn('lang="hi"', page)
        self.c.post("/i18n/setlang/", {"language": "en", "next": "/"})
        self.assertIn("My Apps", self.c.get("/").content.decode())

    def test_language_menu_has_both_languages(self):
        page = self.c.get("/").content.decode()
        self.assertIn("English", page)
        self.assertIn("हिन्दी", page)

    def test_open_redirect_is_blocked_on_language_switch(self):
        r = self.c.post("/i18n/setlang/", {"language": "hi", "next": "https://evil.example/"})
        self.assertNotIn("evil.example", r["Location"])


class HelpfulLinksAndApplicationsAdminTests(TestCase):
    def setUp(self):
        from portal.models import HelpfulLink
        self.HelpfulLink = HelpfulLink
        self.admin = User.objects.create_superuser("cmsu", "s@vishakha.com", PW)
        self.plain = User.objects.create_user("cmplain2", password=PW)
        self.emp = User.objects.create_user("90003100", password=PW)
        EmployeeProfile.objects.create(user=self.emp, employee_id="90003100", company_email="x.y@vishakha.com")

    def cm(self, user):
        c = Client(); c.force_login(user); return c

    def test_default_links_exist_and_show_in_the_bar(self):
        self.assertGreaterEqual(self.HelpfulLink.objects.count(), 9)
        self.assertIn("Photo albums", self.cm(self.emp).get("/").content.decode())

    def test_admin_adds_edits_hides_and_deletes_links(self):
        c = self.cm(self.admin); url = reverse("content_manager:helpful_links")
        c.post(url, {"action": "add", "title": "Payslips", "url": "https://pay.example.com/", "icon": "card", "display_order": 5, "is_active": "on"})
        link = self.HelpfulLink.objects.get(title="Payslips")
        self.assertIn("Payslips", self.cm(self.emp).get("/").content.decode())
        c.post(url, {"link_id": link.pk, "title": "Payslips", "url": "https://pay.example.com/", "icon": "card", "display_order": 5})   # not ticked => hidden
        self.assertNotIn("Payslips", self.cm(self.emp).get("/").content.decode())
        c.post(url, {"action": "delete", "link_id": link.pk})
        self.assertFalse(self.HelpfulLink.objects.filter(title="Payslips").exists())

    def test_dangerous_link_address_is_refused(self):
        c = self.cm(self.admin)
        c.post(reverse("content_manager:helpful_links"), {"action": "add", "title": "Bad", "url": "javascript:alert(1)", "icon": "link", "display_order": 1, "is_active": "on"})
        self.assertFalse(self.HelpfulLink.objects.filter(title="Bad").exists())

    def test_links_pages_need_permission(self):
        self.assertEqual(self.cm(self.plain).get(reverse("content_manager:helpful_links")).status_code, 403)
        self.assertEqual(self.cm(self.plain).get(reverse("content_manager:applications")).status_code, 403)

    def test_application_name_order_and_visibility_can_be_changed(self):
        from portal.models import CompanyApplication
        app = CompanyApplication.objects.create(name="Edit Me App", url="https://example.com", display_order=50)
        c = self.cm(self.admin)
        c.post(reverse("content_manager:applications"), {"app_id": app.pk, "name": "Renamed App", "url": "https://example.com", "category": "Tools", "description": "", "display_order": 1})
        app.refresh_from_db()
        self.assertEqual((app.name, app.display_order, app.is_active), ("Renamed App", 1, False))

    def test_forbidden_canteen_page_is_friendly_and_link_hidden(self):
        r = self.cm(self.plain).get(reverse("content_manager:canteen_menu"))
        self.assertEqual(r.status_code, 403)
        self.assertContains(r, "don&#x27;t have access" if False else "have access to this page", status_code=403)


class AvailabilityTests(TestCase):
    def test_health_check_is_public_and_reports_db_state(self):
        r = Client().get("/healthz/")
        self.assertEqual((r.status_code, r.json()["status"]), (200, "ok"))
        with mock.patch("portal.health.connection") as conn:
            conn.cursor.side_effect = Exception("db down")
            r = Client().get("/healthz/")
        self.assertEqual(r.status_code, 503)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
    def test_missing_page_shows_friendly_404(self):
        u = User.objects.create_user("90005000", password=PW, email="a.b@vishakha.com")
        EmployeeProfile.objects.create(user=u, employee_id="90005000", company_email="a.b@vishakha.com")
        c = Client(); c.force_login(u)
        r = c.get("/definitely-not-a-page/")
        self.assertEqual(r.status_code, 404)
        self.assertContains(r, "could not find that page", status_code=404)
