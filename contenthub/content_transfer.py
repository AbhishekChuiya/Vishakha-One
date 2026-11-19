"""Move published portal content (and its uploaded files) between Vishakha One installations.

Used by the `export_content` and `import_content` management commands. The bundle is a ZIP:

    content.json            records of every content model
    media/<relative path>   every uploaded file the records point to

Nothing user-related travels in the bundle: people-links (submitted_by, reviewed_by, updated_by)
are dropped, and employees, passwords, notifications, audit trail and read-receipts are never exported.
Importing matches records by a natural key, so running it twice does not create duplicates.
"""
import json
import os
import zipfile
from pathlib import PurePosixPath

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models, transaction

from django.utils import timezone

from contenthub.models import Announcement, CanteenDay, DailyThought, Event, JobOpening, NewJoiner, Resource
from portal.models import CompanyApplication, HelpfulLink

FORMAT = "vishakha-one-content/1"

# label -> (model, natural-key fields)
MODELS = {
    "applications": (CompanyApplication, ("name",)),
    "announcements": (Announcement, ("title", "category", "published_at")),
    "resources": (Resource, ("title", "kind", "published_at")),
    "jobs": (JobOpening, ("title", "department", "published_at")),
    "joiners": (NewJoiner, ("employee_name", "joining_date")),
    "events": (Event, ("title", "starts_at")),
    "canteen": (CanteenDay, ("date",)),
    "thoughts": (DailyThought, ("title", "show_on")),
    "links": (HelpfulLink, ("title",)),
}
SKIP_FIELDS = {"created_at", "updated_at", "submitted_by", "reviewed_by", "updated_by"}


class BundleError(Exception):
    pass


def _fields(model):
    return [f for f in model._meta.concrete_fields if not f.primary_key and f.name not in SKIP_FIELDS]


def _file_fields(model):
    return [f for f in _fields(model) if isinstance(f, models.FileField)]


def _value(field, obj):
    v = getattr(obj, field.name)
    if isinstance(field, models.FileField):
        return v.name if v else ""
    return v


def export_bundle(path, include_media=True, only=None):
    """Write the bundle; returns {'counts': {...}, 'files': n, 'missing': [...]}"""
    payload = {"format": FORMAT, "models": {}}
    media_paths = []
    counts = {}
    for label, (model, _key) in MODELS.items():
        if only and label not in only:
            continue
        rows = []
        for obj in model.objects.all().order_by("pk"):
            rows.append({f.name: _value(f, obj) for f in _fields(model)})
            for ff in _file_fields(model):
                name = getattr(obj, ff.name).name
                if name:
                    media_paths.append(name)
        payload["models"][label] = rows
        counts[label] = len(rows)
    missing, written = [], 0
    root = os.path.realpath(str(settings.MEDIA_ROOT))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("content.json", json.dumps(payload, cls=DjangoJSONEncoder, ensure_ascii=False, indent=1))
        if include_media:
            for rel in sorted(set(media_paths)):
                src = os.path.realpath(os.path.join(root, rel))
                if not src.startswith(root + os.sep) or not os.path.isfile(src):
                    missing.append(rel)
                    continue
                zf.write(src, "media/" + rel.replace("\\", "/"))
                written += 1
    return {"counts": counts, "files": written, "missing": missing}


def _safe_rel(name):
    p = PurePosixPath(name.replace("\\", "/"))
    if p.is_absolute() or ".." in p.parts or not p.parts:
        raise BundleError(f"Unsafe file path in bundle: {name!r}")
    return str(p)


def import_bundle(path, dry_run=False, include_media=True, skip_existing=False, only=None):
    try:
        zf = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as exc:
        raise BundleError(f"Not a readable ZIP bundle: {exc}")
    with zf:
        try:
            payload = json.loads(zf.read("content.json").decode("utf-8"))
        except KeyError:
            raise BundleError("content.json is missing - this is not a Vishakha One content bundle.")
        if payload.get("format") != FORMAT:
            raise BundleError("Unsupported bundle format: %r" % payload.get("format"))
        names = set(zf.namelist())
        summary = {label: {"created": 0, "updated": 0, "skipped": 0} for label in payload["models"]}
        media_to_copy = []
        with transaction.atomic():
            for label, rows in payload["models"].items():
                if only and label not in only:
                    continue
                if label not in MODELS:
                    continue
                model, key = MODELS[label]
                fmap = {f.name: f for f in _fields(model)}
                for row in rows:
                    data = {}
                    for name, field in fmap.items():
                        if name not in row:
                            continue
                        raw = row[name]
                        if isinstance(field, models.FileField):
                            data[name] = _safe_rel(raw) if raw else ""
                            if raw and include_media and ("media/" + data[name]) in names:
                                media_to_copy.append(data[name])
                        elif raw is None:
                            data[name] = None
                        else:
                            data[name] = field.to_python(raw)
                    if "push_sent_at" in fmap and not data.get("push_sent_at"):
                        data["push_sent_at"] = timezone.now()      # imported notices were announced long ago: never push them
                    lookup = {k: data[k] for k in key if k in data}
                    existing = model.objects.filter(**lookup).first()
                    if existing:
                        if skip_existing:
                            summary[label]["skipped"] += 1
                            continue
                        for k, v in data.items():
                            setattr(existing, k, v)
                        existing.save()
                        summary[label]["updated"] += 1
                    else:
                        model.objects.create(**data)
                        summary[label]["created"] += 1
            if dry_run:
                transaction.set_rollback(True)
        copied = 0
        if not dry_run and include_media:
            root = os.path.realpath(str(settings.MEDIA_ROOT))
            for rel in sorted(set(media_to_copy)):
                dest = os.path.realpath(os.path.join(root, rel))
                if not dest.startswith(root + os.sep):
                    raise BundleError(f"Unsafe file path in bundle: {rel!r}")
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with zf.open("media/" + rel) as src, open(dest, "wb") as out:
                    while True:
                        chunk = src.read(1 << 20)
                        if not chunk:
                            break
                        out.write(chunk)
                copied += 1
        else:
            copied = len(set(media_to_copy)) if dry_run else 0
    return {"summary": summary, "files": copied}
