from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('contenthub', '0001_initial'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name='announcement', name='approval_status', field=models.CharField(choices=[('draft', 'Draft'), ('pending', 'Pending approval'), ('approved', 'Approved'), ('rejected', 'Changes requested')], db_index=True, default='approved', max_length=12)),
        migrations.AddField(model_name='announcement', name='submitted_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='announcement', name='reviewed_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='announcement', name='submitted_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='announcement', name='reviewed_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='announcement', name='review_note', field=models.TextField(blank=True)),
        migrations.AlterModelOptions(name='announcement', options={'ordering': ('display_order', '-published_at'), 'permissions': [('approve_announcement', 'Can approve Announcement content')]}),
        migrations.AddField(model_name='resource', name='approval_status', field=models.CharField(choices=[('draft', 'Draft'), ('pending', 'Pending approval'), ('approved', 'Approved'), ('rejected', 'Changes requested')], db_index=True, default='approved', max_length=12)),
        migrations.AddField(model_name='resource', name='submitted_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='resource', name='reviewed_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='resource', name='submitted_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='resource', name='reviewed_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='resource', name='review_note', field=models.TextField(blank=True)),
        migrations.AlterModelOptions(name='resource', options={'ordering': ('display_order', '-published_at'), 'permissions': [('approve_resource', 'Can approve Resource content'), ('manage_policy_only', 'Can manage policy resources only')]}),
        migrations.AddField(model_name='jobopening', name='approval_status', field=models.CharField(choices=[('draft', 'Draft'), ('pending', 'Pending approval'), ('approved', 'Approved'), ('rejected', 'Changes requested')], db_index=True, default='approved', max_length=12)),
        migrations.AddField(model_name='jobopening', name='submitted_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='jobopening', name='reviewed_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='jobopening', name='submitted_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='jobopening', name='reviewed_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='jobopening', name='review_note', field=models.TextField(blank=True)),
        migrations.AlterModelOptions(name='jobopening', options={'ordering': ('display_order', '-published_at'), 'permissions': [('approve_jobopening', 'Can approve Jobopening content')]}),
        migrations.AddField(model_name='newjoiner', name='approval_status', field=models.CharField(choices=[('draft', 'Draft'), ('pending', 'Pending approval'), ('approved', 'Approved'), ('rejected', 'Changes requested')], db_index=True, default='approved', max_length=12)),
        migrations.AddField(model_name='newjoiner', name='submitted_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='newjoiner', name='reviewed_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='newjoiner', name='submitted_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='newjoiner', name='reviewed_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='newjoiner', name='review_note', field=models.TextField(blank=True)),
        migrations.AlterModelOptions(name='newjoiner', options={'ordering': ('display_order', '-published_at'), 'permissions': [('approve_newjoiner', 'Can approve Newjoiner content')]}),
        migrations.AddField(model_name='event', name='approval_status', field=models.CharField(choices=[('draft', 'Draft'), ('pending', 'Pending approval'), ('approved', 'Approved'), ('rejected', 'Changes requested')], db_index=True, default='approved', max_length=12)),
        migrations.AddField(model_name='event', name='submitted_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='event', name='reviewed_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='event', name='submitted_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='event', name='reviewed_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='event', name='review_note', field=models.TextField(blank=True)),
        migrations.AlterModelOptions(name='event', options={'ordering': ('display_order', '-published_at'), 'permissions': [('approve_event', 'Can approve Event content')]}),
    ]
