from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='CompanyApplication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('url', models.URLField(blank=True, max_length=1000)),
                ('category', models.CharField(blank=True, max_length=100)),
                ('icon_path', models.CharField(blank=True, help_text='Path relative to static/, e.g. assets/apps/sap.png', max_length=255)),
                ('display_order', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'ordering': ['display_order', 'name']},
        ),
    ]
