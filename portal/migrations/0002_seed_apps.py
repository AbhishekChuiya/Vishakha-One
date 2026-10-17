from django.db import migrations

APPS = [
 ('PeopleStrong','HR & People','peoplestrong.png','https://vishakha.peoplestrong.com/altLogin.jsf'),
 ('Service Excellence Portal','Operations','vishakha.png',''),
 ('SAP Fiori','ERP & Finance','sap.png',''),
 ('SAP Business One','ERP & Finance','sap.png',''),
 ('Odoo','Operations','odoo.png',''),
 ('ProcureGenie','Procurement','procuregenie.png',''),
 ('Quest2Travel','Travel','quest.png',''),
 ('GyaanShala','Learning','gyaan.png',''),
 ('VRPL IoT','Manufacturing','vishakha.png',''),
 ('CLMS','Compliance','vishakha.png',''),
 ('Legratrix','Legal','vishakha.png',''),
 ('Vishakha Group','Company','vishakha.png',''),
]

def seed(apps, schema_editor):
    Model = apps.get_model('portal','CompanyApplication')
    for i,(name,category,icon,url) in enumerate(APPS):
        Model.objects.get_or_create(name=name, defaults={
            'category':category, 'icon_path':'assets/apps/'+icon,
            'url':url, 'display_order':i+1, 'is_active':True,
        })

def unseed(apps, schema_editor):
    pass  # Avoid deleting employee-managed records on reverse migration.

class Migration(migrations.Migration):
    dependencies = [('portal','0001_initial')]
    operations = [migrations.RunPython(seed, unseed)]
