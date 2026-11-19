import io
import json
import os
import shutil
import tempfile
import zipfile
from datetime import timedelta
from unittest import mock

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from contenthub.content_transfer import BundleError, import_bundle
from contenthub.models import Announcement, CanteenDay, NewJoiner, Resource
from portal.models import CompanyApplication

MEDIA = tempfile.mkdtemp(prefix="vone-xfer-media-")
OUT = tempfile.mkdtemp(prefix="vone-xfer-out-")


@override_settings(MEDIA_ROOT=MEDIA)
class ContentTransferTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)
        shutil.rmtree(OUT, ignore_errors=True)

    def _seed(self):
        when = timezone.now() - timedelta(days=3)
        r = Resource(title="Leave Policy", kind="policy", is_published=True, published_at=when)
        r.file.save("leave.pdf", ContentFile(b"%PDF-1.4 hello"), save=False)
        r.save()
        Announcement.objects.create(title="Diwali", category="news", is_published=True, published_at=when, summary="Happy")
        CanteenDay.objects.create(date=timezone.localdate(), lunch_roti="Phulka")
        NewJoiner.objects.create(employee_name="Asha", designation="HR", department="HR", published_at=when, is_published=True)
        CompanyApplication.objects.create(name="Round Trip App", url="https://example.com")
        return os.path.join(OUT, "b.zip")

    def _wipe(self):
        for m in (Resource, Announcement, CanteenDay, NewJoiner):
            m.objects.all().delete()
        CompanyApplication.objects.filter(name="Round Trip App").delete()
        shutil.rmtree(MEDIA, ignore_errors=True)
        os.makedirs(MEDIA, exist_ok=True)

    def test_round_trip_with_files_and_no_duplicates(self):
        path = self._seed()
        call_command("export_content", path, stdout=io.StringIO())
        with zipfile.ZipFile(path) as z:
            self.assertIn("media/content/resources/leave.pdf", z.namelist())
            self.assertNotIn("password", z.read("content.json").decode().lower())
        self._wipe()
        call_command("import_content", path, stdout=io.StringIO())
        r = Resource.objects.get(title="Leave Policy")
        self.assertTrue(r.is_published)
        with open(os.path.join(MEDIA, r.file.name), "rb") as fh:
            self.assertEqual(fh.read(), b"%PDF-1.4 hello")
        self.assertEqual(Announcement.objects.count(), 1)
        self.assertEqual(CanteenDay.objects.get().lunch_roti, "Phulka")
        call_command("import_content", path, stdout=io.StringIO())  # second run
        self.assertEqual(Resource.objects.count(), 1)
        self.assertEqual(NewJoiner.objects.count(), 1)

    def test_dry_run_changes_nothing(self):
        path = self._seed()
        call_command("export_content", path, stdout=io.StringIO())
        self._wipe()
        out = io.StringIO()
        call_command("import_content", path, "--dry-run", stdout=out)
        self.assertIn("DRY RUN", out.getvalue())
        self.assertEqual(Resource.objects.count(), 0)
        self.assertFalse(os.path.exists(os.path.join(MEDIA, "content")))

    def test_bundle_with_path_traversal_is_rejected(self):
        path = os.path.join(OUT, "evil.zip")
        payload = {"format": "vishakha-one-content/1", "models": {"resources": [
            {"title": "X", "kind": "policy", "file": "../../evil.txt", "published_at": "2025-01-01T00:00:00Z"}]}}
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("content.json", json.dumps(payload))
        with self.assertRaises(BundleError):
            import_bundle(path)
        self.assertEqual(Resource.objects.count(), 0)

    def test_non_bundle_is_refused(self):
        path = os.path.join(OUT, "junk.zip")
        with open(path, "wb") as f:
            f.write(b"not a zip")
        with self.assertRaises(CommandError):
            call_command("import_content", path)


class ImportDoesNotPushTests(TestCase):
    def test_imported_notices_are_marked_as_already_announced(self):
        import json as _json, zipfile as _zf
        path = os.path.join(tempfile.mkdtemp(prefix="vone-xfer-push-"), "push.zip")
        payload = {"format": "vishakha-one-content/1", "models": {"announcements": [
            {"title": "Old circular", "category": "circular", "published_at": "2025-01-01T00:00:00Z", "is_published": True, "approval_status": "approved"}]}}
        with _zf.ZipFile(path, "w") as z:
            z.writestr("content.json", _json.dumps(payload))
        with override_settings(VONE_VAPID_PUBLIC_KEY="x", VONE_VAPID_PRIVATE_KEY="y"):
            with mock.patch("portal.push.send_to_everyone") as send:
                import_bundle(path)
        send.assert_not_called()
        self.assertIsNotNone(Announcement.objects.get().push_sent_at)
