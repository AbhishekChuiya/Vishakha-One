import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from portal.models import CompanyApplication

User = get_user_model()
PW = "cm-shell-test-password-4471-x"
MEDIA = tempfile.mkdtemp(prefix="vone-cm-media-")


def png():
    b = io.BytesIO(); Image.new("RGB", (256, 256), (10, 120, 200)).save(b, "PNG"); return b.getvalue()


@override_settings(MEDIA_ROOT=MEDIA)
class CmShellAndLogoTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass(); shutil.rmtree(MEDIA, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("cmsuper", "s@vishakha.com", PW)
        cls.plain = User.objects.create_user("cmplain", password=PW)
        cls.logo_user = User.objects.create_user("cmlogo", password=PW)
        cls.logo_user.user_permissions.add(Permission.objects.get(codename="change_companyapplication"))
        cls.app = CompanyApplication.objects.create(name="Logo CM App", url="https://example.com")

    def login(self, user):
        c = Client(); c.force_login(user); return c

    def test_pages_use_new_shell_and_render(self):
        c = self.login(self.admin)
        for name, args in [("dashboard", []), ("list", ["announcements"]), ("new", ["announcements"]),
                           ("canteen_menu", []), ("app_logos", []), ("announcement_overview", []),
                           ("notification_center", []), ("approval_queue", []), ("approval_analytics", [])]:
            r = c.get(reverse(f"content_manager:{name}", args=args))
            self.assertEqual(r.status_code, 200, name)
            self.assertContains(r, "vone_cm.css", msg_prefix=name)
            self.assertContains(r, 'class="vx-side"', msg_prefix=name)

    def test_login_page_uses_new_design(self):
        r = Client().get(reverse("content_manager:login"))
        self.assertContains(r, "vone_cm.css")
        self.assertContains(r, "Sign in to Content Manager")

    def test_logo_page_requires_permission(self):
        self.assertEqual(self.login(self.plain).get(reverse("content_manager:app_logos")).status_code, 403)
        self.assertEqual(self.login(self.logo_user).get(reverse("content_manager:app_logos")).status_code, 200)

    def test_upload_replace_and_remove_logo(self):
        c = self.login(self.logo_user); url = reverse("content_manager:app_logos")
        r = c.post(url, {"app_id": self.app.pk, "logo": SimpleUploadedFile("a.png", png(), "image/png")})
        self.assertEqual(r.status_code, 302)
        self.app.refresh_from_db(); self.assertTrue(self.app.logo)
        c.post(url, {"app_id": self.app.pk, "remove": "1"})
        self.app.refresh_from_db(); self.assertFalse(self.app.logo)

    def test_non_image_is_rejected(self):
        c = self.login(self.logo_user)
        c.post(reverse("content_manager:app_logos"), {"app_id": self.app.pk,
               "logo": SimpleUploadedFile("evil.png", b"<html>not an image</html>", "image/png")})
        self.app.refresh_from_db(); self.assertFalse(self.app.logo)
