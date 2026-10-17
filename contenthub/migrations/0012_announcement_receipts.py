from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('contenthub', '0011_announcement_event_details'), ('auth', '0012_alter_user_first_name_max_length')]
    operations = [migrations.CreateModel(name='AnnouncementReceipt', fields=[
        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        ('seen_revision', models.DateTimeField(blank=True, null=True)),
        ('read_at', models.DateTimeField(auto_now_add=True)),
        ('announcement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='employee_receipts', to='contenthub.announcement')),
        ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='announcement_receipts', to='auth.user')),
    ], options={'constraints':[models.UniqueConstraint(fields=('recipient','announcement'),name='unique_employee_announcement_receipt')]})]
