"""Priority highlighting, thought of the day, archiving, expiry, video library, collateral, bookmarks, cache busting."""
import io
import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from contenthub.models import Announcement, DailyThought, Resource, ResourceBookmark
from employees.models import EmployeeProfile

User = get_user_model()
PW = "Library-Test-Pass-5581-x"


def pub(model, **kw):
    kw.setdefault("is_published", True)
    kw.setdefault("approval_status", "approved")
    kw.setdefault("published_at", timezone.now() - timedelta(hours=1))
    return model.objects.create(**kw)


class LibraryTests(TestCase):
    def setUp(self):
        self.emp = User.objects.create_user("90007000", password=PW, email="l.t@vishakha.com")
        EmployeeProfile.objects.create(user=self.emp, employee_id="90007000", company_email="l.t@vishakha.com")
        self.other = User.objects.create_user("90007001", password=PW, email="o.t@vishakha.com")
        EmployeeProfile.objects.create(user=self.other, employee_id="90007001", company_email="o.t@vishakha.com")
        self.c = Client(); self.c.force_login(self.emp)

    # ---- priority ----
    def test_priority_news_is_highlighted_and_listed_first(self):
        pub(Announcement, title="Plain old news", category="news", published_at=timezone.now())
        pub(Announcement, title="Big urgent circular", category="circular", priority="urgent", published_at=timezone.now() - timedelta(days=5))
        pub(Announcement, title="Important leadership note", category="leadership", priority="important", published_at=timezone.now() - timedelta(days=3))
        page = self.c.get("/news/").content.decode()
        self.assertLess(page.index("Big urgent circular"), page.index("Important leadership note"))
        self.assertLess(page.index("Important leadership note"), page.index("Plain old news"))
        self.assertIn("prio-urgent", page); self.assertIn("prio-important", page)
        home = self.c.get("/").content.decode()
        self.assertIn("prio-tag urgent", home)

    def test_leadership_and_circular_filters(self):
        pub(Announcement, title="CEO message", category="leadership")
        pub(Announcement, title="HR circular", category="circular")
        self.assertIn("CEO message", self.c.get("/news/?category=leadership").content.decode())
        self.assertNotIn("HR circular", self.c.get("/news/?category=leadership").content.decode())
        self.assertIn("Circulars", self.c.get("/news/").content.decode())

    # ---- thought of the day ----
    def test_thought_of_the_day_shows_today_and_hides_stale(self):
        pub(DailyThought, title="Well begun is half done", author="Aristotle", show_on=timezone.localdate())
        page = self.c.get("/").content.decode()
        self.assertIn("Well begun is half done", page); self.assertIn("Aristotle", page)
        DailyThought.objects.update(show_on=timezone.localdate() - timedelta(days=30))
        self.assertNotIn("Well begun is half done", self.c.get("/").content.decode())

    def test_future_dated_thought_waits_for_its_day(self):
        pub(DailyThought, title="Tomorrow thought", show_on=timezone.localdate() + timedelta(days=1))
        self.assertNotIn("Tomorrow thought", self.c.get("/").content.decode())

    # ---- expiry and archive ----
    def test_expired_and_archived_documents_disappear(self):
        pub(Resource, title="Live doc", kind="document", external_url="https://e.com/a")
        pub(Resource, title="Expired doc", kind="document", external_url="https://e.com/b", expires_at=timezone.now() - timedelta(minutes=5))
        pub(Resource, title="Archived doc", kind="document", external_url="https://e.com/c", is_archived=True)
        pub(Resource, title="Not yet effective", kind="document", external_url="https://e.com/d", published_at=timezone.now() + timedelta(days=1))
        page = self.c.get("/documents/").content.decode()
        self.assertIn("Live doc", page)
        for gone in ("Expired doc", "Archived doc", "Not yet effective"):
            self.assertNotIn(gone, page)

    def test_auto_archive_command(self):
        old = pub(Resource, title="Long expired", kind="document", external_url="https://e.com/x", expires_at=timezone.now() - timedelta(days=40))
        recent = pub(Resource, title="Just expired", kind="document", external_url="https://e.com/y", expires_at=timezone.now() - timedelta(days=2))
        call_command("archive_expired_content", stdout=io.StringIO())
        old.refresh_from_db(); recent.refresh_from_db()
        self.assertTrue(old.is_archived); self.assertFalse(recent.is_archived)

    # ---- video library + collateral ----
    def test_video_library_has_four_video_types_and_filters(self):
        for kind in ("video", "training", "corporate_film", "event_video"):
            pub(Resource, title=f"Clip {kind}", kind=kind, external_url="https://e.com/v")
        pub(Resource, title="A brochure", kind="brochure", external_url="https://e.com/b")
        page = self.c.get("/videos/").content.decode()
        for kind in ("video", "training", "corporate_film", "event_video"):
            self.assertIn(f"Clip {kind}", page)
        self.assertNotIn("A brochure", page)
        self.assertIn("Training Content", page); self.assertIn("Corporate Films", page); self.assertIn("Event Videos", page)
        only = self.c.get("/videos/?category=training").content.decode()
        self.assertIn("Clip training", only); self.assertNotIn("Clip event_video", only)

    def test_collateral_shows_brochures_presentations_brand_with_download(self):
        r = Resource(title="Brand guide", kind="brand_material", is_published=True, approval_status="approved", published_at=timezone.now() - timedelta(hours=1))
        r.file.save("brand.pdf", SimpleUploadedFile("brand.pdf", b"%PDF-1.4"), save=True)
        pub(Resource, title="Deck", kind="presentation", external_url="https://e.com/deck")
        pub(Resource, title="Folder", kind="brochure", external_url="https://e.com/f")
        pub(Resource, title="Policy doc", kind="policy", external_url="https://e.com/p")
        page = self.c.get("/collateral/").content.decode()
        for t in ("Brand guide", "Deck", "Folder"):
            self.assertIn(t, page)
        self.assertNotIn("Policy doc", page)
        self.assertIn("download", page); self.assertIn("data-bookmark", page)
        r.file.delete(save=False)

    # ---- bookmarks ----
    def test_bookmark_toggle_page_and_privacy(self):
        doc = pub(Resource, title="Leave policy", kind="policy", external_url="https://e.com/lp")
        url = reverse("portal:bookmark_toggle", args=[doc.pk])
        self.assertTrue(self.c.post(url).json()["bookmarked"])
        self.assertIn("Leave policy", self.c.get("/bookmarks/").content.decode())
        other = Client(); other.force_login(self.other)
        self.assertNotIn("Leave policy", other.get("/bookmarks/").content.decode())     # private to each employee
        self.assertIn('aria-pressed="true"', self.c.get("/policies/").content.decode())
        self.assertFalse(self.c.post(url).json()["bookmarked"])
        self.assertEqual(ResourceBookmark.objects.count(), 0)

    def test_cannot_bookmark_hidden_documents_and_get_is_refused(self):
        hidden = pub(Resource, title="Hidden", kind="policy", external_url="https://e.com/h", is_archived=True)
        self.assertEqual(self.c.post(reverse("portal:bookmark_toggle", args=[hidden.pk])).status_code, 404)
        live = pub(Resource, title="Live", kind="policy", external_url="https://e.com/l")
        self.assertEqual(self.c.get(reverse("portal:bookmark_toggle", args=[live.pk])).status_code, 405)

    def test_archived_bookmarked_document_leaves_the_bookmarks_page(self):
        doc = pub(Resource, title="Will be archived", kind="policy", external_url="https://e.com/w")
        self.c.post(reverse("portal:bookmark_toggle", args=[doc.pk]))
        Resource.objects.filter(pk=doc.pk).update(is_archived=True)
        self.assertNotIn("Will be archived", self.c.get("/bookmarks/").content.decode())

    # ---- cache busting ----
    def test_assets_carry_a_content_fingerprint(self):
        html = self.c.get("/").content.decode()
        m = re.search(r'vone_ui\.css\?v=([0-9a-f]{10})', html)
        self.assertIsNotNone(m, "css link must carry a 10-char fingerprint, not a fixed number")
        self.assertNotIn("?v=1.0", html)


class ContentManagerLifecycleTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("cmroot", "r@vishakha.com", PW)
        self.editor = User.objects.create_user("cmeditor", password=PW)
        for code in ("view_resource", "add_resource", "change_resource"):
            self.editor.user_permissions.add(Permission.objects.get(codename=code))
        self.c = Client(); self.c.force_login(self.admin)

    def test_archive_and_restore_cycle(self):
        r = pub(Resource, title="Archive me", kind="document", external_url="https://e.com/a")
        url = reverse("content_manager:archive", args=["resources", r.pk])
        self.c.post(url)
        r.refresh_from_db(); self.assertTrue(r.is_archived); self.assertFalse(r.is_published)
        self.assertNotIn("Archive me", self.c.get(reverse("content_manager:list", args=["resources"])).content.decode())
        self.assertIn("Archive me", self.c.get(reverse("content_manager:list", args=["resources"]) + "?status=archived").content.decode())
        self.c.post(url)
        r.refresh_from_db(); self.assertFalse(r.is_archived); self.assertEqual(r.approval_status, "draft")

    def test_editors_without_approval_rights_cannot_archive(self):
        r = pub(Resource, title="Mine", kind="document", external_url="https://e.com/m")
        c = Client(); c.force_login(self.editor)
        self.assertEqual(c.post(reverse("content_manager:archive", args=["resources", r.pk])).status_code, 403)

    def test_document_expiry_must_follow_effective_date(self):
        now = timezone.now()
        data = {"title": "Policy X", "kind": "document", "external_url": "https://e.com/x", "display_order": 0, "save_action": "publish",
                "published_at": (now + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M"),
                "expires_at": (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")}
        r = self.c.post(reverse("content_manager:new", args=["resources"]), data)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "must be later than the effective")
        self.assertEqual(Resource.objects.count(), 0)

    def test_thought_of_the_day_is_a_content_manager_module(self):
        page = self.c.get(reverse("content_manager:dashboard")).content.decode()
        self.assertIn("Thought of the Day", page)
        r = self.c.post(reverse("content_manager:new", args=["thoughts"]),
                        {"title": "Be the change", "author": "Gandhi", "show_on": timezone.localdate().isoformat(), "display_order": 0, "save_action": "publish"})
        self.assertEqual(r.status_code, 302)
        t = DailyThought.objects.get()
        self.assertTrue(t.is_published)

    def test_scheduling_still_works_for_all_content(self):
        future = (timezone.now() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")
        r = self.c.post(reverse("content_manager:new", args=["announcements"]),
                        {"title": "Scheduled news", "category": "circular", "priority": "normal", "display_order": 0, "save_action": "schedule", "published_at": future})
        self.assertEqual(r.status_code, 302)
        a = Announcement.objects.get()
        self.assertTrue(a.is_published and a.published_at > timezone.now())
        self.assertIn("Scheduled news", self.c.get(reverse("content_manager:list", args=["announcements"]) + "?status=scheduled").content.decode())
