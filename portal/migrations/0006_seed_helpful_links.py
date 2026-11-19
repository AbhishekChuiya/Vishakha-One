from django.db import migrations

DEFAULTS = [
    ("Search all", "/search/", "search"),
    ("Policies", "/policies/", "file"),
    ("New Joiners", "/joiners/", "users"),
    ("Internal Careers", "/careers/", "briefcase"),
    ("Documents", "/documents/", "folder"),
    ("Recognition", "/news/?category=recognition", "award"),
    ("Photo albums", "/news/?category=gallery", "image"),
    ("Videos", "/documents/?category=video", "play"),
    ("Bank Benefits", "/documents/?category=bank_benefit", "card"),
]


def seed(apps, schema_editor):
    HelpfulLink = apps.get_model("portal", "HelpfulLink")
    if HelpfulLink.objects.exists():
        return
    for order, (title, url, icon) in enumerate(DEFAULTS, start=1):
        HelpfulLink.objects.create(title=title, url=url, icon=icon, display_order=order * 10)


class Migration(migrations.Migration):
    dependencies = [("portal", "0005_helpfullink")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
