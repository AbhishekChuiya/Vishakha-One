from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('contenthub', '0006_homepage_content_types')]
    operations = [
        migrations.AddField(
            model_name='resource',
            name='cover_image',
            field=models.ImageField(upload_to='content/resource_covers/', blank=True),
        ),
    ]
