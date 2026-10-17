from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('contenthub', '0007_resource_cover_image')]
    operations = [
        migrations.AlterField(
            model_name='resource', name='kind',
            field=models.CharField(max_length=20, default='policy', choices=[
                ('policy', 'Policy'), ('document', 'Document'), ('brochure', 'Brochure'),
                ('insider', 'Vishakha Insider'), ('bank_benefit', 'Bank Benefits'),
                ('canteen_menu', 'Canteen Menu'), ('video', 'Company Videos'),
            ]),
        ),
    ]
