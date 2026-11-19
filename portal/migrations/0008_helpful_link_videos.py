from django.db import migrations


def point_videos_to_library(apps, schema_editor):
    HelpfulLink = apps.get_model("portal", "HelpfulLink")
    HelpfulLink.objects.filter(title="Videos", url="/documents/?category=video").update(url="/videos/")


class Migration(migrations.Migration):
    dependencies = [("portal", "0007_push")]
    operations = [migrations.RunPython(point_videos_to_library, migrations.RunPython.noop)]
