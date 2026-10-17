from django.core.management.base import BaseCommand
from django.db import transaction
from portal.models import CompanyApplication

APPLICATIONS = [
    ("Vishakha Group", "Home | Vishakha Group", "https://www.vishakha.com/", "Company", "vishakha.png"),
    ("VRPL IoT", "VRPL IOT", "http://vrpliot.vishakhagroup.com:8080/", "Manufacturing", "vishakha.png"),
    ("Quest2Travel", "Quest2Travel", "https://quest2travel.in/vishakha", "Travel", "quest.png"),
    ("Legratrix", "Legatrix", "https://prod.legatrix.in/Legatrix-Vishakha-Live/", "Legal", "vishakha.png"),
    ("Service Excellence Portal", "Service Excellence Portal", "https://vresolved.vishakhapolyfab.com/", "Operations", "vishakha.png"),
    ("Odoo", "Odoo", "https://odoo.vishakhapolyfab.com/web/database/selector", "Operations", "odoo.png"),
    ("PeopleStrong", "PeopleStrong", "https://vishakha.peoplestrong.com/altLogin.jsf", "HR & People", "peoplestrong.png"),
    ("CLMS", "CLMS", "http://labourworks.vishakhagroup.com:251/labourworks/Login.aspx", "Compliance", "vishakha.png"),
    ("GyaanShala", "Gyaanshala Learning Portal", "https://gyaanshala.percipio.com/login?state=/#/", "Learning", "gyaan.png"),
    ("SAP Fiori", "SAP Fiori Prod.", "https://vpplwebwdp.vishakhapolyfab.com:44300/sap/bc/ui2/flp", "ERP & Finance", "sap.png"),
    ("ProcureGenie", "ProcureGenie", "https://vishakhavendors.procuregenie.com/login", "Procurement", "procuregenie.png"),
    ("SAP Business One", "SAP Business One", "https://sapserver:8100/dispatcher/", "ERP & Finance", "sap.png"),
]

class Command(BaseCommand):
    help = "Update company application links without creating duplicate records."

    @transaction.atomic
    def handle(self, *args, **options):
        for index, (lookup_name, display_name, url, category, icon_file) in enumerate(APPLICATIONS, 1):
            app = CompanyApplication.objects.filter(name=lookup_name).first()
            if app is None and display_name != lookup_name:
                app = CompanyApplication.objects.filter(name=display_name).first()
            if app is None:
                app = CompanyApplication(name=display_name)
            app.name = display_name
            app.url = url
            app.category = category
            app.display_order = index
            app.is_active = True
            if not app.icon_path:
                app.icon_path = f"assets/apps/{icon_file}"
            app.save()
            self.stdout.write(self.style.SUCCESS(f"{index:02d}. {app.name}: {app.url}"))
        self.stdout.write(self.style.SUCCESS("Application links updated successfully."))
