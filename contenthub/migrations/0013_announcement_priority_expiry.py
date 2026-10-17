from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('contenthub', '0012_announcement_receipts')]
    operations = [
        migrations.AddField(model_name='announcement', name='priority', field=models.CharField(max_length=12, default='normal', db_index=True, choices=[('normal','Normal'),('important','Important'),('urgent','Urgent')])),
        migrations.AddField(model_name='announcement', name='expires_at', field=models.DateTimeField(null=True, blank=True, help_text='Optional. Announcement disappears automatically after this time.')),
    ]
