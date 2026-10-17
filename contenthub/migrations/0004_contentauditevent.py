from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('contenthub', '0003_contentnotification'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name='ContentAuditEvent', fields=[
        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        ('section', models.CharField(db_index=True, max_length=30)),
        ('object_id', models.PositiveIntegerField(db_index=True)),
        ('actor_label', models.CharField(blank=True, max_length=150)),
        ('action', models.CharField(max_length=24)),
        ('note', models.TextField(blank=True)),
        ('created_at', models.DateTimeField(auto_now_add=True)),
        ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
    ], options={'ordering': ('-created_at', '-pk'), 'indexes': [models.Index(fields=['section', 'object_id', '-created_at'], name='content_audit_lookup')]})]
