from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('contenthub', '0005_approvalreminderdelivery')]
    operations = [
        migrations.AlterField(
            model_name='announcement', name='category',
            field=models.CharField(max_length=20, default='news', choices=[
                ('news', 'Company News'), ('announcement', 'Announcement'),
                ('recognition', 'Recognition'), ('gallery', 'Life at Vishakha Gallery'),
            ]),
        ),
        migrations.AlterField(
            model_name='resource', name='kind',
            field=models.CharField(max_length=20, default='policy', choices=[
                ('policy', 'Policy'), ('document', 'Document'), ('brochure', 'Brochure'),
                ('insider', 'Vishakha Insider'), ('bank_benefit', 'Bank Benefits'),
                ('canteen_menu', 'Canteen Menu'),
            ]),
        ),
    ]
