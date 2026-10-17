from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('contenthub', '0004_contentauditevent'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(
        name='ApprovalReminderDelivery',
        fields=[
            ('id', models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
            ('section', models.CharField(max_length=30)),
            ('object_id', models.PositiveIntegerField()),
            ('submitted_at', models.DateTimeField()),
            ('threshold_hours', models.PositiveSmallIntegerField()),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
        ],
        options={'constraints': [models.UniqueConstraint(fields=('recipient','section','object_id','submitted_at','threshold_hours'), name='unique_approval_reminder_delivery')]},
    )]
