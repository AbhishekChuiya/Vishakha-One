"""Uploaded application logos and parity of the new home page with the earlier Vishakha One home."""
import io
import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from contenthub.models import CanteenDay
from employees.models import EmployeeProfile
from .models import CompanyApplication

User = get_user_model()
PASSWORD = "logo-test-password-5512-x"
TMP_MEDIA = tempfile.mkdtemp(prefix="vone-test-media-")


def png_bytes():
    buf = io.BytesIO()
    Image.new("RGBA", (300, 300), (200, 30, 40, 255)).save(buf, "PNG")
    return buf.getvalue()


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class LogoAndHomeTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("90002222", password=PASSWORD, first_name="Ravi")
        EmployeeProfile.objects.create(user=cls.user, employee_id="90002222", company_email="ravi@vishakha.com")
        cls.admin = User.objects.create_superuser("admin9", "a@vishakha.com", PASSWORD)

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def test_uploaded_logo_is_used_on_home_tile(self):
        app = CompanyApplication.objects.create(name="Logo Test App", url="https://example.com", category="Tools")
        app.logo.save("x.png", SimpleUploadedFile("x.png", png_bytes(), "image/png"))
        html = self.client.get(reverse("portal:home")).content.decode()
        self.assertIn(app.logo.url, html)
        self.assertTrue(app.logo_url.startswith("/media/app_logos/"))

    def test_app_without_logo_falls_back_to_initials(self):
        CompanyApplication.objects.create(name="Plain Test App", url="https://example.com")
        html = self.client.get(reverse("portal:home")).content.decode()
        self.assertIn("Plain Test App", html)
        self.assertNotIn("/media/app_logos/", html)

    def test_admin_can_upload_logo_with_preview(self):
        app = CompanyApplication.objects.create(name="Admin Logo App", url="https://example.com")
        c = Client(); c.force_login(self.admin)
        url = reverse("admin:portal_companyapplication_change", args=[app.pk])
        self.assertContains(c.get(url), 'name="logo"')
        r = c.post(url, {"name": "Admin Logo App", "description": "", "url": "https://example.com", "category": "",
                         "icon_path": "", "display_order": 0, "is_active": "on",
                         "logo": SimpleUploadedFile("l.png", png_bytes(), "image/png")})
        self.assertEqual(r.status_code, 302)
        app.refresh_from_db()
        self.assertTrue(app.logo)
        self.assertContains(c.get(reverse("admin:portal_companyapplication_changelist")), app.logo.url)

    def test_home_has_every_app_and_more_apps_button(self):
        for i in range(15):
            CompanyApplication.objects.create(name=f"Bulk App {i:02d}", url="https://example.com")
        html = self.client.get(reverse("portal:home")).content.decode()
        for i in range(15):
            self.assertIn(f"Bulk App {i:02d}", html)
        # every tile is in the page (phones show 4 first via CSS, with a "More apps" button)
        self.assertIn("data-apps-more", html)
        self.assertIn("data-side-collapse", html)

    def test_home_has_full_week_menu_and_resources(self):
        today = timezone.localdate()
        monday = today - timedelta(days=today.weekday())
        CanteenDay.objects.create(date=monday + timedelta(days=1), lunch_veg_dal="Paneer Test Curry", snacks="Samosa Test")
        html = self.client.get(reverse("portal:home")).content.decode()
        self.assertIn("What&#x27;s Cooking?", html.replace("'", "&#x27;"))
        self.assertIn("Paneer Test Curry", html)
        self.assertIn("Employee resources", html)
        self.assertGreaterEqual(html.count('role="tabpanel"'), 6)
