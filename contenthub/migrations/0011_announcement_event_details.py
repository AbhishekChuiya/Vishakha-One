from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('contenthub', '0010_newjoiner_introduction_document')]
    operations = [
        migrations.AddField(model_name='announcement', name='event_at', field=models.DateTimeField(blank=True, null=True, help_text='Optional event date and time (local timezone).')),
        migrations.AddField(model_name='announcement', name='event_location', field=models.CharField(blank=True, max_length=180, help_text='Optional venue or location.')),
    ]
