from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('contenthub', '0002_approval_workflow'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name='ContentNotification', fields=[
        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        ('section', models.CharField(max_length=30)),
        ('object_id', models.PositiveIntegerField()),
        ('title', models.CharField(max_length=220)),
        ('message', models.TextField(blank=True)),
        ('kind', models.CharField(max_length=30)),
        ('is_read', models.BooleanField(default=False, db_index=True)),
        ('created_at', models.DateTimeField(auto_now_add=True)),
        ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
        ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='content_notifications', to=settings.AUTH_USER_MODEL)),
    ], options={'ordering': ('-created_at',)})]
