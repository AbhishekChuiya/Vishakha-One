from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('contenthub', '0014_alter_jobopening_options_alter_newjoiner_options'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='CanteenDay',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(db_index=True, unique=True)),
                ('is_holiday', models.BooleanField(default=False)),
                ('lunch_veg_dal', models.CharField(blank=True, max_length=300, verbose_name='Veg / Dal preparation')),
                ('lunch_roti', models.CharField(blank=True, max_length=200, verbose_name='Roti preparation')),
                ('lunch_rice', models.CharField(blank=True, max_length=250, verbose_name='Salad / Papad / Rice')),
                ('lunch_curd', models.CharField(blank=True, max_length=250, verbose_name='Curd / Sweet')),
                ('snacks', models.CharField(blank=True, max_length=300, verbose_name='Evening snacks')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('date',), 'permissions': [('manage_canteen_menu', 'Can manage daily canteen menu')]},
        ),
    ]
