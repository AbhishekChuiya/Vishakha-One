from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('contenthub', '0009_csr_home_banner')]
    operations = [migrations.AddField(
        model_name='newjoiner',
        name='introduction_document',
        field=models.FileField(upload_to='content/joiner_profiles/', blank=True,
            help_text='Optional detailed new joiner introduction (PDF or image).'),
    )]
